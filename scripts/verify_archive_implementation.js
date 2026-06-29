#!/usr/bin/env node

/**
 * Automated verification script for Commish Tiers Archive implementation
 * This script checks that all required files exist and have correct structure
 */

const fs = require('fs');
const path = require('path');

const DASHBOARD_ROOT = path.join(__dirname, 'dashboard', 'frontend');

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkFileExists(filePath, description) {
  const fullPath = path.join(DASHBOARD_ROOT, filePath);
  const exists = fs.existsSync(fullPath);
  
  if (exists) {
    log(`✓ ${description}`, 'green');
    return true;
  } else {
    log(`✗ ${description} - File not found: ${filePath}`, 'red');
    return false;
  }
}

function checkFileContent(filePath, searchStrings, description) {
  const fullPath = path.join(DASHBOARD_ROOT, filePath);
  
  if (!fs.existsSync(fullPath)) {
    log(`✗ ${description} - File not found: ${filePath}`, 'red');
    return false;
  }
  
  const content = fs.readFileSync(fullPath, 'utf8');
  const missingStrings = searchStrings.filter(str => !content.includes(str));
  
  if (missingStrings.length === 0) {
    log(`✓ ${description}`, 'green');
    return true;
  } else {
    log(`✗ ${description} - Missing: ${missingStrings.join(', ')}`, 'red');
    return false;
  }
}

function checkEnvVariable() {
  const envPath = path.join(DASHBOARD_ROOT, '.env');
  
  if (!fs.existsSync(envPath)) {
    log('✗ .env file not found', 'red');
    return false;
  }
  
  const content = fs.readFileSync(envPath, 'utf8');
  const hasVariable = content.includes('VITE_DRIVE_FOLDER_ID');
  const hasValue = /VITE_DRIVE_FOLDER_ID=.+/.test(content);
  
  if (hasVariable && hasValue) {
    log('✓ VITE_DRIVE_FOLDER_ID is configured in .env', 'green');
    return true;
  } else if (hasVariable) {
    log('⚠ VITE_DRIVE_FOLDER_ID exists but has no value', 'yellow');
    return false;
  } else {
    log('✗ VITE_DRIVE_FOLDER_ID not found in .env', 'red');
    return false;
  }
}

function main() {
  log('\n=== Commish Tiers Archive Implementation Verification ===\n', 'blue');
  
  let passed = 0;
  let failed = 0;
  
  // Check component files
  log('Checking Component Files:', 'blue');
  if (checkFileExists('src/pages/CommishTiersArchive.tsx', 'Main page component')) passed++; else failed++;
  if (checkFileExists('src/components/Archive/GoogleDriveEmbed.tsx', 'GoogleDriveEmbed component')) passed++; else failed++;
  if (checkFileExists('src/components/Archive/ArchiveHeader.tsx', 'ArchiveHeader component')) passed++; else failed++;
  if (checkFileExists('src/components/Archive/ArchiveInstructions.tsx', 'ArchiveInstructions component')) passed++; else failed++;
  
  // Check configuration files
  log('\nChecking Configuration Files:', 'blue');
  if (checkFileExists('src/config/archive.ts', 'Archive configuration')) passed++; else failed++;
  if (checkFileExists('src/types/archive.ts', 'Archive type definitions')) passed++; else failed++;
  
  // Check environment configuration
  log('\nChecking Environment Configuration:', 'blue');
  if (checkEnvVariable()) passed++; else failed++;
  
  // Check routing integration
  log('\nChecking Routing Integration:', 'blue');
  if (checkFileContent(
    'src/App.tsx',
    ['CommishTiersArchive', 'commish-tiers'],
    'Route added to App.tsx'
  )) passed++; else failed++;
  
  // Check navigation integration
  log('\nChecking Navigation Integration:', 'blue');
  if (checkFileContent(
    'src/components/Layout/DashboardLayout.tsx',
    ['FileText', 'Commish Tiers', '/commish-tiers'],
    'Navigation item added to DashboardLayout'
  )) passed++; else failed++;
  
  // Check key implementation details
  log('\nChecking Implementation Details:', 'blue');
  if (checkFileContent(
    'src/pages/CommishTiersArchive.tsx',
    ['archiveConfig', 'GoogleDriveEmbed', 'ArchiveHeader', 'ArchiveInstructions'],
    'Page uses all required components'
  )) passed++; else failed++;
  
  if (checkFileContent(
    'src/components/Archive/GoogleDriveEmbed.tsx',
    ['embeddedfolderview', 'sandbox', 'onLoad', 'onError'],
    'GoogleDriveEmbed has required functionality'
  )) passed++; else failed++;
  
  // Summary
  log('\n=== Verification Summary ===', 'blue');
  log(`Passed: ${passed}`, 'green');
  log(`Failed: ${failed}`, failed > 0 ? 'red' : 'green');
  
  if (failed === 0) {
    log('\n✓ All checks passed! Implementation is complete.', 'green');
    log('\nNext steps:', 'blue');
    log('1. Start the development server: npm run dev');
    log('2. Follow the manual testing guide: COMMISH_TIERS_ARCHIVE_TESTING_GUIDE.md');
    log('3. Test all scenarios in the guide');
    return 0;
  } else {
    log('\n✗ Some checks failed. Please review the errors above.', 'red');
    return 1;
  }
}

process.exit(main());
