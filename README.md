# 自製剪映小助手

兩條線一起走：

1. **線上模板介面（目前主線）**  
   Streamlit → **Streamlit Community Cloud（免費）** → 手機也能設模板。  
   模板用 **下載/上傳 JSON**，你自行放到 Google 雲端硬碟。

2. **本機剪映草稿**  
   Coze Scene JSON → 本機 Python → **pyJianYingDraft** 寫入剪映。  
   （草稿只能在你電腦寫，雲端做不到。）

## 進度

### A. 線上 Streamlit 模板介面（目前主線）

| 能力 | 狀態 |
|------|------|
| 富模板 Pydantic 資料結構 | ✅ UI 階段 1 |
| 頁面框架 + 側邊欄（手機可開） | ✅ UI 階段 1 |
| 全域設定（素材用檔名/代號） | ✅ UI 階段 1 |
| 可部署 Streamlit Community Cloud | ✅ UI 階段 1 |
| 分鏡管理與詳細設定 | ✅ UI 階段 2 |
| 可視化預覽 + JSON 下載/上傳 | ✅ UI 階段 3 |

### B. Coze → 剪映草稿（本機）

| 能力 | 狀態 |
|------|------|
| Scene JSON + 預設值 + 寫草稿 | ✅ |
| FastAPI / Coze HTTP | ✅ |
| LLM 智能層 | ⏳ 可選 |

---

## 線上介面：本機預覽

```powershell
cd C:\Users\Jimmy\jianying-assistant
pip install -r requirements.txt
streamlit run streamlit_app.py
# 或 .\scripts\start_streamlit.ps1
```

瀏覽器：http://localhost:8501

## 線上介面：免費部署（Streamlit Cloud）

完整步驟：**[docs/STREAMLIT_CLOUD_DEPLOY.md](docs/STREAMLIT_CLOUD_DEPLOY.md)**

| 項目 | 值 |
|------|-----|
| 倉庫 | 推到 GitHub |
| Main file path | **`streamlit_app.py`** |
| 依賴 | 根目錄 `requirements.txt`（僅 streamlit + pydantic） |
| 費用 | 免費方案 |

模板保存：階段 3 提供下載/上傳 JSON → 你放到 Google 雲端硬碟。

**UI 階段 1 可做：** 專案名、解析度、FPS、BGM 參數、底圖/封面參數、使用說明頁。

## 目錄結構

```
jianying-assistant/
├── streamlit_app.py          # ★ 雲端部署入口
├── requirements.txt          # ★ 雲端輕量依賴
├── requirements-local.txt    # 本機剪映/API 完整依賴
├── .streamlit/config.toml
├── src/
│   ├── template_models.py    # 模板 UI 資料結構
│   ├── ui/                   # Streamlit 介面
│   ├── models.py / converter.py / api.py   # 本機剪映線
├── docs/
│   ├── STREAMLIT_CLOUD_DEPLOY.md
│   └── COZE_INTEGRATION.md
├── templates/
├── tests/
└── scripts/
```

## 安裝

```powershell
cd C:\Users\Jimmy\jianying-assistant

# 只要線上介面 / 本機預覽 UI
pip install -r requirements.txt

# 若還要本機寫剪映草稿 + Coze API
pip install -r requirements-local.txt
pip install pytest   # 跑測試用
```

可選：複製 `.env.example` 為 `.env`，設定草稿路徑與 API port。

本機已偵測到預設草稿目錄時，**不設也能跑**：

`C:\Users\Jimmy\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`

---

## 階段 2：啟動 HTTP 服務

```powershell
cd C:\Users\Jimmy\jianying-assistant

# 方式 A
python -m src.api

# 方式 B
.\scripts\start_server.ps1
```

| 項目 | 預設 |
|------|------|
| 地址 | http://127.0.0.1:8765 |
| 互動文件 | http://127.0.0.1:8765/docs |
| 健康檢查 | GET /health |

### API 一覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 服務是否正常、草稿目錄是否存在 |
| POST | `/v1/validate` | 驗證 + 補預設（**不**寫草稿） |
| POST | `/v1/convert` | 驗證並寫入剪映草稿 |
| POST | `/v1/coze/convert` | **Coze 主推**：扁平欄位回應 |
| POST | `/v1/coze/validate` | Coze 用驗證 |
| GET | `/v1/coze/guide` | 串接速查 JSON |

### 請求 body 兩種格式

**格式 1：直接 Scene JSON（最簡單）**

```json
{
  "title": "我的草稿",
  "scenes": [
    { "path": "C:/path/to/clip.mp4", "text": "字幕" }
  ]
}
```

**格式 2：包裝格式（方便之後 Coze 塞 options）**

```json
{
  "scene": {
    "title": "我的草稿",
    "scenes": [{ "path": "C:/path/to/clip.mp4", "text": "字幕" }]
  },
  "options": {
    "check_files": true,
    "base_dir": "C:/Users/Jimmy/videos",
    "draft_folder": null
  }
}
```

### curl 範例（PowerShell）

```powershell
# 健康檢查
Invoke-RestMethod http://127.0.0.1:8765/health

# 驗證
$body = Get-Content examples\sample_scene.json -Raw -Encoding UTF8
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8765/v1/validate?check_files=true&base_dir=C:\Users\Jimmy\jianying-assistant\examples" `
  -Method POST -ContentType "application/json; charset=utf-8" -Body $body

