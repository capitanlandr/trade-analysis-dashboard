# Commish Tiers Archive - Manual Testing Guide

This document provides a comprehensive testing checklist for the Commish Tiers Archive feature. Complete each test scenario and document the results.

## Prerequisites

1. **Start the development server:**
   ```bash
   cd trade-analysis-dashboard-clean
   npm run dev
   ```

2. **Access the dashboard:**
   - Open browser to `http://localhost:5173`
   - Ensure you have a valid Google Drive folder ID configured in `.env`

## Test Execution Checklist

### ✅ Task 7.1: Test with Valid Google Drive Folder

**Current Configuration:**
- Folder ID: `1lMGJrFE1lcMa6mRkoq6mpZ8twPa9kKMp`
- Folder URL: https://drive.google.com/drive/folders/1lMGJrFE1lcMa6mRkoq6mpZ8twPa9kKMp

#### Test Steps:

- [ ] **7.1.1** Navigate to the Commish Tiers tab
  - Click "Commish Tiers" in the navigation menu
  - **Expected:** Page loads and displays the archive header
  - **Result:** The tab is there.

- [ ] **7.1.2** Verify folder loads and displays documents
  - Wait for the iframe to load (should show loading indicator)
  - **Expected:** Google Drive folder interface appears within 3 seconds
  - **Expected:** Documents are visible in the folder list
  - **Result:** I get a loading archive... signal and a preview of the folder, but it just keeps reloading this "Load archive..." signal.

- [ ] **7.1.3** Test document preview functionality
  - Click on a PDF document in the folder
  - **Expected:** Google Drive's PDF viewer opens
  - Click on a DOCX document in the folder
  - **Expected:** Google Docs viewer opens
  - **Result:** _______________

- [ ] **7.1.4** Test document download functionality
  - Right-click on a document or use Google Drive's download button
  - **Expected:** Download option is available
  - **Expected:** Document downloads successfully
  - **Result:** _______________

- [ ] **7.1.5** Verify loading completes within expected time
  - Refresh the page and time the loading
  - **Expected:** Loading indicator disappears within 3 seconds
  - **Expected:** Folder content is visible within 5 seconds
  - **Result:** _______________

---

### ✅ Task 7.2: Test Responsive Behavior

#### Desktop Testing (>768px):

- [ ] **7.2.1** Test on desktop viewport
  - Resize browser to 1920x1080 or larger
  - **Expected:** Iframe displays at full width within container
  - **Expected:** Height is 800px (as per design)
  - **Expected:** All navigation elements are visible
  - **Result:** _______________

#### Mobile Testing (<768px):

- [ ] **7.2.2** Test on mobile viewport
  - Resize browser to 375x667 (iPhone SE size)
  - **Expected:** Iframe adjusts to mobile width
  - **Expected:** Height is 600px (as per design)
  - **Expected:** Navigation collapses appropriately
  - **Result:** _______________

- [ ] **7.2.3** Verify no horizontal scrolling on mobile
  - Scroll horizontally on mobile viewport
  - **Expected:** No horizontal scrollbar appears
  - **Expected:** Content fits within viewport width
  - **Result:** _______________

- [ ] **7.2.4** Test iframe interactions on touch devices
  - Use browser dev tools to simulate touch events
  - Try scrolling within the iframe
  - **Expected:** Touch scrolling works within iframe
  - **Expected:** No scroll conflicts with page scroll
  - **Result:** _______________

- [ ] **7.2.5** Verify Google Drive's mobile interface displays correctly
  - Check if Google Drive shows mobile-optimized view
  - **Expected:** Google Drive adapts to mobile viewport
  - **Expected:** Documents are readable and clickable
  - **Result:** _______________

---

### ✅ Task 7.3: Test Error Scenarios

#### Missing Folder ID:

