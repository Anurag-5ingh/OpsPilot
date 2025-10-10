// Test 1: Basic application loading
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - Application Loading', () => {
  test('should load the login page', async ({ page }) => {
    await page.goto('/opspilot');
    
    // Check page title
    await expect(page).toHaveTitle(/AI Shell Assistant/);
    
    // Check login screen is visible
    await expect(page.locator('#login-screen')).toBeVisible();
    
    // Check logo and branding
    await expect(page.locator('.logo-text')).toContainText('opsPilot');
    
    // Check input fields exist
    await expect(page.locator('#host')).toBeVisible();
    await expect(page.locator('#user')).toBeVisible();
    
    // Check connect button exists
    await expect(page.locator('#connect-button')).toBeVisible();
  });

  test('should show validation error for empty credentials', async ({ page }) => {
    await page.goto('/opspilot');
    
    // Click connect without entering credentials
    await page.click('#connect-button');
    
    // Should show error message
    await expect(page.locator('#login-error')).toContainText('Both fields are required');
  });

  test('should have all required assets loaded', async ({ page }) => {
    await page.goto('/opspilot');
    
    // Check CSS is loaded
    const stylesheets = await page.$$('link[rel="stylesheet"]');
    expect(stylesheets.length).toBeGreaterThan(0);
    
    // Check JavaScript files are loaded
    const scripts = await page.$$('script[src]');
    expect(scripts.length).toBeGreaterThan(0);
    
    // Check logo image exists
    const logo = page.locator('img[alt="Brain Logo"]');
    await expect(logo).toBeVisible();
  });
});
