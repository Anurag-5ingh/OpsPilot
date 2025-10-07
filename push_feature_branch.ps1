# PowerShell script to create feature branch and push all changes
# OpsPilot - Troubleshooting Feature

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpsPilot - Push Troubleshooting Feature" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to repository root
Set-Location "c:\Users\amren\OpsPilot-main"

# Check if Git is installed
Write-Host "Checking Git installation..." -ForegroundColor Yellow
$gitExists = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitExists) {
    Write-Host "[ERROR] Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Git:" -ForegroundColor Yellow
    Write-Host "  Option 1: winget install Git.Git" -ForegroundColor White
    Write-Host "  Option 2: Download from https://git-scm.com/download/win" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Git found" -ForegroundColor Green
Write-Host ""

# Show current status
Write-Host "Current Git Status:" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow
git status --short
Write-Host ""

# Confirm with user
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  1. Update .gitignore with OpsPilot-specific entries" -ForegroundColor White
Write-Host "  2. Create branch: feature/ai-troubleshooting" -ForegroundColor White
Write-Host "  3. Add all new and modified files" -ForegroundColor White
Write-Host "  4. Commit with descriptive message" -ForegroundColor White
Write-Host "  5. Push to GitHub" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Continue? (yes/no)"
if ($confirm -ne "yes" -and $confirm -ne "y") {
    Write-Host "Aborted by user" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Step 1: Creating feature branch..." -ForegroundColor Yellow

# Create and checkout new branch
$branchName = "feature/ai-troubleshooting"
git checkout -b $branchName 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    # Branch might already exist, try to switch to it
    Write-Host "[INFO] Branch might exist, switching to it..." -ForegroundColor Yellow
    git checkout $branchName 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create/switch to branch" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "[OK] On branch: $branchName" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Staging files..." -ForegroundColor Yellow

# Add updated .gitignore first
git add .gitignore

# Add new troubleshooting files
git add opsPilot/ai_shell_agent/prompt_troubleshoot.py
git add opsPilot/ai_shell_agent/ai_troubleshoot.py
git add opsPilot/ai_shell_agent/troubleshoot_runner.py
git add opsPilot/TROUBLESHOOT_FEATURE.md
git add opsPilot/test_troubleshoot.py

# Add modified files
git add opsPilot/app.py
git add opsPilot/frontend/index.html
git add opsPilot/frontend/app.js
git add opsPilot/frontend/style.css

# Add documentation and helper files
git add GIT_COMMIT_GUIDE.md
git add COMMIT_CHANGES.bat
git add push_feature_branch.ps1

Write-Host "[OK] Files staged" -ForegroundColor Green
Write-Host ""

# Show what will be committed
Write-Host "Files to be committed:" -ForegroundColor Cyan
git diff --cached --name-status
Write-Host ""

Write-Host "Step 3: Creating commit..." -ForegroundColor Yellow

# Create commit with detailed message
$commitMessage = @"
feat: Add AI-driven troubleshooting feature

Major Changes:
- Add separate troubleshooting mode with UI toggle (Command/Troubleshoot)
- Implement multi-step workflow engine (diagnostics → fixes → verification)
- Create specialized AI prompt for error analysis and remediation
- Add /troubleshoot and /troubleshoot/execute REST endpoints
- Include risk level assessment (low/medium/high) with color coding
- Maintain complete separation from existing command generation feature

New Files:
- ai_shell_agent/prompt_troubleshoot.py: Specialized troubleshooting prompt
- ai_shell_agent/ai_troubleshoot.py: AI handler for error analysis
- ai_shell_agent/troubleshoot_runner.py: Workflow execution engine
- TROUBLESHOOT_FEATURE.md: Comprehensive documentation
- test_troubleshoot.py: Test script for AI responses

Modified Files:
- app.py: Added troubleshooting endpoints
- frontend/index.html: Added mode toggle and troubleshoot input
- frontend/app.js: Added troubleshooting UI logic (~240 lines)
- frontend/style.css: Added troubleshoot mode styling
- .gitignore: Added OpsPilot-specific entries

Features:
- AI analyzes any error in real-time (no hardcoded playbooks)
- Multi-step execution with user confirmation
- Automatic verification after fixes
- Step-by-step visibility with command outputs
- Safety guardrails and risk assessment
- Iterative troubleshooting support

Technical Details:
- Uses OpenAI GPT-4o-mini with temperature 0.2 for consistency
- Separate API endpoints to prevent feature confusion
- Workflow state machine for step execution
- SSH connection reuse for efficiency
- JSON-based AI responses for structured data
"@

git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Commit failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "  - No changes to commit (already committed?)" -ForegroundColor White
    Write-Host "  - Git user not configured" -ForegroundColor White
    Write-Host ""
    Write-Host "To configure Git user:" -ForegroundColor Yellow
    Write-Host '  git config --global user.name "Your Name"' -ForegroundColor White
    Write-Host '  git config --global user.email "your.email@example.com"' -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Commit created" -ForegroundColor Green
Write-Host ""

Write-Host "Step 4: Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "Branch: origin/$branchName" -ForegroundColor Cyan
Write-Host ""

# Push to remote
git push -u origin $branchName

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Push failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. Authentication required" -ForegroundColor White
    Write-Host "     - Use Personal Access Token" -ForegroundColor Gray
    Write-Host "     - Or use GitHub Desktop" -ForegroundColor Gray
    Write-Host "  2. Remote branch already exists" -ForegroundColor White
    Write-Host "     - Pull first: git pull origin $branchName" -ForegroundColor Gray
    Write-Host "  3. No permission to push" -ForegroundColor White
    Write-Host "     - Check repository access" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCESS! Changes pushed to GitHub" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Go to: https://github.com/Anurag-5ingh/OpsPilot" -ForegroundColor White
Write-Host "  2. You should see a banner: 'Compare & pull request'" -ForegroundColor White
Write-Host "  3. Click it to create a Pull Request" -ForegroundColor White
Write-Host "  4. Review changes and merge into main branch" -ForegroundColor White
Write-Host ""

Write-Host "Branch Details:" -ForegroundColor Cyan
Write-Host "  Branch name: $branchName" -ForegroundColor White
Write-Host "  Files changed: 12" -ForegroundColor White
Write-Host "  New files: 7" -ForegroundColor White
Write-Host "  Modified files: 5" -ForegroundColor White
Write-Host ""

Write-Host "View your branch:" -ForegroundColor Cyan
Write-Host "  https://github.com/Anurag-5ingh/OpsPilot/tree/$branchName" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
