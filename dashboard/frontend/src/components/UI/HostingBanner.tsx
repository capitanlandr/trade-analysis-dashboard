import React, { useState } from 'react';
import { X, Info } from 'lucide-react';

const HostingBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState(false);
  
  // Don't show if dismissed
  if (dismissed) return null;
  
  return (
    <div className="bg-purple-50 border-l-4 border-purple-400 mt-2 mb-1">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5 text-purple-600">
            <Info className="h-5 w-5" />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="text-sm text-purple-900">
              <p className="font-semibold mb-2">
                <span className="mr-2">🔄</span>
                Dashboard Migration Notice
              </p>
              <p className="text-purple-800 mb-2">
                This dashboard is available on two URLs:
              </p>
              <div className="mt-2 space-y-1.5">
                <p className="text-purple-800">
                  • <strong>Vercel:</strong>{' '}
                  <a 
                    href="https://dynasuiiiianalytics.vercel.app" 
                    className="font-mono text-xs underline hover:text-purple-950"
                  >
                    dynasuiiiianalytics.vercel.app
                  </a>
                </p>
                <p className="text-purple-800">
                  • <strong>AWS:</strong>{' '}
                  <a 
                    href="https://d137gsvp1einvh.cloudfront.net" 
                    className="font-mono text-xs underline hover:text-purple-950"
                  >
                    d137gsvp1einvh.cloudfront.net
                  </a>
                </p>
              </div>
              <p className="text-purple-800 mt-2">
                If you see a random CloudFront URL, that's not a scam! It's our free AWS domain until we get a custom one. 
                Both URLs work and show the same data. 📊
              </p>
            </div>
          </div>
          
          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 text-purple-400 hover:text-purple-600 transition-colors"
            aria-label="Dismiss banner"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default HostingBanner;
