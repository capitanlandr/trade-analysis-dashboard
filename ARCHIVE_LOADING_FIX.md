# Commish Tiers Archive - Loading Issues Fixed

## Issue 1: Infinite Loading Loop (RESOLVED)

### Problem
The iframe was stuck in an infinite loading loop, continuously showing "Loading archive..." without ever completing.

### Root Cause
The `useEffect` hook had `isLoading` in its dependency array, causing infinite re-renders.

### Solution
Removed `isLoading` from dependencies and used a local `hasLoaded` flag.

---

## Issue 2: Timeout Error After 5 Seconds (RESOLVED)

### Problem
After fixing the infinite loop, the component would show files for 5 seconds, then display "Unable to Load Archive" error message.

### Root Cause
Google Drive's embedded folder view doesn't reliably fire the iframe `onLoad` event because it loads content dynamically via JavaScript. The component was waiting for an event that never fired, causing the 5-second timeout to trigger.

### Solution
Replaced event-based loading detection with time-based approach:
- Removed dependency on iframe's `onLoad` event
- Show loading indicator for 1.5 seconds (enough time for iframe to start rendering)
- Automatically hide loading indicator after delay
- Only show error if iframe's `onError` event fires (actual failure)

---

## Final Implementation

**File:** `trade-analysis-dashboard-clean/dashboard/frontend/src/components/Archive/GoogleDriveEmbed.tsx`

**Key Changes:**
1. Removed `isLoading` from useEffect dependencies
2. Removed `onLoad` handler from iframe element
3. Changed from event-based to time-based loading (1.5s delay)
4. Kept `onError` handler for actual iframe failures

**Code:**
```typescript
useEffect(() => {
  setIsLoading(true);
  setHasError(false);

  // Google Drive's embedded folder view doesn't reliably fire onLoad events
  // because it loads content dynamically. Instead, we'll hide the loading
  // indicator after a brief delay to let the iframe start rendering.
  const loadingTimeout = setTimeout(() => {
    setIsLoading(false);
    onLoad?.();
  }, 1500);

  return () => {
    clearTimeout(loadingTimeout);
  };
}, [folderId, onLoad]);
```

---

## Testing Results

✅ **Task 7.1 Completed - Valid Google Drive Folder:**
- Loading indicator shows for 1.5 seconds
- Google Drive folder view appears and stays visible
- Files are clickable and open in new tabs
- No error message after timeout
- Works with both "Anyone with link" and "Restricted" folder permissions

---

## Next Steps

Continue with remaining manual testing tasks:
- [ ] Task 7.2: Test responsive behavior (desktop/mobile)
- [ ] Task 7.3: Test error scenarios (missing/invalid folder ID)
- [ ] Task 7.4: Test permission scenarios
- [ ] Task 7.5: Test navigation and state management

See: `COMMISH_TIERS_ARCHIVE_TESTING_GUIDE.md`
