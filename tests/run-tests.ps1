# PowerShell script to run Playwright tests
# Starts the Flask app in background and runs tests

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpsPilot E2E Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if app is already running
$appRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    $appRunning = $true
    Write-Host "✅ Flask app is already running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Flask app is not running" -ForegroundColor Yellow
}

# Start Flask app if not running
$flaskProcess = $null
if (-not $appRunning) {
    Write-Host "Starting Flask app..." -ForegroundColor Yellow
    Set-Location ".."
    $flaskProcess = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru -WindowStyle Hidden
    Set-Location "tests"
    
    Write-Host "Waiting for Flask app to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Verify app started
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080" -Method GET -TimeoutSec 5
        Write-Host "✅ Flask app started successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to start Flask app" -ForegroundColor Red
        if ($flaskProcess) {
            Stop-Process -Id $flaskProcess.Id -Force
        }
        exit 1
    }
}

Write-Host ""
Write-Host "Running Playwright tests..." -ForegroundColor Cyan
Write-Host ""

# Run tests
npm test

$testExitCode = $LASTEXITCODE

Write-Host ""
if ($testExitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ All tests passed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ Some tests failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "View detailed report:" -ForegroundColor Yellow
    Write-Host "  npx playwright show-report" -ForegroundColor White
}

# Cleanup: Stop Flask app if we started it
if ($flaskProcess) {
    Write-Host ""
    Write-Host "Stopping Flask app..." -ForegroundColor Yellow
    Stop-Process -Id $flaskProcess.Id -Force
    Write-Host "✅ Flask app stopped" -ForegroundColor Green
}

Write-Host ""
exit $testExitCode
