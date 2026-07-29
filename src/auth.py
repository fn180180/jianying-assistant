"""
可選 API Token 驗證（階段 3 對外隧道時建議開啟）。

白話說明：
- 本機自己用：可以不設 Token
- 用 cpolar / Cloudflare Tunnel 把服務暴露出去時：一定要設 Token
- Coze HTTP 節點在 Header 加：Authorization: Bearer <你的Token>
  或：X-API-Key: <你的Token>
"""

from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException, status


def get_configured_token() -> Optional[str]:
    """讀取環境變數中的 Token；空字串視為未設定。"""
    token = os.getenv("JY_API_TOKEN", "").strip()
    return token or None


def token_required() -> bool:
    return get_configured_token() is not None


def verify_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    FastAPI Depends 用：若設定了 JY_API_TOKEN，則強制驗證。

    支援：
    - Authorization: Bearer <token>
    - X-API-Key: <token>
    """
    expected = get_configured_token()
    if expected is None:
        return  # 未設定 = 不檢查（本機開發方便）

    provided: Optional[str] = None
    if x_api_key and x_api_key.strip():
        provided = x_api_key.strip()
    elif authorization and authorization.strip():
        auth = authorization.strip()
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()
        else:
            provided = auth

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "ok": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "缺少或錯誤的 API Token。請在 Header 加 Authorization: Bearer <token> 或 X-API-Key",
                    "details": None,
                },
            },
        )
