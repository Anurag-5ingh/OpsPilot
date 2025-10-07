# Git Commit Guide - Troubleshooting Feature

## Prerequisites
You need Git installed on your system. If not installed:
- Download from: https://git-scm.com/download/win
- Or install via: `winget install Git.Git`

## Files Changed/Added

### New Files (7 files)
1. `opsPilot/ai_shell_agent/prompt_troubleshoot.py`
2. `opsPilot/ai_shell_agent/ai_troubleshoot.py`
3. `opsPilot/ai_shell_agent/troubleshoot_runner.py`
4. `opsPilot/TROUBLESHOOT_FEATURE.md`
5. `opsPilot/test_troubleshoot.py`
6. `opsPilot/GIT_COMMIT_GUIDE.md` (this file)

### Modified Files (4 files)
1. `opsPilot/app.py`
2. `opsPilot/frontend/index.html`
3. `opsPilot/frontend/app.js`
4. `opsPilot/frontend/style.css`

## Option 1: Commit to Main Branch (Recommended if you're the only developer)

Open PowerShell or Git Bash in `c:\Users\amren\OpsPilot-main\` and run:

```powershell
# Navigate to repository root
cd c:\Users\amren\OpsPilot-main

# Check current status
git status

# Add all new and modified files
git add opsPilot/ai_shell_agent/prompt_troubleshoot.py
git add opsPilot/ai_shell_agent/ai_troubleshoot.py
git add opsPilot/ai_shell_agent/troubleshoot_runner.py
git add opsPilot/TROUBLESHOOT_FEATURE.md
git add opsPilot/test_troubleshoot.py
git add opsPilot/app.py
git add opsPilot/frontend/index.html
git add opsPilot/frontend/app.js
git add opsPilot/frontend/style.css

# Or add all changes at once
git add .

# Commit with descriptive message
git commit -m "feat: Add AI-driven troubleshooting feature

- Add separate troubleshooting mode with dedicated UI toggle
- Implement multi-step workflow (diagnostics, fixes, verification)
- Create specialized AI prompt for error analysis
- Add /troubleshoot and /troubleshoot/execute endpoints
- Include risk level assessment and safety confirmations
- Maintain complete separation from existing command generation feature
- Add comprehensive documentation and test script"

# Push to main branch
git push origin main
```

## Option 2: Create New Feature Branch (Recommended for team collaboration)

```powershell
# Navigate to repository root
cd c:\Users\amren\OpsPilot-main

# Create and switch to new branch
git checkout -b feature/troubleshooting

# Add all changes
git add .

# Commit
git commit -m "feat: Add AI-driven troubleshooting feature

- Add separate troubleshooting mode with dedicated UI toggle
- Implement multi-step workflow (diagnostics, fixes, verification)
- Create specialized AI prompt for error analysis
- Add /troubleshoot and /troubleshoot/execute endpoints
- Include risk level assessment and safety confirmations
- Maintain complete separation from existing command generation feature
- Add comprehensive documentation and test script"

# Push to new branch
git push origin feature/troubleshooting

# Then create Pull Request on GitHub to merge into main
```

## Option 3: Using GitHub Desktop (GUI)

If you prefer a graphical interface:

1. Download GitHub Desktop: https://desktop.github.com/
2. Open the repository in GitHub Desktop
3. You'll see all changed files listed
4. Write commit message: "feat: Add AI-driven troubleshooting feature"
5. Click "Commit to main" (or create new branch first)
6. Click "Push origin"

## Verify Changes Were Pushed

After pushing, verify on GitHub:
1. Go to: https://github.com/Anurag-5ingh/OpsPilot
2. Check if your commit appears in the commit history
3. Verify all files are present

## Troubleshooting

### If you get "Git not found" error:
```powershell
# Install Git via winget
winget install Git.Git

# Or download installer from:
# https://git-scm.com/download/win

# After installation, restart PowerShell
```

### If you get authentication error:
```powershell
# Configure Git credentials
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# You may need to authenticate via:
# - Personal Access Token (recommended)
# - SSH key
# - GitHub Desktop (handles auth automatically)
```

### If you get merge conflicts:
```powershell
# Pull latest changes first
git pull origin main

# Resolve any conflicts
# Then commit and push
```

## Quick Commands Summary

```powershell
# One-liner to commit everything to main
cd c:\Users\amren\OpsPilot-main && git add . && git commit -m "feat: Add troubleshooting feature" && git push origin main

# One-liner to create feature branch
cd c:\Users\amren\OpsPilot-main && git checkout -b feature/troubleshooting && git add . && git commit -m "feat: Add troubleshooting feature" && git push origin feature/troubleshooting
```

## What Happens Next?

After pushing:
1. Changes will be visible on GitHub
2. Other collaborators can pull your changes
3. You can create a Pull Request if using feature branch
4. CI/CD pipelines will run (if configured)

## Need Help?

If you encounter any issues:
1. Check git status: `git status`
2. Check git log: `git log --oneline -5`
3. Check remote: `git remote -v`
4. Check current branch: `git branch`