- [ ] **7.3.1** Test with missing folder ID
  - Edit `.env` file: Set `VITE_DRIVE_FOLDER_ID=`
  - Restart dev server
  - Navigate to Commish Tiers tab
  - **Expected:** Error message displays: "Archive Not Configured"
  - **Expected:** No iframe is rendered
  - **Expected:** Message mentions `VITE_DRIVE_FOLDER_ID` environment variable
  - **Result:** _______________

#### Invalid Folder ID:

- [ ] **7.3.2** Test with invalid folder ID
  - Edit `.env` file: Set `VITE_DRIVE_FOLDER_ID=invalid_folder_id_12345`
  - Restart dev server
  - Navigate to Commish Tiers tab
  - **Expected:** Loading indicator appears initially
  - **Expected:** After timeout, error message displays: "Unable to Load Archive"
  - **Expected:** Fallback link to Google Drive is provided
  - **Result:** _______________

#### Private Folder:

- [ ] **7.3.3** Test with private folder
  - Use a private Google Drive folder ID (if available)
  - **Expected:** Google Drive shows permission prompt within iframe
  - **Expected:** User can sign in through Google's interface
  - **Result:** _______________

#### Network Timeout:

- [ ] **7.3.4** Test with network timeout
  - Use browser dev tools to throttle network to "Slow 3G"
  - Navigate to Commish Tiers tab
  - **Expected:** Loading indicator shows for up to 5 seconds
  - **Expected:** If loading exceeds 5 seconds, error fallback displays
  - **Expected:** Fallback link is provided
  - **Result:** _______________

#### User-Friendly Error Messages:

- [ ] **7.3.5** Verify error messages are user-friendly
  - Review all error messages encountered
  - **Expected:** Messages are clear and actionable
  - **Expected:** No technical jargon or stack traces
  - **Expected:** Fallback options are provided
  - **Result:** _______________

---

### ✅ Task 7.4: Test Permission Scenarios

#### Public/Link-Shared Folder:

- [ ] **7.4.1** Test with public/link-shared folder
  - Use current folder ID (should be link-shared)
  - Open in incognito/private browsing mode
  - Navigate to Commish Tiers tab
  - **Expected:** Folder loads without requiring sign-in
  - **Expected:** Documents are visible and accessible
  - **Result:** _______________

#### Private Folder:

- [ ] **7.4.2** Test with private folder
  - Change to a private folder ID (if available)
  - **Expected:** Google Drive prompts for sign-in within iframe
  - **Expected:** After sign-in, folder content is accessible
  - **Result:** _______________

#### Google Drive Authentication:

- [ ] **7.4.3** Verify Google Drive handles authentication in iframe
  - Test with a folder requiring authentication
  - **Expected:** Google's sign-in interface appears in iframe
  - **Expected:** Authentication flow completes within iframe
  - **Expected:** No redirect to external page
  - **Result:** _______________

#### Permission Changes:

- [ ] **7.4.4** Test changing folder permissions and reloading page
  - Change folder sharing settings in Google Drive
  - Reload the dashboard page
  - **Expected:** New permissions are reflected immediately
  - **Expected:** Access is granted/denied based on new settings
  - **Result:** _______________

---

### ✅ Task 7.5: Test Navigation and State Management

#### Navigation from Each Page:

- [ ] **7.5.1** Navigate to archive from Trade Analysis page
  - Start on Trade Analysis (/)
  - Click "Commish Tiers" nav item
  - **Expected:** Navigates to /commish-tiers
  - **Expected:** Archive page loads correctly
  - **Result:** _______________

- [ ] **7.5.2** Navigate to archive from Standings page
  - Start on Standings (/standings)
  - Click "Commish Tiers" nav item
  - **Expected:** Navigates to /commish-tiers
  - **Expected:** Archive page loads correctly
  - **Result:** _______________

- [ ] **7.5.3** Navigate to archive from Playoff Scenarios page
  - Start on Playoff Scenarios (/playoff-scenarios)
  - Click "Commish Tiers" nav item
  - **Expected:** Navigates to /commish-tiers
  - **Expected:** Archive page loads correctly
  - **Result:** _______________

