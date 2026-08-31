import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardLayout from './components/Layout/DashboardLayout'
import Overview from './pages/Overview'
import Standings from './pages/Standings'
import PlayoffScenarios from './pages/PlayoffScenarios'
import DraftOrderProjection from './pages/DraftOrderProjection'
import CommishTiersArchive from './pages/CommishTiersArchive'
import WaiverWireAnalysis from './pages/WaiverWireAnalysis'
import SurveyResults from './pages/SurveyResults'
import NflTop100 from './pages/NflTop100'
import DraftPickValue from './pages/DraftPickValue'
import { ErrorBoundary } from './components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors (client errors)
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <ErrorBoundary 
            fallback={
              <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Dashboard Temporarily Unavailable
                  </h1>
                  <p className="text-gray-600">
                    Please refresh the page or try again later.
                  </p>
                </div>
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<DashboardLayout />}>
                <Route index element={<Overview />} />
                <Route path="standings" element={<Standings />} />
                <Route path="playoff-scenarios" element={<PlayoffScenarios />} />
                <Route path="draft-order" element={<DraftOrderProjection />} />
                <Route path="commish-tiers" element={<CommishTiersArchive />} />
                <Route path="waiver-wire" element={<WaiverWireAnalysis />} />
                <Route path="survey-results" element={<SurveyResults />} />
                <Route path="nfl-top-100" element={<NflTop100 />} />
                <Route path="draft-value" element={<DraftPickValue />} />
              </Route>
            </Routes>
          </ErrorBoundary>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App