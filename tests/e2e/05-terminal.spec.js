// Test 5: Terminal Functionality
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - Terminal', () => {
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

    await page.fill('#host', '10.0.0.1');
    await page.fill('#user', 'ubuntu');
    await page.click('#connect-button');
    await page.waitForSelector('#main-screen:not(.hidden)', { timeout: 5000 });
  });

  test('should have terminal container visible', async ({ page }) => {
    await expect(page.locator('#terminal-container')).toBeVisible();
  });

  test('should have terminal control buttons', async ({ page }) => {
    await expect(page.locator('#clear-terminal')).toBeVisible();
    await expect(page.locator('#reconnect-terminal')).toBeVisible();
  });

  test('should show terminal header', async ({ page }) => {
    await expect(page.locator('.terminal-header')).toBeVisible();
    await expect(page.locator('.terminal-header')).toContainText('SSH Terminal');
  });

  test('clear button should be clickable', async ({ page }) => {
    const clearBtn = page.locator('#clear-terminal');
    await expect(clearBtn).toBeEnabled();
    await clearBtn.click();
    // Button should remain enabled after click
    await expect(clearBtn).toBeEnabled();
  });

  test('reconnect button should be clickable', async ({ page }) => {
    const reconnectBtn = page.locator('#reconnect-terminal');
    await expect(reconnectBtn).toBeEnabled();
    await reconnectBtn.click();
    // Button should remain enabled after click
    await expect(reconnectBtn).toBeEnabled();
  });
});
