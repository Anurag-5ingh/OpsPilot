# Step-by-Step Instructions to Push Feature Branch

## ⚠️ Git Not Installed

Git is not currently installed on your system. Follow these steps:

---

## Step 1: Install Git

### Option A: Using winget (Recommended - Fastest)
Open PowerShell as Administrator and run:
```powershell
winget install Git.Git
```

### Option B: Download Installer
1. Go to: https://git-scm.com/download/win
2. Download the installer
3. Run the installer (use default settings)
4. Restart PowerShell after installation

---

## Step 2: Configure Git (First Time Only)

Open PowerShell and run:
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Replace with your actual name and email.

---

## Step 3: Run the Automated Script

After Git is installed, simply run:

### Option A: Double-click this file
```
c:\Users\amren\OpsPilot-main\push_feature_branch.ps1
```

Right-click → "Run with PowerShell"

### Option B: Run from PowerShell
```powershell
cd c:\Users\amren\OpsPilot-main
.\push_feature_branch.ps1
```

The script will:
- ✅ Create branch: `feature/ai-troubleshooting`
- ✅ Add all 12 changed files
- ✅ Commit with detailed message
- ✅ Push to GitHub

---

## Step 4: Manual Alternative (If Script Fails)

If the script doesn't work, run these commands manually:

```powershell
# Navigate to repository
cd c:\Users\amren\OpsPilot-main

# Create and switch to new branch
git checkout -b feature/ai-troubleshooting

# Add all changes
git add .gitignore
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
git add push_feature_branch.ps1
git add PUSH_INSTRUCTIONS.md

# Commit
git commit -m "feat: Add AI-driven troubleshooting feature

- Add separate troubleshooting mode with UI toggle
- Implement multi-step workflow (diagnostics, fixes, verification)
- Create specialized AI prompt for error analysis
- Add /troubleshoot and /troubleshoot/execute endpoints
- Include risk level assessment and safety confirmations
- Maintain complete separation from existing command generation
- Update .gitignore with OpsPilot-specific entries"

# Push to GitHub
git push -u origin feature/ai-troubleshooting
```

---

## Step 5: Create Pull Request on GitHub

After pushing:

1. Go to: https://github.com/Anurag-5ingh/OpsPilot
2. You'll see a yellow banner: **"Compare & pull request"**
3. Click the button
4. Review the changes
5. Add description (optional)
6. Click **"Create pull request"**
7. Merge the PR into main branch

---

## Files Being Committed (12 files)

### New Files (8):
1. ✅ `opsPilot/ai_shell_agent/prompt_troubleshoot.py` - Troubleshooting AI prompt
2. ✅ `opsPilot/ai_shell_agent/ai_troubleshoot.py` - AI handler
3. ✅ `opsPilot/ai_shell_agent/troubleshoot_runner.py` - Workflow engine
4. ✅ `opsPilot/TROUBLESHOOT_FEATURE.md` - Documentation
5. ✅ `opsPilot/test_troubleshoot.py` - Test script
6. ✅ `GIT_COMMIT_GUIDE.md` - Git guide
7. ✅ `COMMIT_CHANGES.bat` - Batch script
8. ✅ `push_feature_branch.ps1` - PowerShell script

### Modified Files (4):
1. ✅ `opsPilot/app.py` - Added troubleshooting endpoints
2. ✅ `opsPilot/frontend/index.html` - Added mode toggle
3. ✅ `opsPilot/frontend/app.js` - Added troubleshooting logic
4. ✅ `opsPilot/frontend/style.css` - Added styling
5. ✅ `.gitignore` - Added OpsPilot-specific entries

---

## Troubleshooting

### Authentication Error
If you get an authentication error when pushing:

1. **Use Personal Access Token (PAT)**:
   - Go to: https://github.com/settings/tokens
   - Generate new token (classic)
   - Select scopes: `repo` (full control)
   - Copy the token
   - When Git asks for password, paste the token

2. **Or use GitHub Desktop**:
   - Download: https://desktop.github.com/
   - It handles authentication automatically

### Branch Already Exists
If the branch already exists:
```powershell
git checkout feature/ai-troubleshooting
git pull origin feature/ai-troubleshooting
# Then add and commit as above
git push origin feature/ai-troubleshooting
```

### Permission Denied
Make sure you have write access to the repository.

---

## Quick Summary

1. **Install Git** → `winget install Git.Git`
2. **Configure Git** → Set name and email
3. **Run Script** → `.\push_feature_branch.ps1`
4. **Create PR** → On GitHub website
5. **Merge** → Into main branch

---

## Need Help?

If you encounter any issues:
- Check Git version: `git --version`
- Check current branch: `git branch`
- Check remote: `git remote -v`
- Check status: `git status`

Or use GitHub Desktop for a GUI experience: https://desktop.github.com/
