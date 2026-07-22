# PowerShell Dev Script for Windows
Write-Host "Starting GLM Usage Monitor Backend and Frontend..." -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"

# Check Python environment
if (Test-Path "$backendPath\venv\Scripts\Activate.ps1") {
    $backendCmd = "cd '$backendPath'; .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload --port 8000"
} else {
    $backendCmd = "cd '$backendPath'; python -m uvicorn app.main:app --reload --port 8000"
}

$frontendCmd = "cd '$frontendPath'; npm run dev"

Write-Host "Launching Backend (FastAPI) on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "Launching Frontend (Vite) on port 5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Both development servers launched in separate windows!" -ForegroundColor Cyan
