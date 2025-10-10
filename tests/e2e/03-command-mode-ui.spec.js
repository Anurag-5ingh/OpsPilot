// Test 3: Command Generation Mode UI
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - Command Generation Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/opspilot');
  });

  test('should have Command mode as default', async ({ page }) => {
    // Mock successful connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Fill credentials and connect
    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');

    // Wait for main screen
    await page.waitForSelector('#main-screen:not(.hidden)', { timeout: 5000 });

    // Command mode should be active by default
    await expect(page.locator('#mode-command')).toHaveClass(/active/);
    await expect(page.locator('#command-input-container')).toBeVisible();
    await expect(page.locator('#troubleshoot-input-container')).toBeHidden();
  });

  test('should generate command from natural language', async ({ page }) => {
    // Mock connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    // Mock AI command generation
    await page.route('/ask', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ai_command: 'ls -la',
          original_prompt: 'list all files'
        })
      });
    });

    // Connect
    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Type command request
    await page.fill('#user-input', 'list all files');
    await page.click('#ask');

    // Wait for AI response
    await page.waitForSelector('.message.ai', { timeout: 5000 });

    // Should show generated command
    const aiMessage = page.locator('.message.ai').last();
    await expect(aiMessage).toContainText('ls -la');

    // Should show confirmation buttons
    await expect(page.locator('.confirm-buttons')).toBeVisible();
  });

  test('should switch between Command and Troubleshoot modes', async ({ page }) => {
    // Mock connection
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Initially in Command mode
    await expect(page.locator('#mode-command')).toHaveClass(/active/);
    await expect(page.locator('#command-input-container')).toBeVisible();

    // Switch to Troubleshoot mode
    await page.click('#mode-troubleshoot');
    
    await expect(page.locator('#mode-troubleshoot')).toHaveClass(/active/);
    await expect(page.locator('#troubleshoot-input-container')).toBeVisible();
    await expect(page.locator('#command-input-container')).toBeHidden();

    // Switch back to Command mode
    await page.click('#mode-command');
    
    await expect(page.locator('#mode-command')).toHaveClass(/active/);
    await expect(page.locator('#command-input-container')).toBeVisible();
    await expect(page.locator('#troubleshoot-input-container')).toBeHidden();
  });

  test('should handle Enter key to submit command', async ({ page }) => {
    await page.route('/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ output: 'connected', error: '' })
      });
    });

    await page.route('/ask', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ai_command: 'pwd' })
      });
    });

    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)');

    // Type and press Enter
    await page.fill('#user-input', 'show current directory');
    await page.press('#user-input', 'Enter');

    // Should trigger AI request
    await page.waitForSelector('.message.ai', { timeout: 5000 });
  });
});
