"""
FastAPI 本地服務（階段 2 + 3）。

白話說明：
- 在你電腦上開一個 HTTP 服務
- Coze / 瀏覽器 / curl 都可以 POST Scene JSON 進來
- 服務負責驗證、補預設、寫入剪映草稿
- 階段 3：可選 Token、Coze 友善端點（扁平欄位方便映射）

啟動：
  python -m src.api
  或：uvicorn src.api:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from . import __version__
from .auth import get_configured_token, token_required, verify_api_token
from .converter import ConvertResult, convert_from_dict
from .defaults import apply_defaults, default_jianying_draft_folder
from .models import SceneDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 設定（可用環境變數覆寫）
# ---------------------------------------------------------------------------
API_HOST = os.getenv("JY_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("JY_API_PORT", "8765"))
API_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("JY_API_CORS_ORIGINS", "*").split(",")
    if o.strip()
]


app = FastAPI(
    title="自製剪映小助手 API",
    description=(
        "接收 Scene JSON → 驗證／補預設 → 寫入剪映本機草稿。\n\n"
        "階段 2：本地 HTTP。\n"
        "階段 3：Coze 串接（/v1/coze/*）+ 可選 Token。\n\n"
        "文件：docs/COZE_INTEGRATION.md"
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CORS_ORIGINS if API_CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 回應模型
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "jianying-assistant"
    version: str
    draft_folder: str
    draft_folder_exists: bool
    auth_required: bool = False


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorBody


class ValidateData(BaseModel):
    title: str
    project: dict[str, Any]
    scene_count: int
    scenes: list[dict[str, Any]]
    has_bgm: bool
    draft_folder: Optional[str]
    allow_replace: bool
    normalized: Optional[dict[str, Any]] = None


class ValidateResponse(BaseModel):
    ok: bool = True
    message: str = "驗證通過"
    data: ValidateData


class ConvertData(BaseModel):
    draft_name: str
    draft_folder: str
    draft_path: str
    scene_count: int
    total_duration_sec: float
    has_bgm: bool
    has_subtitles: bool


class ConvertResponse(BaseModel):
    ok: bool = True
    message: str = "草稿已建立"
    data: ConvertData


class CozeConvertResponse(BaseModel):
    """
    Coze 友善回應：同時有 data 巢狀 + 頂層扁平欄位。

    Coze 工作流映射時，可直接取 draft_name / draft_path 等。
    """

    ok: bool = True
    success: bool = True
    message: str = "草稿已建立"
    # 扁平欄位（給 Coze 節點取值）
    draft_name: str
    draft_folder: str
    draft_path: str
    scene_count: int
    total_duration_sec: float
    has_bgm: bool
    has_subtitles: bool
    # 巢狀（與 /v1/convert 一致，方便通用客戶端）
    data: ConvertData


class CozeValidateResponse(BaseModel):
    ok: bool = True
    success: bool = True
    message: str = "驗證通過"
    title: str
    scene_count: int
    has_bgm: bool
    draft_folder: Optional[str]
    data: ValidateData


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "success": False,
            "error": {"code": code, "message": message, "details": details},
            # 扁平錯誤訊息，方便 Coze 直接顯示
            "message": message,
            "error_code": code,
        },
    )


async def _read_json_body(request: Request) -> dict[str, Any]:
    """
    讀取 body，並容忍「JSON 字串再包一層」的情況（部分 Coze 節點會這樣送）。
    """
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"無法解析 JSON body：{e}") from e

    # 有時 body 整段是字串
    if isinstance(body, str):
        body = json.loads(body)

    if not isinstance(body, dict):
        raise ValueError("請求 body 必須是 JSON 物件")

    # Coze 偶發：{ "body": "{...json string...}" }
    if "body" in body and isinstance(body["body"], str) and "scenes" not in body:
        try:
            inner = json.loads(body["body"])
            if isinstance(inner, dict):
                return inner
        except json.JSONDecodeError:
            pass

    return body


def _parse_body(body: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    回傳 (scene_dict, options_dict)。

    支援：
    - 直接 Scene JSON（有 title + scenes）
    - 包裝格式 {scene, options}
    - Coze 變體：{ data: Scene } / { output: Scene } / { scene_json: Scene|str }
    """
    if not isinstance(body, dict):
        raise ValueError("請求 body 必須是 JSON 物件")

    # 包裝：scene
    if "scene" in body and isinstance(body["scene"], dict):
        options = body.get("options") or {}
        if not isinstance(options, dict):
            raise ValueError("options 必須是物件")
        return body["scene"], options

    # scene_json 字串或物件
    if "scene_json" in body:
        sj = body["scene_json"]
        if isinstance(sj, str):
            sj = json.loads(sj)
        if isinstance(sj, dict):
            options = body.get("options") or {}
            return sj, options if isinstance(options, dict) else {}

    # data / output 包一層
    for key in ("data", "output", "result"):
        if key in body and isinstance(body[key], dict):
            inner = body[key]
            if "title" in inner and "scenes" in inner:
                return inner, body.get("options") or {}
            if "scene" in inner and isinstance(inner["scene"], dict):
                return inner["scene"], inner.get("options") or body.get("options") or {}

    if "title" in body and "scenes" in body:
        return body, {}

    raise ValueError(
        "無法辨識 body 格式。請傳送 Scene JSON（需含 title、scenes），"
        '或 {"scene": {...}, "options": {...}}，'
        '或 {"scene_json": {...}}'
    )


