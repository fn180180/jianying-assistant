# 給 Coze 串接用的啟動腳本（階段 3）
# 1) 設定 Token（若尚未設定）
# 2) 啟動本機 API
# 3) 提示你另外開隧道

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:JY_API_HOST = if ($env:JY_API_HOST) { $env:JY_API_HOST } else { "127.0.0.1" }
$env:JY_API_PORT = if ($env:JY_API_PORT) { $env:JY_API_PORT } else { "8765" }

if (-not $env:JY_API_TOKEN -or $env:JY_API_TOKEN.Trim() -eq "") {
    # 產生臨時 Token 並顯示（重開服務會變；正式請自己固定一個）
    $env:JY_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(24))"
    Write-Host ""
    Write-Host "已自動產生 JY_API_TOKEN（請複製到 Coze Header）：" -ForegroundColor Yellow
    Write-Host "  $($env:JY_API_TOKEN)" -ForegroundColor Cyan
    Write-Host "  Authorization: Bearer $($env:JY_API_TOKEN)" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "使用既有 JY_API_TOKEN（已設定，不在此顯示完整值）" -ForegroundColor Green
}

Write-Host "本機 API: http://$($env:JY_API_HOST):$($env:JY_API_PORT)"
Write-Host "Coze 建議路徑: /v1/coze/convert"
Write-Host "文件: docs\COZE_INTEGRATION.md"
Write-Host ""
Write-Host "下一步（另開終端做隧道，擇一）：" -ForegroundColor Yellow
Write-Host "  cpolar http $($env:JY_API_PORT)"
Write-Host "  cloudflared tunnel --url http://127.0.0.1:$($env:JY_API_PORT)"
Write-Host ""
Write-Host "按 Ctrl+C 停止服務"
Write-Host ""

python -m src.api
