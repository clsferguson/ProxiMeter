/**
 * 404 Not Found page
 */

import { Link } from 'react-router-dom'
import Layout from '@/components/Layout'

export default function NotFound() {
  return (
    <Layout>
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-4xl font-bold mb-4">404</h1>
        <p className="text-xl text-muted-foreground mb-6">Page not found</p>
        <Link 
          to="/" 
          className="text-primary hover:underline"
        >
          Return to Dashboard
        </Link>
      </div>
    </Layout>
  )
}
