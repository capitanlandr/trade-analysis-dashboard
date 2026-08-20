import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { archiveConfig } from '../config/archive';
import { ArchiveHeader } from '../components/Archive/ArchiveHeader';
import { ArchiveInstructions } from '../components/Archive/ArchiveInstructions';
import { GoogleDriveEmbed } from '../components/Archive/GoogleDriveEmbed';

export default function CommishTiersArchive() {
  const [, setIsLoading] = useState(true);
  const [, setHasError] = useState(false);

  // Check if folder ID is configured
  const { driveFolderId } = archiveConfig;
  const hasValidConfig = driveFolderId && driveFolderId.trim().length > 0;

  const handleLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  // Show configuration error if folder ID is missing
  if (!hasValidConfig) {
    return (
      <div className="space-y-8">
        <ArchiveHeader
          title="Commish Tiers Archive"
          description="Access the complete collection of weekly Commish Tiers power rankings"
        />
        
        <div className="card p-8 text-center">
          <AlertCircle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Archive Not Configured
          </h3>
          <p className="text-gray-600 mb-4">
            The Google Drive folder ID has not been configured. Please set the 
            <code className="mx-1 px-2 py-1 bg-gray-100 rounded text-sm">VITE_DRIVE_FOLDER_ID</code> 
            environment variable.
          </p>
          <p className="text-sm text-gray-500">
            Contact your administrator to configure the archive.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <ArchiveHeader
        title="Commish Tiers Archive"
        description="Access the complete collection of weekly Commish Tiers power rankings"
      />

      <ArchiveInstructions isVisible={true} folderId={driveFolderId} />

      <GoogleDriveEmbed
        folderId={driveFolderId}
        onLoad={handleLoad}
        onError={handleError}
      />
    </div>
  );
}
