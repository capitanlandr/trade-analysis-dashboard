/**
 * Archive Configuration
 * 
 * Configuration for the Commish Tiers Archive feature that embeds
 * a Google Drive folder viewer in the dashboard.
 */

export interface ArchiveConfiguration {
  /** Google Drive folder ID from environment variables */
  driveFolderId: string;
  /** Base URL for Google Drive embed */
  embedBaseUrl: string;
  /** Fallback URL for direct folder access */
  fallbackUrl: string;
  /** Timeout for iframe loading in milliseconds */
  loadTimeout: number;
}

/**
 * Get the archive configuration from environment variables
 * 
 * @returns ArchiveConfiguration object with folder ID and settings
 */
export const getArchiveConfig = (): ArchiveConfiguration => {
  const driveFolderId = import.meta.env.VITE_DRIVE_FOLDER_ID || '';
  
  return {
    driveFolderId,
    embedBaseUrl: 'https://drive.google.com/embeddedfolderview',
    fallbackUrl: driveFolderId 
      ? `https://drive.google.com/drive/folders/${driveFolderId}`
      : '',
    loadTimeout: 5000
  };
};

/**
 * Construct the Google Drive embed URL from folder ID
 * 
 * @param folderId - Google Drive folder ID
 * @returns Complete embed URL with list view fragment
 */
export const constructEmbedUrl = (folderId: string): string => {
  if (!folderId) {
    return '';
  }
  return `https://drive.google.com/embeddedfolderview?id=${folderId}#list`;
};

// Export default configuration instance
export const archiveConfig = getArchiveConfig();
