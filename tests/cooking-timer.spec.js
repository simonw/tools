// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8765';

// Helper to load a recipe and transition to timer screen
async function loadRecipeAndGoToTimer(page, recipe) {
  await page.locator('#jsonInput').fill(JSON.stringify(recipe));
  await page.getByRole('button', { name: 'Load Recipe' }).click();
  // Wait for timer screen to become visible
  await expect(page.locator('#timerScreen')).toBeVisible({ timeout: 5000 });
}

test.describe('Cooking Timer Transfer Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Listen to console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser error:', msg.text());
      }
    });
  });

  test('page loads with no test failures', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);

    // Wait for initialization
    await page.waitForTimeout(1000);

    // Check that no test failures are displayed
    const testResults = page.locator('.test-results');
    await expect(testResults).not.toBeVisible();
  });

  test('Transfer button appears on timer screen', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);

    // Wait for page to load
    await page.waitForTimeout(500);

    // Load a recipe - this should navigate to timer screen
    await loadRecipeAndGoToTimer(page, {
      name: "Test Recipe",
      steps: [
        { time: 0, title: "Step 1", detail: "Do something" },
        { time: 60, title: "Step 2", detail: "Do something else" }
      ]
    });

    // Check transfer button is visible
    const transferBtn = page.getByRole('button', { name: 'Transfer to Phone' });
    await expect(transferBtn).toBeVisible();
  });

  test('QR modal opens when transfer button clicked', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe
    await loadRecipeAndGoToTimer(page, {
      name: "Test Recipe",
      steps: [{ time: 0, title: "Step 1" }]
    });

    // Click transfer button
    await page.getByRole('button', { name: 'Transfer to Phone' }).click();

    // Wait for QR code to generate
    await page.waitForTimeout(1000);

    // Modal should be visible
    const modal = page.locator('#qrModalOverlay');
    await expect(modal).toBeVisible();

    // Canvas should be visible
    const canvas = page.locator('#qrCanvas');
    await expect(canvas).toBeVisible();

    // Close button should work
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(modal).not.toBeVisible();
  });

  test('State serialization creates valid transfer URL', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe
    await loadRecipeAndGoToTimer(page, {
      name: "Test Recipe",
      steps: [{ time: 0, title: "Step 1" }]
    });

    // Start the timer
    await page.getByRole('button', { name: 'START COOKING' }).click();
    await page.waitForTimeout(500);

    // Generate URL via JavaScript evaluation (async)
    const transferUrl = await page.evaluate(async () => {
      return await window.generateTransferUrl();
    });

    // Should contain #transfer=
    expect(transferUrl).toContain('#transfer=');

    // Extract and decode the state (async)
    const fragment = transferUrl.split('#transfer=')[1];
    const state = await page.evaluate(async (frag) => {
      return await window.deserializeState(frag);
    }, fragment);

    // State should have expected structure
    expect(state).toHaveProperty('startTime');
    expect(state).toHaveProperty('recipeJsons');
    expect(state.recipeJsons.length).toBe(1);
    expect(state.recipeJsons[0].name).toBe('Test Recipe');
  });

  test('Transfer URL restores state on new page', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe
    const testRecipe = {
      name: "Transfer Test Recipe",
      steps: [
        { time: 0, title: "First Step", detail: "Details here" },
        { time: 60, title: "Second Step" }
      ]
    };

    await loadRecipeAndGoToTimer(page, testRecipe);

    // Start the timer
    await page.getByRole('button', { name: 'START COOKING' }).click();
    await page.waitForTimeout(500);

    // Get the transfer URL (async)
    const transferUrl = await page.evaluate(async () => {
      return await window.generateTransferUrl();
    });

    // Open a new page with the transfer URL
    const newPage = await context.newPage();
    await newPage.goto(transferUrl);

    // Wait for page to initialize
    await newPage.waitForTimeout(1000);

    // Timer screen should be showing
    const timerScreen = newPage.locator('#timerScreen');
    await expect(timerScreen).toBeVisible();

    // Recipe name should be displayed
    const recipeName = newPage.locator('#recipeName');
    await expect(recipeName).toContainText('Transfer Test Recipe');

    // Timer should be running (elapsed time visible)
    const elapsedTime = newPage.locator('#elapsedTime');
    await expect(elapsedTime).toBeVisible();

    // No test failures
    const testResults = newPage.locator('.test-results');
    await expect(testResults).not.toBeVisible();

    await newPage.close();
  });

  test('Recipe deduplication works on import', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe with JSON
    const testRecipe = {
      name: "Dedupe Test Recipe",
      steps: [{ time: 0, title: "Step 1" }]
    };

    await loadRecipeAndGoToTimer(page, testRecipe);

    // Start timer
    await page.getByRole('button', { name: 'START COOKING' }).click();
    await page.waitForTimeout(500);

    // Get transfer URL (async)
    const transferUrl = await page.evaluate(async () => await window.generateTransferUrl());

    // Open new page with transfer URL (first time)
    const newPage = await context.newPage();
    await newPage.goto(transferUrl);
    await newPage.waitForTimeout(1000);

    // Count saved recipes
    const countBefore = await newPage.evaluate(() => {
      return JSON.parse(localStorage.getItem('cookingTimerRecipes') || '[]').length;
    });

    // Navigate to the same transfer URL again (simulating second scan)
    await newPage.goto(transferUrl);
    await newPage.waitForTimeout(1000);

    // Count should be the same (no duplicate added)
    const countAfter = await newPage.evaluate(() => {
      return JSON.parse(localStorage.getItem('cookingTimerRecipes') || '[]').length;
    });

    expect(countAfter).toBe(countBefore);

    await newPage.close();
  });

  test('Timer sync maintains correct elapsed time', async ({ page, context }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe
    await loadRecipeAndGoToTimer(page, {
      name: "Sync Test",
      steps: [{ time: 0, title: "Step 1" }, { time: 300, title: "Step 2" }]
    });

    // Start the timer
    await page.getByRole('button', { name: 'START COOKING' }).click();

    // Wait 2 seconds
    await page.waitForTimeout(2000);

    // Get the transfer URL (async)
    const transferUrl = await page.evaluate(async () => await window.generateTransferUrl());

    // Record start time from original page
    const originalStartTime = await page.evaluate(() => window.startTime);

    // Open new page
    const newPage = await context.newPage();
    await newPage.goto(transferUrl);
    await newPage.waitForTimeout(1000);

    // Check that start time is preserved
    const newStartTime = await newPage.evaluate(() => window.startTime);
    expect(newStartTime).toBe(originalStartTime);

    // The displayed elapsed time should be similar (within a few seconds)
    const elapsed = await newPage.evaluate(() => {
      return Math.floor((Date.now() - window.startTime) / 1000);
    });

    // Should be at least 2 seconds (we waited 2 seconds)
    expect(elapsed).toBeGreaterThanOrEqual(2);

    await newPage.close();
  });

  test('Modal closes when clicking overlay', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);
    await page.waitForTimeout(500);

    // Load a recipe
    await loadRecipeAndGoToTimer(page, {
      name: "Test",
      steps: [{ time: 0, title: "Step" }]
    });

    // Open modal
    await page.getByRole('button', { name: 'Transfer to Phone' }).click();
    await page.waitForTimeout(1000);

    const modal = page.locator('#qrModalOverlay');
    await expect(modal).toBeVisible();

    // Click on overlay (outside the modal content)
    await page.locator('#qrModalOverlay').click({ position: { x: 10, y: 10 } });

    await expect(modal).not.toBeVisible();
  });

  test('Inline tests pass in browser', async ({ page }) => {
    await page.goto(`${BASE_URL}/cooking-timer.html`);

    // Wait for initialization and tests to run
    await page.waitForTimeout(1000);

    // Get test results from page
    const results = await page.evaluate(() => {
      return {
        passed: window.testResults.passed.length,
        failed: window.testResults.failed
      };
    });

    // Should have passed tests
    expect(results.passed).toBeGreaterThan(0);

    // Should have no failures
    expect(results.failed).toEqual([]);
  });
});
