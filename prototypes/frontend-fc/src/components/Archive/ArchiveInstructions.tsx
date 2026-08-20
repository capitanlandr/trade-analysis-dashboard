import { Info, ExternalLink } from 'lucide-react';

interface ArchiveInstructionsProps {
  isVisible: boolean;
  folderId?: string;
}

export function ArchiveInstructions({ isVisible, folderId }: ArchiveInstructionsProps) {
  if (!isVisible) {
    return null;
  }

  const fallbackUrl = folderId ? `https://drive.google.com/drive/folders/${folderId}` : null;

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <Info className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900 mb-1">
              How to Use the Archive
            </h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Click on any document to preview it in Google Drive's viewer</li>
              <li>• Use the download button in the preview to save documents locally</li>
              <li>• Documents are organized chronologically with the most recent first</li>
              <li>• If you see a cookie message, allow cookies to view files directly in the page</li>
            </ul>
          </div>
        </div>
      </div>

      {fallbackUrl && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-yellow-900 mb-1">
                Having trouble with the embedded viewer?
              </h4>
              <p className="text-sm text-yellow-800">
                Open the archive directly in Google Drive for the best experience
              </p>
            </div>
            <a
              href={fallbackUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Open in Google Drive
              <ExternalLink className="h-4 w-4 ml-2" />
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
