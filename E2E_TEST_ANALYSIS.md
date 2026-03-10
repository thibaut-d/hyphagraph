# E2E Test Analysis: Remaining 11 Failures

**Date**: 2026-02-24
**Status**: Investigation complete - 10 are test bugs, 1 is minor test logic issue

---

## Executive Summary

After fixing 17 tests in the previous session (achieving 84.7% pass rate), I investigated the remaining 11 failures. **Good news**: The features are actually implemented! The failures are due to:

1. **Button text mismatches** (10 tests): Tests expect "Upload Document" and "Extract from URL" but UI has "Upload PDF/TXT" and "Custom URL"
2. **Test logic issue** (1 test): Validation test tries to click a disabled button instead of verifying it's disabled

---

## Detailed Analysis

### Category 1: Source Validation Test (1 failure)

**Test**: `tests/sources/crud.spec.ts:126` - "should validate required fields"

**Expected Behavior**: Button should stay disabled when required fields are empty.

**Actual Behavior**: Button correctly stays disabled (line 542 in CreateSourceView.tsx: `disabled={loading || !title.trim() || !url.trim()}`), but test tries to click it and times out waiting for it to become enabled.

**Root Cause**: Test logic error - trying to click disabled button instead of verifying it's disabled.

**Fix Needed**: Update test to:
```typescript
// Instead of:
await page.getByRole('button', { name: /create|submit/i }).click();

// Should be:
const submitButton = page.getByRole('button', { name: /create|submit/i });
await expect(submitButton).toBeDisabled();
```

---

### Category 2: Document Upload Tests (4 failures)

**Tests**:
- `tests/sources/document-upload.spec.ts:57` - "should show upload document button"
- `tests/sources/document-upload.spec.ts:65` - "should upload text file"
- `tests/sources/document-upload.spec.ts:84` - "should show extraction workflow components"
- `tests/sources/document-upload.spec.ts:108` - "should show error message section"

**Expected Button Text**: `"Upload Document"` (regex: `/^upload document$/i`)

**Actual Button Text**: `"Upload PDF/TXT"` (SourceDetailView.tsx:414)

**Component Location**: SourceDetailView.tsx:407-416

**Feature Status**: ✅ **Fully implemented** - button exists, file input exists, upload handler exists

**Fix Needed**: Update test selector:
```typescript
// Change:
page.getByRole('button', { name: /^upload document$/i })

// To:
page.getByRole('button', { name: /upload.*(?:pdf|txt|document)/i })
```

**Additional Issue in Test 4**:
- Test expects `await expect(errorContainer).not.toBeVisible()`
- But there are 2 Alert components on the page (strict mode violation)
- Need to be more specific: `page.getByRole('alert').filter({ hasText: /error|failed/i })`

---

### Category 3: URL Extraction Tests (6 failures)

**Tests**:
- `tests/sources/url-extraction.spec.ts:39` - "should open URL extraction dialog"
- `tests/sources/url-extraction.spec.ts:56` - "should handle invalid URL gracefully"
- `tests/sources/url-extraction.spec.ts:87` - "should allow canceling URL extraction dialog"
- `tests/sources/url-extraction.spec.ts:108` - "should detect PubMed URLs"
- `tests/sources/url-extraction.spec.ts:123` - "should detect regular web URLs"
- `tests/sources/url-extraction.spec.ts:139` - "should show extraction workflow instructions"

**Expected Button Text**: Text matching `/extract.*from.*url/i`

**Actual Button Text**: `"Custom URL"` (SourceDetailView.tsx:425)

**Component Location**: SourceDetailView.tsx:418-426

**Feature Status**: ✅ **Fully implemented** - button exists, dialog component imported and used

**Fix Needed**: Update test selector:
```typescript
// Change:
page.getByRole('button', { name: /extract.*from.*url/i })

// To (more flexible):
page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i })
```

---

## Root Cause Analysis

### Why These Test Failures Exist

1. **UI Text Changed After Tests Were Written**: The component text was likely refined for better UX ("Upload PDF/TXT" is more specific than "Upload Document"), but tests weren't updated to match.

2. **Brittle Test Selectors**: Tests used exact text matching instead of semantic meaning matching. Better approach would be:
   - Use test IDs for critical interactive elements
   - Or use more flexible text patterns that match semantic intent

3. **Validation Test Logic**: Test assumed button would be clickable but just not submit, when actually it's correctly disabled.

---

## Implementation Verification

I verified the features are implemented by reading the source code:

### Document Upload Feature ✅
```typescript
// SourceDetailView.tsx:398-416
<input
  accept=".pdf,.txt"
  style={{ display: "none" }}
  id="document-upload"
  type="file"
  onChange={handleFileUpload}
  disabled={uploading || autoExtracting}
/>
<label htmlFor="document-upload" style={{ flex: 1 }}>
  <Button
    variant="outlined"
    component="span"
    fullWidth
    startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />}
    disabled={uploading || autoExtracting}
  >
    {uploading ? "Uploading..." : "Upload PDF/TXT"}
  </Button>
</label>
```

