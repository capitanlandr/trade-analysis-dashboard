import { Info } from 'lucide-react';

interface ArchiveInstructionsProps {
  isVisible: boolean;
}

export function ArchiveInstructions({ isVisible }: ArchiveInstructionsProps) {
  if (!isVisible) {
    return null;
  }

  return (
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
          </ul>
        </div>
      </div>
    </div>
  );
}
