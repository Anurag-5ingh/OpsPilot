# OpsPilot E2E Tests

End-to-end tests for OpsPilot using Playwright.

## Setup

1. Install Node.js dependencies:
```bash
cd tests
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install
```

## Running Tests

### Option 1: Using PowerShell script (Recommended)
```powershell
cd tests
.\run-tests.ps1
```
This will automatically start the Flask app, run tests, and stop the app.

### Option 2: Manual
1. Start Flask app in one terminal:
```bash
cd ..
python app.py
```

2. Run tests in another terminal:
```bash
cd tests
npm test
```

### Run tests in headed mode (see browser):
```bash
npm run test:headed
```

### Run tests in debug mode:
```bash
npm run test:debug
```

### Run tests with UI:
```bash
npm run test:ui
```

### View test report:
```bash
npm run report
```

## Test Structure

- `01-app-loads.spec.js` - Basic application loading tests
- `02-api-endpoints.spec.js` - API endpoint tests
- `03-command-mode-ui.spec.js` - Command generation UI tests
- `04-troubleshoot-mode-ui.spec.js` - Troubleshooting UI tests
- `05-terminal.spec.js` - Terminal functionality tests
- `06-integration.spec.js` - Full integration workflow tests

## What's Tested

### Application Loading
- ✅ Login page loads correctly
- ✅ Validation for empty credentials
- ✅ All assets (CSS, JS, images) load

### API Endpoints
- ✅ POST /ask - Command generation
- ✅ POST /troubleshoot - Error analysis
- ✅ POST /troubleshoot/execute - Workflow execution
- ✅ GET /ssh/list - SSH connections
- ✅ POST /ssh/save - Save SSH info
- ✅ GET / - Redirect to /opspilot

### Command Mode
- ✅ Default mode is Command
- ✅ Generate commands from natural language
- ✅ Show confirmation buttons
- ✅ Handle Enter key submission
- ✅ Switch between modes

### Troubleshoot Mode
- ✅ Show troubleshoot input area
- ✅ Analyze errors and show plan
- ✅ Display risk levels (low/medium/high)
- ✅ Execute workflow steps
- ✅ Handle Ctrl+Enter submission

### Terminal
- ✅ Terminal container visible
- ✅ Control buttons (Clear, Reconnect)
- ✅ Terminal header

### Integration
- ✅ Complete command generation workflow
- ✅ Complete troubleshooting workflow
- ✅ Mode switching during workflow
- ✅ Error handling

## Notes

- Tests use mocked API responses for consistency
- The Flask app is automatically started before tests
- Tests run in Chromium by default
- Screenshots and videos are captured on failure
