import { useState, useEffect } from 'react';
import { AlertCircle, ExternalLink } from 'lucide-react';

interface GoogleDriveEmbedProps {
  folderId: string;
  onLoad?: () => void;
  onError?: () => void;
}

export function GoogleDriveEmbed({ folderId, onLoad, onError }: GoogleDriveEmbedProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const embedUrl = `https://drive.google.com/embeddedfolderview?id=${folderId}#list`;
  const fallbackUrl = `https://drive.google.com/drive/folders/${folderId}`;

  useEffect(() => {
    // Reset loading state when folder ID changes
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

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
    onError?.();
  };

  if (hasError) {
    return (
      <div className="card p-8 text-center">
        <AlertCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Unable to Load Archive
        </h3>
        <p className="text-gray-600 mb-4">
          The embedded viewer failed to load. This might be due to network issues or browser settings.
        </p>
        <a
          href={fallbackUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-primary-600 hover:text-primary-700 hover:underline"
        >
          Open in Google Drive
          <ExternalLink className="h-4 w-4 ml-1" />
        </a>
      </div>
    );
  }

  return (
    <div className="relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-10">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading archive...</p>
          </div>
        </div>
      )}
      <iframe
        src={embedUrl}
        onError={handleError}
        className="w-full h-[600px] md:h-[800px] border-0 rounded-lg shadow-sm"
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
        title="Commish Tiers Archive"
      />
    </div>
  );
}
