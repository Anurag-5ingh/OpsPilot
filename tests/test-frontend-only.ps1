# Test frontend files without starting backend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpsPilot Frontend Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Testing frontend file structure..." -ForegroundColor Yellow

$errors = 0

# Check frontend files
$frontendFiles = @(
    "../frontend/index.html",
    "../frontend/js/main.js",
    "../frontend/js/utils.js",
    "../frontend/js/terminal.js",
    "../frontend/js/command-mode.js",
    "../frontend/js/troubleshoot-mode.js",
    "../frontend/css/style.css",
    "../frontend/assets/brain.svg"
)

foreach ($file in $frontendFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file - MISSING" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "Testing backend module structure..." -ForegroundColor Yellow

$backendFiles = @(
    "../ai_shell_agent/modules/command_generation/ai_handler.py",
    "../ai_shell_agent/modules/command_generation/prompts.py",
    "../ai_shell_agent/modules/troubleshooting/ai_handler.py",
    "../ai_shell_agent/modules/troubleshooting/prompts.py",
    "../ai_shell_agent/modules/troubleshooting/workflow_engine.py",
    "../ai_shell_agent/modules/ssh/client.py",
    "../ai_shell_agent/modules/ssh/session_manager.py",
    "../ai_shell_agent/modules/shared/conversation_memory.py",
    "../ai_shell_agent/modules/shared/utils.py"
)

foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file - MISSING" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "Testing Python syntax..." -ForegroundColor Yellow

# Test Python files for syntax errors
$pythonFiles = Get-ChildItem -Path "../ai_shell_agent" -Filter "*.py" -Recurse

foreach ($file in $pythonFiles) {
    $result = python -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $($file.Name) - Syntax OK" -ForegroundColor Green
    } else {
        Write-Host "❌ $($file.Name) - Syntax Error" -ForegroundColor Red
        Write-Host "   $result" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "✅ All structure tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ $errors errors found" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

exit $errors