def _result_to_data(result: ConvertResult) -> ConvertData:
    return ConvertData(
        draft_name=result.draft_name,
        draft_folder=result.draft_folder,
        draft_path=result.draft_path,
        scene_count=result.scene_count,
        total_duration_sec=result.total_duration_sec,
        has_bgm=result.has_bgm,
        has_subtitles=result.has_subtitles,
    )


def _doc_to_validate_data(
    doc: SceneDocument,
    *,
    include_normalized: bool,
) -> ValidateData:
    scenes_brief = []
    for s in doc.scenes:
        scenes_brief.append(
            {
                "id": s.id,
                "type": s.type.value if s.type else None,
                "path": s.path,
                "duration": s.duration,
                "text": s.text,
            }
        )
    return ValidateData(
        title=doc.title,
        project=doc.project.model_dump(),
        scene_count=len(doc.scenes),
        scenes=scenes_brief,
        has_bgm=doc.bgm is not None,
        draft_folder=doc.draft_folder,
        allow_replace=doc.allow_replace,
        normalized=doc.model_dump(mode="json") if include_normalized else None,
    )


def _do_validate(
    scene_raw: dict[str, Any],
    options: dict[str, Any],
    *,
    check_files: bool,
    base_dir: Optional[str],
    include_normalized: bool,
) -> ValidateData:
    opt_check = options.get("check_files", check_files)
    opt_base = options.get("base_dir", base_dir)
    opt_norm = options.get("include_normalized", include_normalized)
    raw = dict(scene_raw)
    if options.get("draft_folder"):
        raw["draft_folder"] = options["draft_folder"]

    doc = apply_defaults(
        raw,
        base_dir=opt_base,
        check_files_exist=bool(opt_check),
    )
    return _doc_to_validate_data(doc, include_normalized=bool(opt_norm))


