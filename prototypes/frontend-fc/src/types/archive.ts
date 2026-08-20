/**
 * Archive Type Definitions
 * 
 * Type definitions for the Commish Tiers Archive feature components
 */

/**
 * Loading state for the embedded Google Drive viewer
 */
export type LoadingState = 'idle' | 'loading' | 'loaded' | 'error';

/**
 * Error types that can occur during embed loading
 */
export type EmbedErrorType = 'config' | 'network' | 'permissions' | 'unknown';

/**
 * Error information for embed failures
 */
export interface EmbedError {
  /** Type of error that occurred */
  type: EmbedErrorType;
  /** Human-readable error message */
  message: string;
  /** Optional fallback URL for direct access */
  fallbackUrl?: string;
}

/**
 * Props for the GoogleDriveEmbed component
 */
export interface GoogleDriveEmbedProps {
  /** Google Drive folder ID to embed */
  folderId: string;
  /** Callback when iframe successfully loads */
  onLoad: () => void;
  /** Callback when iframe fails to load */
  onError: () => void;
}

/**
 * Props for the ArchiveHeader component
 */
export interface ArchiveHeaderProps {
  /** Page title */
  title: string;
  /** Page description */
  description: string;
}

/**
 * Props for the ArchiveInstructions component
 */
export interface ArchiveInstructionsProps {
  /** Whether instructions should be visible */
  isVisible: boolean;
}
