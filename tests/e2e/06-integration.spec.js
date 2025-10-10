// Test 6: Full Integration Tests
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - Full Integration', () => {
  test('complete workflow: login → command generation → execution', async ({ page }) => {
    await page.goto('/opspilot');

    // Mock connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Mock AI command
    await page.route('/ask', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ai_command: 'ls -la /home',
          original_prompt: 'list files in home directory'
        })
      });
    });

    // Step 1: Login
    await page.fill('#host', '192.168.1.100');
    await page.fill('#user', 'testuser');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Step 2: Generate command
    await page.fill('#user-input', 'list files in home directory');
    await page.click('#ask');
    await page.waitForSelector('.message.ai');

    // Step 3: Verify command shown
    await expect(page.locator('.message.ai').last()).toContainText('ls -la /home');

    // Step 4: Confirmation buttons appear
    await expect(page.locator('.confirm-buttons')).toBeVisible();
  });

  test('complete workflow: login → troubleshoot → execute fixes', async ({ page }) => {
    await page.goto('/opspilot');

    // Mock connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Mock troubleshoot
    await page.route('/troubleshoot', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analysis: 'Service is not running',
          diagnostic_commands: ['systemctl status nginx'],
          fix_commands: ['sudo systemctl start nginx'],
          verification_commands: ['systemctl status nginx'],
          risk_level: 'low',
          requires_confirmation: true
        })
      });
    });

    // Mock execute
    await page.route('/troubleshoot/execute', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          step_type: 'fix',
          results: [{
            command: 'sudo systemctl start nginx',
            output: 'Service started',
            error: '',
            success: true
          }],
          all_success: true
        })
      });
    });

    // Step 1: Login
    await page.fill('#host', '192.168.1.100');
    await page.fill('#user', 'testuser');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Step 2: Switch to troubleshoot mode
    await page.click('#mode-troubleshoot');

    // Step 3: Submit error
    await page.fill('#error-input', 'nginx service failed to start');
    await page.click('#troubleshoot-btn');
    await page.waitForSelector('.troubleshoot-analysis');

    // Step 4: Execute fixes
    await page.click('button:has-text("Run Fixes")');
    await page.waitForSelector('.troubleshoot-result');

    // Step 5: Verify results shown
    await expect(page.locator('.troubleshoot-result')).toContainText('sudo systemctl start nginx');
  });

  test('should handle mode switching during workflow', async ({ page }) => {
    await page.goto('/opspilot');

    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Login
    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Start in Command mode
    await expect(page.locator('#mode-command')).toHaveClass(/active/);
    await page.fill('#user-input', 'test command');

    // Switch to Troubleshoot mode
    await page.click('#mode-troubleshoot');
    await expect(page.locator('#mode-troubleshoot')).toHaveClass(/active/);
    await page.fill('#error-input', 'test error');

    // Switch back to Command mode
    await page.click('#mode-command');
    await expect(page.locator('#mode-command')).toHaveClass(/active/);

    // Both inputs should maintain their values
    await expect(page.locator('#user-input')).toHaveValue('test command');
    
    await page.click('#mode-troubleshoot');
    await expect(page.locator('#error-input')).toHaveValue('test error');
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.goto('/opspilot');

    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Mock failed AI request
    await page.route('/ask', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    await page.fill('#user-input', 'test command');
    await page.click('#ask');

    // Should show error message
    await page.waitForSelector('.message.system', { timeout: 5000 });
    await expect(page.locator('.message.system').last()).toContainText(/error|failed/i);
  });
});