# 轉草稿
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8765/v1/convert?check_files=true&base_dir=C:\Users\Jimmy\jianying-assistant\examples" `
  -Method POST -ContentType "application/json; charset=utf-8" -Body $body
```

### 成功回應範例（convert）

```json
{
  "ok": true,
  "message": "草稿已建立",
  "data": {
    "draft_name": "JY助手_階段1測試",
    "draft_path": "C:\\Users\\...\\JY助手_階段1測試",
    "scene_count": 3,
    "total_duration_sec": 6.5,
    "has_bgm": true,
    "has_subtitles": true
  }
}
```

### 失敗回應範例

```json
{
  "ok": false,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "素材不存在：...",
    "details": null
  }
}
```

常見 `error.code`：`VALIDATION_ERROR` / `FILE_NOT_FOUND` / `BAD_REQUEST` / `INTERNAL_ERROR`

---

## 一鍵測試

```powershell
cd C:\Users\Jimmy\jianying-assistant

# 階段 1（CLI + 草稿）
python scripts\run_phase1_test.py

# 階段 2（pytest + 真 HTTP）
python scripts\run_phase2_test.py

# 階段 3（模擬 Coze + Token）
python scripts\run_phase3_test.py
```

---

## 階段 3：接 Coze（精簡版）

完整說明請看：**[docs/COZE_INTEGRATION.md](docs/COZE_INTEGRATION.md)**

```powershell
# 1) 帶 Token 啟動（給隧道用）
.\scripts\start_for_coze.ps1

# 2) 另開終端做隧道（擇一）
cpolar http 8765
# 或
cloudflared tunnel --url http://127.0.0.1:8765

# 3) Coze HTTP 節點
#    POST https://你的隧道網域/v1/coze/convert
#    Header: Authorization: Bearer <JY_API_TOKEN>
#    Body: Scene JSON
```

**記住：** 寫剪映草稿一定要在本機跑本服務；雲端 Workers/Spaces 寫不進你的剪映資料夾。

---

## 階段 1 CLI（仍可用）

```powershell
python -m src.cli validate examples\sample_scene.json --check-files
python -m src.cli convert examples\sample_scene.json
python -m src.cli convert examples\minimal_scene.json
```

## Scene JSON 最小範例

```json
{
  "title": "我的草稿",
  "scenes": [
    {
      "path": "C:/path/to/clip.mp4",
      "text": "字幕文字"
    }
  ]
}
```

完整欄位見 `examples/sample_scene.json` 與 `schema/scene_schema.json`。

### 常見欄位說明（白話）

| 欄位 | 意思 | 可省略？ |
|------|------|----------|
| `title` | 草稿名稱 | 否 |
| `scenes[].path` | 本地影片/圖片路徑 | 否 |
| `scenes[].type` | `video` / `image` | 可（依副檔名判斷） |
| `scenes[].duration` | 時間軸秒數 | 影片可；圖片預設 3 秒 |
| `scenes[].text` | 字幕 | 可 |
| `bgm.path` | 背景音樂 | 整段 bgm 可省略 |
| `project.width/height` | 畫布 | 預設 1080×1920 |

## 轉換後怎麼看

1. 打開 **剪映專業版**  
2. 若列表沒刷新：進入任一舊草稿再退出，或重開剪映  
3. 找到與 `title` 同名的草稿

## 常見錯誤與解法

| 錯誤 | 原因 | 解法 |
|------|------|------|
| `找不到 Scene JSON` | 路徑錯 | 用絕對路徑或先 `cd` 到專案根目錄 |
| `FILE_NOT_FOUND` / 素材不存在 | Coze 給了網址或錯誤本機路徑 | 只接受**本機真實檔案**；先下載到本地 |
| 草稿根目錄不存在 | 路徑不對 | 剪映 → 全局设置 → 草稿位置，設 `JIANYING_DRAFT_FOLDER` |
| 無法從副檔名判斷 | 奇怪副檔名 | 在 scene 加 `"type": "video"` 或 `"image"` |
| `address already in use` | 8765 被占用 | 設 `JY_API_PORT=8766` 或關掉舊程序 |
| 連不上 127.0.0.1 | 服務沒開 | 先 `python -m src.api` |
| BGM 比影片短 | 音訊不夠長 | 會自動裁短並警告，不崩潰 |

## 階段限制

### 階段 1+2 共同
- **不**自動匯出成 MP4（需手動開剪映）  
- **不**下載遠端 URL 素材  
- **不**做轉場／特效／花字  

### 階段 2 額外
- 預設只綁 `127.0.0.1`（本機）

### 階段 3 額外
- Coze 雲端需搭配隧道（cpolar / cloudflared）  
- 對外時請設 `JY_API_TOKEN`  
- 仍不下載遠端素材 URL；path 必須本機存在  

## 架構

```
Coze Scene JSON  ──HTTP──►  FastAPI (/v1/convert)
                                │
                         [規則層] models + defaults
                                │
                         [converter] pyJianYingDraft
                                │
                           剪映草稿資料夾
```
