# Coze 串接指南（階段 3）

## 一句話架構

```
Coze 工作流產出 Scene JSON
        │
        │  HTTP POST（需可到達你電腦）
        ▼
本機 FastAPI（jianying-assistant）
        │
        ▼
pyJianYingDraft 寫入「這台電腦」的剪映草稿
        │
        ▼
你打開剪映 → 看到草稿
```

**關鍵限制（一定要懂）：**

1. **寫草稿必須在「有安裝剪映的電腦」上執行**  
   不能只部署到雲端伺服器，因為剪映草稿在本機資料夾。
2. **Coze 雲端跑工作流時，打不進 `127.0.0.1`**  
   需要「內網穿透 / 隧道」給 Coze 一個公開 HTTPS URL。
3. **素材 `path` 必須是本機檔案路徑**  
   例如 `C:/Users/Jimmy/videos/a.mp4`，不能是 `https://...` 圖片連結。

---

## 推薦端點（給 Coze 用）

| 用途 | 方法 | 路徑 | 說明 |
|------|------|------|------|
| 寫草稿（主推） | POST | `/v1/coze/convert` | 扁平欄位，方便 Coze 取值 |
| 只驗證 | POST | `/v1/coze/validate` | 不寫草稿 |
| 健康檢查 | GET | `/health` | 測隧道是否通 |
| 串接速查 | GET | `/v1/coze/guide` | JSON 說明 |

通用端點（階段 2）仍可用：`/v1/convert`、`/v1/validate`。

---

## 步驟 A：本機啟動 API

```powershell
cd C:\Users\Jimmy\jianying-assistant

# 建議：對外前先設 Token（請改成你自己的長密碼）
$env:JY_API_TOKEN = "請改成很長的隨機字串"
$env:JY_API_HOST = "127.0.0.1"
$env:JY_API_PORT = "8765"

python -m src.api
```

瀏覽器打開：http://127.0.0.1:8765/docs  
健康檢查：http://127.0.0.1:8765/health

---

## 步驟 B：讓 Coze 打得到你（隧道）

任選一種免費／低成本方案即可。

### 方案 1：cpolar（你電腦已有 `.cpolar` 設定痕跡）

1. 確認本機 API 已在 `8765` 跑著  
2. 開另一個終端，執行（指令依你安裝的 cpolar 為準）：

```powershell
cpolar http 8765
```

3. 複製它給你的 **公開 HTTPS 網址**，例如：  
   `https://xxxx.cpolar.cn`  
4. Coze 的完整 URL 就是：  
   `https://xxxx.cpolar.cn/v1/coze/convert`

### 方案 2：Cloudflare Tunnel（免費、穩定，推薦長期用）

1. 安裝 [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)  
2. 快速臨時隧道（免域名，適合測試）：

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

3. 終端會印出 `https://xxxxx.trycloudflare.com`  
4. Coze URL：`https://xxxxx.trycloudflare.com/v1/coze/convert`

> 注意：臨時隧道網址每次重開會變。固定域名需 Cloudflare 帳號進階設定。

### 方案 3：僅本機測試（不開 Coze 雲端）

若你用的是「能在本機跑」的客戶端，或只是用 Postman/curl 模擬 Coze：

```
http://127.0.0.1:8765/v1/coze/convert
```

**不需隧道。**

---

## 步驟 C：在 Coze 加「HTTP 請求」節點

不同版 Coze 介面文字可能略有差異，欄位對應如下：

### 1. 基本設定

| 欄位 | 填什麼 |
|------|--------|
| 請求方法 | `POST` |
| 請求 URL | `https://你的隧道網域/v1/coze/convert` |
| 逾時 | 建議 60～120 秒（素材多時轉換較久） |

### 2. Headers

| Header 名 | 值 |
|-----------|-----|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer 你的JY_API_TOKEN`（有設 Token 才要） |

也可用：`X-API-Key: 你的JY_API_TOKEN`

### 3. Body

**Body 類型：JSON**

把上一個節點產出的 Scene 物件整包送出。兩種最穩的寫法：

#### 寫法 A：直接 Scene（最簡單）

若上一步變數叫 `scene_json`（物件）：

```json
{{scene_json}}
```

或在 Coze 裡組：

```json
{
  "title": "{{title}}",
  "project": { "width": 1080, "height": 1920, "fps": 30 },
  "scenes": {{scenes_array}},
  "allow_replace": true
}
```

#### 寫法 B：包裝格式（方便帶 options）

```json
{
  "scene": {{scene_json}},
  "options": {
    "check_files": true
  }
}
```

#### 寫法 C：字串形式（有些 LLM 節點只輸出字串）

```json
{
  "scene_json": "{{scene_json_string}}"
}
```

本服務會自動 `json.loads`。

### 4. 成功後如何取值

成功時回應（節錄）：

```json
{
  "ok": true,
  "success": true,
  "message": "草稿已建立",
  "draft_name": "JY助手_階段2HTTP測試",
  "draft_path": "C:\\Users\\...\\JY助手_階段2HTTP測試",
  "scene_count": 3,
  "total_duration_sec": 6.5,
  "has_bgm": true,
  "has_subtitles": true
}
```

在 Coze 後續節點可映射：

| 你要的資訊 | 欄位路徑 |
|------------|----------|
| 是否成功 | `ok` 或 `success` |
| 提示文字 | `message` |
| 草稿名稱 | `draft_name` |
| 草稿完整路徑 | `draft_path` |
| 場景數 | `scene_count` |
| 總秒數 | `total_duration_sec` |

失敗時：

```json
{
  "ok": false,
  "success": false,
  "message": "素材不存在：...",
  "error_code": "FILE_NOT_FOUND",
  "error": { "code": "FILE_NOT_FOUND", "message": "..." }
}
```

---

## 步驟 D：建議的 Coze 工作流骨架

```
[開始]
  → [腳本/分鏡 LLM] 產出文案與場景描述
  → [素材落地] 下載或生成到「本機資料夾」（重要！）
  → [組裝 Scene JSON]  code 節點 / LLM 嚴格 JSON
  → [HTTP POST /v1/coze/convert]  ← 本服務
  → [回傳 draft_name 給使用者]
