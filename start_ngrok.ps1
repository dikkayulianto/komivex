# start_ngrok.ps1
# Script helper to download and run ngrok locally

$Url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$ZipFile = "$PSScriptRoot\ngrok.zip"
$DestDir = "$PSScriptRoot"

if (-not (Test-Path "$DestDir\ngrok.exe")) {
    Write-Host "Downloading ngrok stable build for Windows..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $Url -OutFile $ZipFile -UseBasicParsing
    
    Write-Host "Extracting archive..." -ForegroundColor Yellow
    Expand-Archive -Path $ZipFile -DestinationPath $DestDir -Force
    
    Remove-Item $ZipFile -Force
    Write-Host "ngrok binary set up successfully!" -ForegroundColor Green
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Cara menggunakan ngrok:" -ForegroundColor Cyan
Write-Host "1. Dapatkan Auth Token gratis dari dashboard: https://dashboard.ngrok.com" -ForegroundColor White
Write-Host "2. Daftarkan token Anda dengan perintah:" -ForegroundColor White
Write-Host "   ./ngrok.exe config add-authtoken <TOKEN_ANDA>" -ForegroundColor Yellow
Write-Host "3. Jalankan kembali script ini untuk meluncurkan preview." -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan

# Check if ngrok configuration file exists or prompt to setup
Write-Host "Membuka ngrok di jendela baru..." -ForegroundColor Green
Start-Process -FilePath "$DestDir\ngrok.exe" -ArgumentList "http", "8080"
