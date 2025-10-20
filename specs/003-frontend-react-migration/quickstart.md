# Quick Start: Frontend React Migration

**Date**: 2025-10-19  
**Feature**: 003-frontend-react-migration  

## Prerequisites

- Node.js LTS (18.x or later)
- npm or yarn package manager
- Backend running on `http://localhost:8000`

## Development Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create `.env.local` in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ProxiMeter
```

### 3. Start Development Server

```bash
npm run dev
```

The development server will start on `http://localhost:5173` and proxy API requests to the backend.

### 4. Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/         # Page components (Dashboard, AddStream, etc.)
│   ├── hooks/         # Custom React hooks
│   ├── services/      # API service functions
│   ├── lib/           # Utilities and constants
│   ├── App.tsx        # Main app component with routing
│   └── main.tsx       # Application entry point
├── public/            # Static assets
├── package.json       # Dependencies and scripts
├── tsconfig.json      # TypeScript configuration
├── vite.config.ts     # Vite bundler configuration
└── index.html         # HTML template
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run test` - Run tests
- `npm run lint` - Run ESLint

## API Integration

The frontend communicates with the backend REST API:

- **Base URL**: `http://localhost:8000/api`
- **Streams**: `GET/POST /streams`, `PATCH/DELETE /streams/{id}`
- **Video Playback**: `GET /streams/play/{id}.mjpg`

## Development Workflow

1. **Backend First**: Ensure backend is running and API endpoints are accessible
2. **Component Development**: Build components in isolation using Storybook (future)
3. **API Integration**: Use the services layer for all backend communication
4. **Testing**: Write unit tests for components and integration tests for API calls
5. **Build Verification**: Test production build before deployment

## Common Issues

### CORS Errors
- Ensure backend allows requests from `http://localhost:5173`
- Check backend CORS configuration

### API Connection Failed
- Verify backend is running on port 8000
- Check `.env.local` has correct `VITE_API_BASE_URL`

### TypeScript Errors
- Run `npm run lint` to check for issues
- Ensure all imports have proper type definitions

## Next Steps

After setup, start with:
1. Dashboard page (`/`) - displays stream list
2. Add stream page (`/add`) - form for new streams
3. Edit stream page (`/edit/:id`) - form for editing streams
4. Play stream page (`/play/:id`) - video playback

See `research.md` for detailed migration strategy and component breakdown.