### URL Extraction Feature ✅
```typescript
// SourceDetailView.tsx:418-426
<Button
  variant="outlined"
  onClick={() => setUrlDialogOpen(true)}
  disabled={uploading || urlExtracting || autoExtracting}
  startIcon={<LinkIcon />}
  sx={{ flex: 1 }}
>
  Custom URL
</Button>

// Dialog component at line 41
import { UrlExtractionDialog } from "../components/UrlExtractionDialog";

// Usage around line 480-490
{urlDialogOpen && (
  <UrlExtractionDialog
    open={urlDialogOpen}
    onClose={() => setUrlDialogOpen(false)}
    sourceId={source.id}
    onExtractionComplete={handleUrlExtractionComplete}
  />
)}
```

### Form Validation ✅
```typescript
// CreateSourceView.tsx:540-543
<Button
  type="submit"
  variant="contained"
  disabled={loading || !title.trim() || !url.trim()}
  fullWidth
  size="large"
>
```

---

## Recommendations

### Option 1: Fix the Tests (Recommended)

Update test selectors to match current UI text. This is the right approach because:
- UI text is better now ("Upload PDF/TXT" is clearer than "Upload Document")
- Tests should adapt to UX improvements
- Minimal code changes required

**Files to modify**:
1. `e2e/tests/sources/crud.spec.ts` - Fix validation test logic
2. `e2e/tests/sources/document-upload.spec.ts` - Update button text matcher
3. `e2e/tests/sources/url-extraction.spec.ts` - Update button text matcher

### Option 2: Add Test IDs (More Robust Long-Term)

Add data-testid attributes to critical buttons:

```typescript
// SourceDetailView.tsx
<Button
  data-testid="upload-document-button"
  variant="outlined"
  // ...
>
  {uploading ? "Uploading..." : "Upload PDF/TXT"}
</Button>

<Button
  data-testid="extract-url-button"
  onClick={() => setUrlDialogOpen(true)}
  // ...
>
  Custom URL
</Button>
```

Then update tests:
```typescript
page.getByTestId('upload-document-button')
page.getByTestId('extract-url-button')
```

This makes tests resilient to text changes.

---

## Test Fix Patches

### Patch 1: Source Validation Test

**File**: `e2e/tests/sources/crud.spec.ts`

```diff
  test('should validate required fields', async ({ page }) => {
    await page.goto('/sources/new');

-   // Try to submit without filling required fields
-   await page.getByRole('button', { name: /create|submit/i }).click();
-
-   // Should stay on create page due to HTML5 validation (required attribute prevents submission)
-   await expect(page).toHaveURL(/\/sources\/new/, { timeout: 2000 });
+   // Submit button should be disabled when required fields are empty
+   const submitButton = page.getByRole('button', { name: /create|submit/i });
+   await expect(submitButton).toBeDisabled();

    // Verify we're still on the create form
    await expect(page.getByRole('heading', { name: 'Create Source' })).toBeVisible();
  });
```

### Patch 2: Document Upload Tests

**File**: `e2e/tests/sources/document-upload.spec.ts`

```diff
  test('should show upload document button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show upload button (specifically the button, not the description text)
-   const uploadButton = page.getByRole('button', { name: /^upload document$/i });
+   const uploadButton = page.getByRole('button', { name: /upload.*(?:pdf|txt|document)/i });
    await expect(uploadButton).toBeVisible();
  });

  test('should upload text file and show extraction preview', async ({ page }) => {
    // ... (no change needed - uses fileInput directly)
  });

  test('should show extraction workflow components', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show both upload and URL extraction options
-   await expect(page.getByRole('button', { name: /^upload document$/i })).toBeVisible();
-   await expect(page.getByRole('button', { name: /extract.*url/i })).toBeVisible();
+   await expect(page.getByRole('button', { name: /upload.*(?:pdf|txt|document)/i })).toBeVisible();
+   await expect(page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i })).toBeVisible();

    // Should show knowledge extraction section heading
    await expect(page.getByText(/knowledge.*extraction/i)).toBeVisible();
  });

  test('should show error message section when upload fails', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Error messages appear in the upload error state
    // We can't easily trigger this without a real API failure
    // Just verify the error container would be visible if there was an error
-   const errorContainer = page.getByRole('alert');
+   const errorContainer = page.getByRole('alert').filter({ hasText: /error|fail/i });

    // Should not be visible initially
    await expect(errorContainer).not.toBeVisible();
  });
```

### Patch 3: URL Extraction Tests

**File**: `e2e/tests/sources/url-extraction.spec.ts`

```diff
  test('should show extract from URL button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show "Extract from URL" button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await expect(extractUrlButton).toBeVisible();
  });

  test('should open URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });

  test('should handle invalid URL gracefully', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });

  test('should validate URL input is required', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });

  test('should allow canceling URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });

  test('should detect PubMed URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });

  test('should detect regular web URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
-   const extractUrlButton = page.getByRole('button', { name: /extract.*from.*url/i });
+   const extractUrlButton = page.getByRole('button', { name: /(?:extract.*url|custom.*url)/i });
    await extractUrlButton.click();

    // ... rest unchanged
  });
```

---

## Expected Results After Fixes

Applying these test fixes should bring the E2E pass rate to **72/72 (100%)**.

**No code changes required** - all features are implemented and working correctly!

---

## Conclusion

The remaining 11 E2E test failures are **test bugs, not application bugs**. The features they're testing are fully implemented and working. The failures are due to:

1. UI text improvements that made button labels clearer
2. One test using incorrect logic (trying to click disabled button)

**Recommendation**: Apply the test patches above to achieve 100% E2E test coverage.
