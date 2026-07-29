# 啟動剪映小助手本地 API（階段 2）
# 用法：在專案根目錄執行  .\scripts\start_server.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:JY_API_HOST = if ($env:JY_API_HOST) { $env:JY_API_HOST } else { "127.0.0.1" }
$env:JY_API_PORT = if ($env:JY_API_PORT) { $env:JY_API_PORT } else { "8765" }

Write-Host "專案目錄: $Root"
Write-Host "服務地址: http://$($env:JY_API_HOST):$($env:JY_API_PORT)"
Write-Host "API 文件: http://$($env:JY_API_HOST):$($env:JY_API_PORT)/docs"
Write-Host "按 Ctrl+C 停止服務"
Write-Host ""

python -m src.api