[結束]
```

### 組裝 Scene 時 checklist

- [ ] `title` 有值（會變成剪映草稿名）  
- [ ] 每個 scene 有本機 `path`  
- [ ] 圖片有 `duration` 或接受預設 3 秒  
- [ ] 路徑用 `/` 或 `\\` 皆可，但必須真實存在  
- [ ] 雲端 URL **不行**（階段 3 仍不下載遠端素材）

最小可用 JSON：

```json
{
  "title": "Coze來的草稿",
  "scenes": [
    {
      "path": "C:/Users/Jimmy/jianying-assistant/assets/test_clip_a.mp4",
      "text": "第一句字幕"
    }
  ],
  "allow_replace": true
}
```

完整範例見：`examples/sample_scene.json`、`examples/coze_request_body.json`

---

## 步驟 E：串接驗收清單

在你電腦上依序打勾：

1. [ ] `python -m src.api` 可開  
2. [ ] 瀏覽器 `GET /health` → `ok: true`  
3. [ ] 本機 `POST /v1/coze/convert` 成功，剪映看得到草稿  
4. [ ] 隧道開啟後，手機 4G 或另一台裝置能 `GET https://隧道/health`  
5. [ ] 設了 `JY_API_TOKEN` 後，沒帶 Token 會 401  
6. [ ] Coze HTTP 節點帶 Token，跑通一次完整工作流  
7. [ ] 打開剪映，找到 `draft_name` 同名草稿  

自動化測試（模擬 Coze，不含真實 Coze 雲端帳號）：

```powershell
cd C:\Users\Jimmy\jianying-assistant
python scripts\run_phase3_test.py
```

---

## 常見錯誤（Coze 特別容易踩）

| 現象 | 原因 | 解法 |
|------|------|------|
| Coze 報連線失敗 / timeout | 隧道沒開或 URL 錯 | 先用瀏覽器開 `/health` |
| 401 Unauthorized | Token 沒帶或帶錯 | Header `Authorization: Bearer ...` |
| FILE_NOT_FOUND | path 是網址或檔案不在這台電腦 | 先把素材存到本機再填 path |
| VALIDATION_ERROR | 缺 title/scenes 或型別錯 | 對照 `schema/scene_schema.json` |
| 草稿成功但剪映看不到 | 列表沒刷新 | 進舊草稿再退出，或重開剪映 |
| 隧道網址變了 | 臨時隧道重開 | 更新 Coze HTTP 節點 URL |
| 安全疑慮 | 公網暴露本機 | **一定要設 JY_API_TOKEN**，不用時關隧道 |

---

## 安全建議（必看）

1. **對外隧道時必設** `JY_API_TOKEN`  
2. 不要把 Token 寫進公開 Git 倉庫  
3. 不用時關掉 cpolar / cloudflared  
4. 服務維持綁 `127.0.0.1`，只讓隧道轉發進來（不要直接 `0.0.0.0` 暴露到區域網以外）

產生隨機 Token 範例：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 為什麼不部署到 Cloudflare Workers / HF Spaces？

因為最終要寫的是：

`C:\Users\...\JianyingPro\...\com.lveditor.draft`

這是**本機磁碟路徑**。雲端容器寫不進去你的剪映。

正確分工：

| 層 | 放哪 |
|----|------|
| 文案、分鏡、LLM | Coze 雲端 |
| 驗證 + 寫剪映草稿 | **本機** jianying-assistant |
| 可選：輕量轉發 | 隧道（cpolar / cloudflared） |

---

## 階段 3 交付範圍

| 項目 | 狀態 |
|------|------|
| Coze 專用 API | ✅ `/v1/coze/convert`、`/v1/coze/validate` |
| 可選 Token | ✅ `JY_API_TOKEN` |
| 相容多種 body 格式 | ✅ scene / scene_json / data 包裝 |
| 本文件 | ✅ |
| 模擬 Coze 測試腳本 | ✅ `scripts/run_phase3_test.py` |
| 真實 Coze 帳號內建工作流匯出 | ❌（需你在 Coze 後台依本文件點一次） |