#### Active State Highlighting:

- [ ] **7.5.4** Verify active state highlights correctly
  - Navigate to Commish Tiers tab
  - **Expected:** "Commish Tiers" nav item has blue underline
  - **Expected:** Text color is primary-600 (blue)
  - **Expected:** Other nav items are gray
  - **Result:** _______________

#### State Persistence:

- [ ] **7.5.5** Navigate away and return to archive
  - Navigate to Commish Tiers
  - Wait for folder to load
  - Navigate to another page
  - Return to Commish Tiers
  - **Expected:** Page loads fresh (iframe reloads)
  - **Expected:** No stale state from previous visit
  - **Result:** _______________

#### Browser Navigation:

- [ ] **7.5.6** Test browser back/forward buttons
  - Navigate: Trade Analysis → Commish Tiers → Standings
  - Click browser back button twice
  - **Expected:** Returns to Trade Analysis
  - Click browser forward button twice
  - **Expected:** Returns to Standings
  - **Expected:** Navigation state is correct at each step
  - **Result:** _______________

---

## Additional Testing Scenarios

### Cross-Browser Testing:

- [ ] **Chrome/Edge** (Chromium-based)
  - Test all scenarios above
  - **Result:** _______________

- [ ] **Firefox**
  - Test all scenarios above
  - **Result:** _______________

- [ ] **Safari** (macOS/iOS)
  - Test all scenarios above
  - **Result:** _______________

### Performance Testing:

- [ ] **Initial Load Time**
  - Measure time from navigation to full render
  - **Expected:** < 3 seconds on standard connection
  - **Result:** _______________

- [ ] **Iframe Load Time**
  - Measure time from iframe render to content visible
  - **Expected:** < 5 seconds on standard connection
  - **Result:** _______________

### Accessibility Testing:

- [ ] **Keyboard Navigation**
  - Tab through all interactive elements
  - **Expected:** Focus indicators are visible
  - **Expected:** Can navigate to and activate all controls
  - **Result:** _______________

- [ ] **Screen Reader**
  - Test with screen reader (VoiceOver, NVDA, etc.)
  - **Expected:** Page structure is announced correctly
  - **Expected:** Error messages are read aloud
  - **Result:** _______________

---

## Test Summary

**Date Tested:** _______________
**Tester:** _______________
**Browser/Version:** _______________
**OS/Version:** _______________

### Overall Results:

- **Total Tests:** 35
- **Passed:** _______________
- **Failed:** _______________
- **Blocked:** _______________

### Issues Found:

1. _______________
2. _______________
3. _______________

### Notes:

_______________
_______________
_______________

---

## Quick Test Commands

```bash
# Start development server
cd trade-analysis-dashboard-clean
npm run dev

# Test with different folder IDs
# Edit: trade-analysis-dashboard-clean/dashboard/frontend/.env
# Change: VITE_DRIVE_FOLDER_ID=<new_folder_id>
# Then restart server

# Test missing folder ID
# Set: VITE_DRIVE_FOLDER_ID=
# Restart server

# Test invalid folder ID
# Set: VITE_DRIVE_FOLDER_ID=invalid_id_12345
# Restart server
```

## Requirements Validation

This testing guide validates the following requirements:

- **Requirement 1.1, 1.2, 1.3, 1.5:** Embedded viewer loads and displays documents
- **Requirement 2.1, 2.2, 2.3, 2.4:** Document preview and download functionality
- **Requirement 3.2, 3.3, 3.4, 3.5:** Configuration and error handling
- **Requirement 4.1, 4.2, 4.3, 4.5:** Navigation integration
- **Requirement 5.1, 5.2, 5.3, 5.4, 5.5:** Responsive behavior
- **Requirement 6.1, 6.2, 6.3, 6.4, 6.5:** Permission handling
- **Requirement 7.1, 7.2, 7.3:** User guidance and error messages
