# 抖音雲端視訊分析｜ChatGPT 素材模式

**不需要開著本地電腦；不需要 Gemini API 金鑰。** GitHub Actions 雲端取得抖音影片、每秒截圖、中文 OCR、語音轉寫，輸出供 ChatGPT 讀取的分鏡圖及逐字稿。影片與音訊只在 GitHub Runner 暫存，執行完成即清理。

## 使用方式
1. 查看此儲存庫 [Actions](https://github.com/fn180180/jianying-assistant/actions) 的 **Analyze Douyin in Cloud**。
2. 該工作流程先在 feature/douyin-cloud-analyzer 分支用「第 14 天」作品執行煙霧測試，測試後再決定是否合併進 main；**目前不更動 main**。GitHub 只有預設分支含 workflow_dispatch 的工作流程，才會在一般 Actions 頁面顯示手動執行入口。
3. 合併且正式啟用後，按 Run workflow 貼抖音分享連結或 AnyToCopy 的 MP4 直鏈。
4. 在執行記錄下載 `douyin-visual-analysis-...` Artifact，其中有 **report.md、report.json、transcript.txt、ocr.json** 及 **visual_evidence/*.jpg**。
5. 將 Artifact 畫面與文字交給 ChatGPT，即可辨認左右不同人物、逐餐食物與重量，按食材另行估算熱量。OCR、ASR 可能有誤，不能只靠文字武斷判定。

## 隱私、安全與成本
- 僅接受抖音及相關受信任 CDN 網域的 HTTPS 連結；使用第三方解析 API `z.gao.gs`，服務不保證可用。
- GitHub Runner 隨任務清除 MP4、聲音、原始逐秒截圖。Artifact 為**臨時衍生 JPG＋文字**，保留 1 天；不保存整支影片。
- 目前所在的既有儲存庫是公開的，故**執行紀錄和報告可能被他人讀取**；正式使用建議搬到新建的私人儲存庫。
- GitHub-hosted Actions 有免費額度與執行等待，無法保證速度。受版權／授權及平台條款約束。
- 無 AI API 費用，但這是供 ChatGPT 分析的**素材包**，不是完全無人值守的 AI 影片理解。
- 不須將 Google/Gemini 金鑰放在儲存庫。