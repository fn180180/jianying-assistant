# 免費部署到 Streamlit Community Cloud（白話步驟）

目標：手機瀏覽器也能開「剪映小助手」模板設定介面。  
費用：**完全免費**（Streamlit Community Cloud 免費方案）。

---

## 你會得到什麼

- 一個公開或可分享的網址，例如 `https://xxxx.streamlit.app`
- 在外面用手機就能設定模板
- 模板用「下載 JSON → 放 Google 雲端硬碟 → 需要時再上傳」保存  
  （雲端網站**不能**直接寫進你電腦或 Google Drive，所以用下載/上傳最穩）

---

## 前提

1. 有 **GitHub** 帳號（免費）
2. 有 **Streamlit** 帳號（用 GitHub 登入即可，免費）
3. 本專案程式已推到 **公開或私有** GitHub 倉庫  
   - 免費方案支援 public repo；private 視當前 Streamlit 政策，公開最省事

---

## 步驟一：把專案推到 GitHub

在電腦 PowerShell：

```powershell
cd C:\Users\Jimmy\jianying-assistant

# 若還沒有 git
git init
git add streamlit_app.py requirements.txt src docs .streamlit .gitignore README.md
git add templates tests  # 可選
git status
git commit -m "Streamlit 模板介面：階段 1（可雲端部署）"

# 在 GitHub 網站新建一個空倉庫，例如 jianying-assistant
# 然後（把網址換成你的）：
git branch -M main
git remote add origin https://github.com/你的帳號/jianying-assistant.git
git push -u origin main
```

> 不要把含密碼的 `.env`、本機大型影片推上去。

---

## 步驟二：在 Streamlit Community Cloud 部署

1. 打開：https://share.streamlit.io/  
   （或搜尋 Streamlit Community Cloud）
2. 用 **GitHub** 登入
3. 按 **New app** / **Create app**
4. 填寫：
   | 欄位 | 填什麼 |
   |------|--------|
   | Repository | 你的 `帳號/jianying-assistant` |
   | Branch | `main` |
   | Main file path | **`streamlit_app.py`** |
   | App URL（可選） | 自己取一個好記的名字 |
5. 按 Deploy，等 1～3 分鐘安裝依賴

成功後會出現網址，用手機 Safari / Chrome 打開即可。

---

## 步驟三：手機怎麼用（模板保存）

**雲端網站關掉後，畫面上的設定會消失**（存在瀏覽器這次連線裡）。  
所以要「帶走設定」請用 JSON：

1. （階段 3 完成後）在網頁按 **下載模板 JSON**
2. 手機/電腦把檔案存進 **Google 雲端硬碟** 同步資料夾  
   例如：`我的雲端硬碟/剪映小助手模板/A01_心理學開頭.json`
3. 下次在外面要改模板：從雲端硬碟找出 JSON → 網頁按 **上傳載入**

階段 1 先把全域設定做穩；下載/上傳會在 **階段 3** 完整接上。

---

## 本機先預覽（可選）

```powershell
cd C:\Users\Jimmy\jianying-assistant
pip install -r requirements.txt
streamlit run streamlit_app.py
```

瀏覽器開 http://localhost:8501

若還要跑「寫剪映草稿」本機服務：

```powershell
pip install -r requirements-local.txt
python -m src.api
```

---

## 常見問題

| 問題 | 原因 | 解法 |
|------|------|------|
| Deploy 失敗、裝套件報錯 | `requirements.txt` 含 Windows 專用套件 | 確認只有 `streamlit`、`pydantic` |
| 找不到模組 `src` | 主檔路徑不對 | Main file 填 `streamlit_app.py` |
| 手機版面擠 | 正常，側邊欄可點左上角選單 | 階段 3 會再優化 |
| 想改程式 | 改完 `git push` | Cloud 會自動重新部署 |
| 雲端能寫進剪映嗎？ | **不能** | 剪映草稿一定要本機 Python；雲端只做「模板設定」 |

---

## 安全提醒

- 免費公開 App 時，**不要**在程式裡寫 API Token
- 模板 JSON 若含敏感路徑，請自管 Google Drive 權限
