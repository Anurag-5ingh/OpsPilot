// Test 4: Troubleshooting Mode UI
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - Troubleshooting Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/opspilot');
    
    // Mock connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Connect to server
    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)', { timeout: 5000 });
    
    // Switch to Troubleshoot mode
    await page.click('#mode-troubleshoot');
  });

  test('should show troubleshoot input area', async ({ page }) => {
    await expect(page.locator('#troubleshoot-input-container')).toBeVisible();
    await expect(page.locator('#error-input')).toBeVisible();
    await expect(page.locator('#troubleshoot-btn')).toBeVisible();
  });

  test('should analyze error and show troubleshooting plan', async ({ page }) => {
    // Mock troubleshoot API
    await page.route('/troubleshoot', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analysis: 'Port 80 is already in use by another process',
          diagnostic_commands: ['sudo lsof -i :80', 'sudo netstat -tlnp | grep :80'],
          fix_commands: ['sudo systemctl stop apache2', 'sudo systemctl start nginx'],
          verification_commands: ['sudo systemctl status nginx'],
          reasoning: 'Apache is likely running on port 80. Stop it first, then start nginx.',
          risk_level: 'medium',
          requires_confirmation: true
        })
      });
    });

    // Enter error message
    await page.fill('#error-input', 'nginx: [emerg] bind() to 0.0.0.0:80 failed');
    await page.click('#troubleshoot-btn');

    // Wait for analysis
    await page.waitForSelector('.troubleshoot-analysis', { timeout: 10000 });

    // Should show analysis
    await expect(page.locator('.troubleshoot-analysis')).toContainText('Port 80 is already in use');

    // Should show risk level
    await expect(page.locator('.risk-medium')).toBeVisible();

    // Should show diagnostic commands
    await expect(page.locator('.troubleshoot-step')).toContainText('sudo lsof -i :80');

    // Should show fix commands
    await expect(page.locator('.troubleshoot-step')).toContainText('sudo systemctl stop apache2');

    // Should show action buttons
    await expect(page.locator('.troubleshoot-buttons')).toBeVisible();
  });

  test('should execute troubleshooting workflow steps', async ({ page }) => {
    // Mock troubleshoot API
    await page.route('/troubleshoot', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analysis: 'Test error analysis',
          diagnostic_commands: ['echo diagnostic'],
          fix_commands: ['echo fix'],
          verification_commands: ['echo verify'],
          risk_level: 'low',
          requires_confirmation: true
        })
      });
    });

    // Mock execute API
    await page.route('/troubleshoot/execute', async route => {
      const request = route.request();
      const postData = request.postDataJSON();
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          step_type: postData.step_type,
          results: postData.commands.map(cmd => ({
            command: cmd,
            output: 'success',
            error: '',
            success: true
          })),
          all_success: true
        })
      });
    });

    await page.fill('#error-input', 'test error');
    await page.click('#troubleshoot-btn');
    await page.waitForSelector('.troubleshoot-buttons', { timeout: 5000 });

    // Click "Run Diagnostics"
    await page.click('button:has-text("Run Diagnostics")');

    // Should show diagnostic results
    await page.waitForSelector('.troubleshoot-result', { timeout: 5000 });
    await expect(page.locator('.troubleshoot-result')).toContainText('echo diagnostic');
  });

  test('should handle Ctrl+Enter to submit error', async ({ page }) => {
    await page.route('/troubleshoot', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analysis: 'Test',
          fix_commands: ['echo test'],
          verification_commands: ['echo verify'],
          risk_level: 'low'
        })
      });
    });

    await page.fill('#error-input', 'test error message');
    await page.press('#error-input', 'Control+Enter');

    // Should trigger troubleshoot request
    await page.waitForSelector('.troubleshoot-analysis', { timeout: 5000 });
  });

  test('should show different risk levels with correct styling', async ({ page }) => {
    const riskLevels = ['low', 'medium', 'high'];

    for (const risk of riskLevels) {
      await page.route('/troubleshoot', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            analysis: `Test ${risk} risk`,
            fix_commands: ['echo test'],
            verification_commands: ['echo verify'],
            risk_level: risk
          })
        });
      });

      await page.fill('#error-input', `test ${risk} risk error`);
      await page.click('#troubleshoot-btn');
      await page.waitForSelector(`.risk-${risk}`, { timeout: 5000 });

      // Verify risk level is displayed
      await expect(page.locator(`.risk-${risk}`)).toContainText(risk.toUpperCase());

      // Reload for next iteration
      await page.reload();
      await page.waitForSelector('#main-screen:not(.hidden)');
      await page.click('#mode-troubleshoot');
    }
  });
});
