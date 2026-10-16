# 抖音雲端視訊分析｜ChatGPT 素材模式

**不需要開著本地電腦；不需要 Gemini API 金鑰。** GitHub Actions 雲端取得抖音影片、每秒截圖、中文 OCR、語音轉寫，輸出供 ChatGPT 讀取的分鏡圖及逐字稿。影片與音訊只在 GitHub Runner 暫存，執行完成即清理。

## 使用方式
1. **目前實測最穩定的是 AnyToCopy 產生的 MP4 直鏈。**抖音短連結模式已加入原生手機頁與公開 API 雙路線，但 GitHub Runner 可能被平台／第三方阻擋 HTTP 403，尚未完成實測成功。不用在手機下載 MP4，只需複製直鏈。\n2. 查看此儲存庫 [Actions](https://github.com/fn180180/jianying-assistant/actions) 的 **Analyze Douyin in Cloud**。
3. 該工作流程先在 feature/douyin-cloud-analyzer 分支用「第 14 天」作品執行煙霧測試，測試後再決定是否合併進 main；**目前不更動 main**。GitHub 只有預設分支含 workflow_dispatch 的工作流程，才會在一般 Actions 頁面顯示手動執行入口。
4. 合併且正式啟用後，按 Run workflow 貼抖音分享連結或 AnyToCopy 的 MP4 直鏈。
5. 在執行記錄下載 `douyin-visual-analysis-...` Artifact，其中有 **report.md、report.json、transcript.txt、ocr.json** 及 **visual_evidence/*.jpg**。
6. 將 Artifact 畫面與文字交給 ChatGPT，即可辨認左右不同人物、逐餐食物與重量，按食材另行估算熱量。OCR、ASR 可能有誤，不能只靠文字武斷判定。

## 隱私、安全與成本
- 僅接受抖音及相關受信任 CDN 網域的 HTTPS 連結；使用第三方解析 API `z.gao.gs`，服務不保證可用。
- GitHub Runner 隨任務清除 MP4、聲音、原始逐秒截圖。Artifact 為**臨時衍生 JPG＋文字**，保留 1 天；不保存整支影片。
- 目前所在的既有儲存庫是公開的，故**執行紀錄和報告可能被他人讀取**；正式使用建議搬到新建的私人儲存庫。
- GitHub-hosted Actions 有免費額度與執行等待，無法保證速度。受版權／授權及平台條款約束。
- 無 AI API 費用，但這是供 ChatGPT 分析的**素材包**，不是完全無人值守的 AI 影片理解。
- 不須將 Google/Gemini 金鑰放在儲存庫。\n## GitHub 實際測試（2026-10-12）\n\n- **成功：** [第二次 GitHub Actions 雲端測試](https://github.com/fn180180/jianying-assistant/actions/runs/38275767763) 使用抖音原始 MP4 串流，成功下載 24.73 MB、抽出 123 張影格、取得 110 個 OCR 時間點、產生 6 張 JPG 分鏡圖與逐字稿；MP4/音訊/原始逐格檔案已從 Runner 暫存移除。GitHub Artifact 可由 ChatGPT GitHub 插件下載讀取。\n- **未通過：** [短連結實測](https://github.com/fn180180/jianying-assistant/actions/runs/38276460954) 顯示原生分享頁 `videoInfoRes.item_list` 為空，第三方解析 API 則回 HTTP 403。故目前不能聲稱短連結已可在 GitHub Runner 全自動解析。先從 AnyToCopy 複製 MP4 直鏈使用。\n- **注意：** 本功能分支無 `workflow_dispatch` 一般手機手動啟動入口，必須合併到 main 或移植新私人儲存庫後才會出現。\n