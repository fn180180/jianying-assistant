# 本機預覽「剪映小助手」Streamlit 介面（與雲端同一入口）
# 用法：在專案根目錄執行  .\scripts\start_streamlit.ps1
# 正式線上請部署到 Streamlit Community Cloud，見 docs/STREAMLIT_CLOUD_DEPLOY.md

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "專案目錄: $Root" -ForegroundColor Cyan
Write-Host "啟動 Streamlit（入口 streamlit_app.py）..." -ForegroundColor Green

python -m streamlit run streamlit_app.py --server.headless true