def _do_convert(
    scene_raw: dict[str, Any],
    options: dict[str, Any],
    *,
    check_files: bool,
    base_dir: Optional[str],
    draft_folder: Optional[str],
) -> ConvertResult:
    opt_check = bool(options.get("check_files", check_files))
    opt_base = options.get("base_dir", base_dir)
    opt_draft = options.get("draft_folder", draft_folder)
    return convert_from_dict(
        scene_raw,
        base_dir=opt_base,
        check_files=opt_check,
        draft_folder_override=opt_draft,
    )


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.get("/", tags=["meta"])
def root() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "jianying-assistant",
        "version": __version__,
        "docs": "/docs",
        "coze_guide": "/v1/coze/guide",
        "auth_required": token_required(),
        "endpoints": {
            "health": "GET /health",
            "validate": "POST /v1/validate",
            "convert": "POST /v1/convert",
            "coze_validate": "POST /v1/coze/validate",
            "coze_convert": "POST /v1/coze/convert",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    folder = default_jianying_draft_folder()
    return HealthResponse(
        version=__version__,
        draft_folder=folder,
        draft_folder_exists=Path(folder).is_dir(),
        auth_required=token_required(),
    )


@app.get("/v1/coze/guide", tags=["coze"], summary="Coze 串接速查（JSON）")
def coze_guide() -> dict[str, Any]:
    """給人或給 Agent 讀的串接說明（不需 Token）。"""
    return {
        "ok": True,
        "summary": "Coze 最後一個 HTTP 節點 POST Scene JSON 到本機剪映小助手",
        "recommended_url_path": "/v1/coze/convert",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer <JY_API_TOKEN>（若有設定）",
            "X-API-Key": "<JY_API_TOKEN>（二選一）",
        },
        "body_formats": [
            "直接 Scene JSON：{title, scenes:[...]}",
            '包裝：{"scene": {...}, "options": {"check_files": true}}',
            '字串：{"scene_json": "{...}"}',
        ],
        "success_fields": [
            "ok",
            "success",
            "message",
            "draft_name",
            "draft_path",
            "scene_count",
            "total_duration_sec",
        ],
        "local_default": f"http://127.0.0.1:{API_PORT}",
        "full_docs": "docs/COZE_INTEGRATION.md",
        "important": [
            "寫剪映草稿必須在「有安裝剪映的那台電腦」上跑本服務",
            "Coze 雲端無法直接打 127.0.0.1，需隧道（cpolar / cloudflared）",
            "素材 path 必須是本機真實路徑，不能是網頁 URL",
        ],
    }


