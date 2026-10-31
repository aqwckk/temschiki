# Запуск продукта: nginx на http://localhost:8080 и бэкенд на 127.0.0.1:8000
# Перед первым запуском: install-nginx.ps1, venv бэкенда и npm run build в mobile-prototype
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$nginxDir = Join-Path $env:LOCALAPPDATA "temschiki-nginx"
$nginxExe = Join-Path $nginxDir "nginx.exe"
$dist = Join-Path $root "mobile-prototype\dist"
$webLink = Join-Path $nginxDir "html-temschiki"
$python = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $nginxExe)) {
    throw "nginx не найден, запустите deploy\install-nginx.ps1"
}
if (-not (Test-Path $dist)) {
    throw "нет сборки фронта, выполните npm run build в mobile-prototype"
}

# nginx не открывает пути с кириллицей, поэтому сборку отдаем через ссылку в его папке
if (Test-Path $webLink) {
    # удаляем только саму ссылку, Remove-Item -Recurse снес бы и сборку
    [System.IO.Directory]::Delete($webLink)
}
New-Item -ItemType Junction -Path $webLink -Target $dist | Out-Null
Copy-Item (Join-Path $PSScriptRoot "nginx.conf") (Join-Path $nginxDir "conf\temschiki.conf") -Force

Start-Process -FilePath $nginxExe -ArgumentList "-p", "$nginxDir\", "-c", "conf/temschiki.conf" -WorkingDirectory $nginxDir -WindowStyle Hidden
Write-Host "nginx: http://localhost:8080"

try {
    Push-Location (Join-Path $root "backend")
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
    & $nginxExe -p "$nginxDir\" -s quit
    Write-Host "nginx остановлен"
}
