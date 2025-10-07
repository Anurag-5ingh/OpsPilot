@echo off
echo ========================================
echo OpsPilot - Commit Troubleshooting Feature
echo ========================================
echo.

cd /d "c:\Users\amren\OpsPilot-main"

echo Checking Git installation...
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git is not installed or not in PATH
    echo.
    echo Please install Git from: https://git-scm.com/download/win
    echo Or run: winget install Git.Git
    echo.
    pause
    exit /b 1
)

echo [OK] Git found
echo.

echo Current Git Status:
echo -------------------
git status
echo.

echo.
echo Choose an option:
echo 1. Commit to MAIN branch (direct push)
echo 2. Create NEW FEATURE BRANCH (recommended)
echo 3. Exit
echo.
set /p choice="Enter choice (1, 2, or 3): "

if "%choice%"=="1" goto commit_main
if "%choice%"=="2" goto commit_branch
if "%choice%"=="3" goto end

:commit_main
echo.
echo [INFO] Committing to MAIN branch...
echo.

git add opsPilot/ai_shell_agent/prompt_troubleshoot.py
git add opsPilot/ai_shell_agent/ai_troubleshoot.py
git add opsPilot/ai_shell_agent/troubleshoot_runner.py
git add opsPilot/TROUBLESHOOT_FEATURE.md
git add opsPilot/test_troubleshoot.py
git add opsPilot/app.py
git add opsPilot/frontend/index.html
git add opsPilot/frontend/app.js
git add opsPilot/frontend/style.css
git add GIT_COMMIT_GUIDE.md
git add COMMIT_CHANGES.bat

echo [OK] Files staged
echo.

git commit -m "feat: Add AI-driven troubleshooting feature - Add separate troubleshooting mode with dedicated UI toggle - Implement multi-step workflow (diagnostics, fixes, verification) - Create specialized AI prompt for error analysis - Add /troubleshoot and /troubleshoot/execute endpoints - Include risk level assessment and safety confirmations - Maintain complete separation from existing command generation"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Commit failed
    pause
    exit /b 1
)

echo [OK] Committed successfully
echo.

echo Pushing to origin/main...
git push origin main

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Push failed - check authentication
    echo.
    echo You may need to:
    echo - Configure Git credentials
    echo - Use Personal Access Token
    echo - Or use GitHub Desktop
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Changes pushed to main branch!
echo.
echo View your changes at: https://github.com/Anurag-5ingh/OpsPilot
echo.
goto end

:commit_branch
echo.
set /p branchname="Enter new branch name (e.g., feature/troubleshooting): "

if "%branchname%"=="" (
    echo [ERROR] Branch name cannot be empty
    pause
    exit /b 1
)

echo [INFO] Creating and switching to branch: %branchname%
git checkout -b %branchname%

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create branch
    pause
    exit /b 1
)

echo [OK] Branch created
echo.

git add opsPilot/ai_shell_agent/prompt_troubleshoot.py
git add opsPilot/ai_shell_agent/ai_troubleshoot.py
git add opsPilot/ai_shell_agent/troubleshoot_runner.py
git add opsPilot/TROUBLESHOOT_FEATURE.md
git add opsPilot/test_troubleshoot.py
git add opsPilot/app.py
git add opsPilot/frontend/index.html
git add opsPilot/frontend/app.js
git add opsPilot/frontend/style.css
git add GIT_COMMIT_GUIDE.md
git add COMMIT_CHANGES.bat

echo [OK] Files staged
echo.

git commit -m "feat: Add AI-driven troubleshooting feature - Add separate troubleshooting mode with dedicated UI toggle - Implement multi-step workflow (diagnostics, fixes, verification) - Create specialized AI prompt for error analysis - Add /troubleshoot and /troubleshoot/execute endpoints - Include risk level assessment and safety confirmations - Maintain complete separation from existing command generation"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Commit failed
    pause
    exit /b 1
)

echo [OK] Committed successfully
echo.

echo Pushing to origin/%branchname%...
git push origin %branchname%

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Push failed - check authentication
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Changes pushed to branch: %branchname%
echo.
echo Next steps:
echo 1. Go to: https://github.com/Anurag-5ingh/OpsPilot
echo 2. Create a Pull Request to merge %branchname% into main
echo.
goto end

:end
echo.
pause