@app.post(
    "/v1/validate",
    response_model=ValidateResponse,
    responses={400: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
    tags=["scene"],
    summary="驗證 Scene JSON 並補預設值（不寫草稿）",
    dependencies=[Depends(verify_api_token)],
)
async def validate_scene(
    request: Request,
    check_files: bool = Query(False, description="是否檢查素材檔案是否存在"),
    base_dir: Optional[str] = Query(None, description="相對路徑基準目錄"),
    include_normalized: bool = Query(False, description="是否附上補全後完整 JSON"),
) -> ValidateResponse | JSONResponse:
    try:
        body = await _read_json_body(request)
        scene_raw, options = _parse_body(body)
        data = _do_validate(
            scene_raw,
            options,
            check_files=check_files,
            base_dir=base_dir,
            include_normalized=include_normalized,
        )
        return ValidateResponse(data=data)
    except ValidationError as e:
        return _error(422, "VALIDATION_ERROR", "Scene JSON 欄位驗證失敗", e.errors())
    except FileNotFoundError as e:
        return _error(400, "FILE_NOT_FOUND", str(e))
    except (ValueError, json.JSONDecodeError) as e:
        return _error(400, "BAD_REQUEST", str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("validate 失敗")
        return _error(500, "INTERNAL_ERROR", str(e), traceback.format_exc())


@app.post(
    "/v1/convert",
    response_model=ConvertResponse,
    responses={
        400: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
        500: {"model": ApiErrorResponse},
    },
    tags=["scene"],
    summary="驗證並寫入剪映草稿",
    dependencies=[Depends(verify_api_token)],
)
async def convert_scene(
    request: Request,
    check_files: bool = Query(True, description="是否檢查素材檔存在"),
    base_dir: Optional[str] = Query(None, description="相對路徑基準目錄"),
    draft_folder: Optional[str] = Query(None, description="覆寫剪映草稿根目錄"),
) -> ConvertResponse | JSONResponse:
    try:
        body = await _read_json_body(request)
        scene_raw, options = _parse_body(body)
        result = _do_convert(
            scene_raw,
            options,
            check_files=check_files,
            base_dir=base_dir,
            draft_folder=draft_folder,
        )
        return ConvertResponse(data=_result_to_data(result))
    except ValidationError as e:
        return _error(422, "VALIDATION_ERROR", "Scene JSON 欄位驗證失敗", e.errors())
    except FileNotFoundError as e:
        return _error(400, "FILE_NOT_FOUND", str(e))
    except (ValueError, json.JSONDecodeError) as e:
        return _error(400, "BAD_REQUEST", str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("convert 失敗")
        return _error(500, "INTERNAL_ERROR", str(e), traceback.format_exc())


@app.post(
    "/v1/coze/validate",
    response_model=CozeValidateResponse,
    tags=["coze"],
    summary="【Coze 專用】驗證 Scene JSON（扁平欄位）",
    dependencies=[Depends(verify_api_token)],
)
async def coze_validate(
    request: Request,
    check_files: bool = Query(False),
    base_dir: Optional[str] = Query(None),
    include_normalized: bool = Query(False),
) -> CozeValidateResponse | JSONResponse:
    try:
        body = await _read_json_body(request)
        scene_raw, options = _parse_body(body)
        data = _do_validate(
            scene_raw,
            options,
            check_files=check_files,
            base_dir=base_dir,
            include_normalized=include_normalized,
        )
        return CozeValidateResponse(
            title=data.title,
            scene_count=data.scene_count,
            has_bgm=data.has_bgm,
            draft_folder=data.draft_folder,
            data=data,
        )
    except ValidationError as e:
        return _error(422, "VALIDATION_ERROR", "Scene JSON 欄位驗證失敗", e.errors())
    except FileNotFoundError as e:
        return _error(400, "FILE_NOT_FOUND", str(e))
    except (ValueError, json.JSONDecodeError) as e:
        return _error(400, "BAD_REQUEST", str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("coze_validate 失敗")
        return _error(500, "INTERNAL_ERROR", str(e), traceback.format_exc())


@app.post(
    "/v1/coze/convert",
    response_model=CozeConvertResponse,
    tags=["coze"],
    summary="【Coze 專用】寫入剪映草稿（扁平欄位，建議用這個）",
    dependencies=[Depends(verify_api_token)],
)
async def coze_convert(
    request: Request,
    check_files: bool = Query(True),
    base_dir: Optional[str] = Query(None),
    draft_folder: Optional[str] = Query(None),
) -> CozeConvertResponse | JSONResponse:
    try:
        body = await _read_json_body(request)
        scene_raw, options = _parse_body(body)
        result = _do_convert(
            scene_raw,
            options,
            check_files=check_files,
            base_dir=base_dir,
            draft_folder=draft_folder,
        )
        data = _result_to_data(result)
        return CozeConvertResponse(
            draft_name=data.draft_name,
            draft_folder=data.draft_folder,
            draft_path=data.draft_path,
            scene_count=data.scene_count,
            total_duration_sec=data.total_duration_sec,
            has_bgm=data.has_bgm,
            has_subtitles=data.has_subtitles,
            data=data,
        )
    except ValidationError as e:
        return _error(422, "VALIDATION_ERROR", "Scene JSON 欄位驗證失敗", e.errors())
    except FileNotFoundError as e:
        return _error(400, "FILE_NOT_FOUND", str(e))
    except (ValueError, json.JSONDecodeError) as e:
        return _error(400, "BAD_REQUEST", str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("coze_convert 失敗")
        return _error(500, "INTERNAL_ERROR", str(e), traceback.format_exc())


def main() -> None:
    """python -m src.api 進入點。"""
    logging.basicConfig(
        level=os.getenv("JY_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    import uvicorn

    token_set = bool(get_configured_token())
    logger.info(
        "啟動剪映小助手 API：http://%s:%s  docs=http://%s:%s/docs",
        API_HOST,
        API_PORT,
        API_HOST,
        API_PORT,
    )
    logger.info("預設草稿目錄：%s", default_jianying_draft_folder())
    logger.info(
        "API Token：%s",
        "已啟用（請在 Coze Header 帶 Authorization: Bearer ...）"
        if token_set
        else "未設定（僅建議本機使用；對外隧道請設 JY_API_TOKEN）",
    )
    uvicorn.run(
        "src.api:app",
        host=API_HOST,
        port=API_PORT,
        reload=os.getenv("JY_API_RELOAD", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
