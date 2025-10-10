// Test 2: API Endpoints
const { test, expect } = require('@playwright/test');

test.describe('OpsPilot - API Endpoints', () => {
  test('POST /ask should return AI command', async ({ request }) => {
    const response = await request.post('/ask', {
      data: {
        prompt: 'list all files'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should have ai_command field
    expect(data).toHaveProperty('ai_command');
    expect(typeof data.ai_command).toBe('string');
    expect(data.ai_command.length).toBeGreaterThan(0);
  });

  test('POST /troubleshoot should return troubleshooting plan', async ({ request }) => {
    const response = await request.post('/troubleshoot', {
      data: {
        error_text: 'nginx: [emerg] bind() to 0.0.0.0:80 failed',
        host: '10.0.0.1',
        username: 'ubuntu',
        port: 22,
        context: {}
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should have troubleshooting plan fields
    expect(data).toHaveProperty('analysis');
    expect(data).toHaveProperty('fix_commands');
    expect(data).toHaveProperty('verification_commands');
    expect(data).toHaveProperty('risk_level');
    
    // Verify data types
    expect(typeof data.analysis).toBe('string');
    expect(Array.isArray(data.fix_commands)).toBeTruthy();
    expect(Array.isArray(data.verification_commands)).toBeTruthy();
    expect(['low', 'medium', 'high']).toContain(data.risk_level);
  });

  test('GET /ssh/list should return empty array', async ({ request }) => {
    const response = await request.get('/ssh/list');
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should return array (empty since database is disabled)
    expect(Array.isArray(data)).toBeTruthy();
  });

  test('POST /ssh/save should accept connection info', async ({ request }) => {
    const response = await request.post('/ssh/save', {
      data: {
        host: '10.0.0.1',
        username: 'ubuntu',
        port: 22,
        description: 'Test server'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Should return success message
    expect(data).toHaveProperty('message');
  });

  test('GET / should redirect to /opspilot', async ({ request }) => {
    const response = await request.get('/', {
      maxRedirects: 0
    });
    
    // Should be a redirect
    expect([301, 302, 303, 307, 308]).toContain(response.status());
  });
});
