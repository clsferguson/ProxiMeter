/**
 * ProxiMeter React Application
 * Main app component with React Router v6 configuration
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './components/theme-provider'
import ErrorBoundary from './components/ErrorBoundary'

// Pages
import Dashboard from './pages/Dashboard'
import AddStream from './pages/AddStream'
import EditStream from './pages/EditStream'
import PlayStream from './pages/PlayStream'
import StreamDetection from './pages/StreamDetection'
import ModelManagement from './pages/ModelManagement'
import NotFound from './pages/NotFound'

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="proximeter-theme">
        <BrowserRouter>
          <div className="min-h-screen">
            <Routes>
              {/* Dashboard - Main page */}
              <Route path="/" element={<Dashboard />} />
              
              {/* Stream Management */}
              <Route path="/add" element={<AddStream />} />
              <Route path="/edit/:streamId" element={<EditStream />} />

              {/* Stream Playback */}
              <Route path="/play/:streamId" element={<PlayStream />} />

              {/* Detection Configuration */}
              <Route path="/streams/:streamId/detection" element={<StreamDetection />} />

              {/* Model Management */}
              <Route path="/models" element={<ModelManagement />} />

              {/* 404 Not Found */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
