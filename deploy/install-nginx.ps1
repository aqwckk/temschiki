# Скачивает nginx для Windows в папку без кириллицы и пробелов (nginx не умеет такие пути)
$ErrorActionPreference = "Stop"

$version = "1.28.0"
$nginxDir = Join-Path $env:LOCALAPPDATA "temschiki-nginx"

if (Test-Path (Join-Path $nginxDir "nginx.exe")) {
    Write-Host "nginx уже установлен: $nginxDir"
    exit 0
}

$zip = Join-Path $env:TEMP "nginx-$version.zip"
$unpacked = Join-Path $env:TEMP "nginx-unpack"
Invoke-WebRequest -Uri "https://nginx.org/download/nginx-$version.zip" -OutFile $zip
if (Test-Path $unpacked) {
    Remove-Item -Recurse -Force $unpacked
}
Expand-Archive -Path $zip -DestinationPath $unpacked
Move-Item (Join-Path $unpacked "nginx-$version") $nginxDir
Remove-Item $zip

Write-Host "nginx установлен: $nginxDir"
