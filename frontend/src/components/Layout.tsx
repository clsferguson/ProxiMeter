/**
 * Layout Component - Shared layout with navigation
 * 
 * Composes shadcn/ui primitives and Tailwind CSS utilities for responsive layout
 * Uses lucide-react icons for navigation
 * 
 * Provides consistent structure across all pages:
 * - Sticky header with ProxiMeter branding and navigation
 * - Responsive navigation (hidden on mobile, visible on md+ breakpoint)
 * - Mobile-optimized "Add Stream" button
 * - Main content area (flex-1 to fill available space)
 * - Footer with copyright/info
 * 
 * Features:
 * - Responsive design with Tailwind breakpoints (md: 768px+)
 * - Active link highlighting based on current route
 * - Backdrop blur effect on header (supports-[backdrop-filter])
 * - Touch-friendly navigation targets (44x44px minimum)
 * 
 * @component
 * @param {LayoutProps} props - Component props
 * @param {React.ReactNode} props.children - Page content to render in main area
 * @returns {JSX.Element} Rendered layout
 * 
 * @example
 * <Layout>
 *   <Dashboard />
 * </Layout>
 */

import { Link, useLocation } from 'react-router-dom'
import { Home, Plus, Video } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-backdrop-filter:bg-card/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center space-x-2">
              <Video className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">ProxiMeter</span>
            </Link>

            <nav className="hidden md:flex items-center gap-6">
              <Link
                to="/"
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary px-3 py-2 rounded-md min-h-10 min-w-10',
                  isActive('/') && !location.pathname.includes('/add')
                    ? 'text-foreground'
                    : 'text-muted-foreground'
                )}
              >
                <Home className="h-4 w-4" />
                Dashboard
              </Link>
              <Link
                to="/add"
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary px-3 py-2 rounded-md min-h-10 min-w-10',
                  isActive('/add') ? 'text-foreground' : 'text-muted-foreground'
                )}
              >
                <Plus className="h-4 w-4" />
                Add Stream
              </Link>
            </nav>
          </div>

          {/* Mobile Add Button - 44x44px minimum touch target */}
          <div className="md:hidden">
            <Link
              to="/add"
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-4 py-2 min-w-11"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Stream
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-sm text-muted-foreground">
            ProxiMeter - RTSP Stream Management
          </p>
        </div>
      </footer>
    </div>
  )
}
