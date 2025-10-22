# Quick Start: Frontend React Migration

**Date**: 2025-10-19  
**Feature**: 003-frontend-react-migration  

## Prerequisites

- Node.js LTS (18.x or later)
- npm package manager
- Backend running on `http://localhost:8000` (for development)

## Development Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The development server will start on `http://localhost:5173` with automatic proxy to the backend API at `/api`.

### 3. Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory with tree-shaken shadcn/ui components.

### 4. Adding New UI Components

To add new shadcn/ui components:

```bash
npx shadcn@latest add <component-name>
```

For example:
```bash
npx shadcn@latest add tooltip
npx shadcn@latest add popover
```

This will:
- Download the component source from the shadcn/ui registry
- Add it to `src/components/ui/`
- Update your dependencies if needed
- Automatically tree-shake unused components during build

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

The frontend communicates with the backend REST API via relative paths:

- **Base URL**: `/api` (proxied to backend in development, served from same origin in production)
- **Streams**: `GET/POST /api/streams`, `PATCH/DELETE /api/streams/{id}`
- **Video Playback**: `GET /api/streams/play/{id}.mjpg`
- **Health Check**: `GET /api/health`

All API calls use the Fetch API with:
- 10-second default timeout
- Automatic error handling and type safety
- Request ID tracking for debugging

## Development Workflow

1. **Backend First**: Ensure backend is running and API endpoints are accessible
2. **Component Development**: Build components in isolation using Storybook (future)
3. **API Integration**: Use the services layer for all backend communication
4. **Testing**: Write unit tests for components and integration tests for API calls
5. **Build Verification**: Test production build before deployment

## Common Issues

### API Connection Failed
- Verify backend is running on port 8000
- Check that the proxy is working: `npm run dev` should show proxy configuration
- In production, ensure the frontend is served from the same origin as the backend

### TypeScript Errors
- Run `npm run lint` to check for issues
- Ensure all imports have proper type definitions
- Check that shadcn/ui components are properly imported from `@/components/ui/`

### Build Errors
- Clear `node_modules/` and reinstall: `rm -r node_modules && npm install`
- Clear Vite cache: `rm -r dist/` and rebuild
- Ensure TypeScript compilation passes: `npm run build` includes `tsc -b` check

### Component Not Found
- Verify the component is added via `npx shadcn@latest add <component-name>`
- Check that the import path is correct: `import { Button } from '@/components/ui/button'`
- Ensure the component is exported from `src/components/ui/index.ts` if using barrel exports

## Tailwind CSS & shadcn/ui Customization

### Design Tokens

The application uses Tailwind CSS with shadcn/ui components. Customize the design system in:

- **Colors**: `frontend/tailwind.config.ts` - Update the `colors` object
- **Spacing**: `frontend/tailwind.config.ts` - Modify `spacing` values
- **Typography**: `frontend/tailwind.config.ts` - Adjust `fontSize`, `fontFamily`
- **Component Variants**: `src/components/ui/*.tsx` - Use `class-variance-authority` for variants

### Component Development

When creating new components:

1. **Use shadcn/ui primitives**: Import from `@/components/ui/`
2. **Apply Tailwind classes**: Use utility classes for styling
3. **Define variants**: Use `cva()` from `class-variance-authority` for component variants
4. **Add TypeScript types**: Define prop interfaces for type safety
5. **Document with JSDoc**: Add comments explaining component purpose and props

Example:
```typescript
import { Button } from '@/components/ui/button'
import { cva, type VariantProps } from 'class-variance-authority'

const myComponentVariants = cva('base-classes', {
  variants: {
    variant: {
      default: 'default-classes',
      secondary: 'secondary-classes',
    },
  },
})

interface MyComponentProps extends VariantProps<typeof myComponentVariants> {
  children: React.ReactNode
}

export function MyComponent({ variant, children }: MyComponentProps) {
  return <div className={myComponentVariants({ variant })}>{children}</div>
}
```

## Next Steps

After setup, start with:
1. Dashboard page (`/`) - displays stream list
2. Add stream page (`/add`) - form for new streams
3. Edit stream page (`/edit/:id`) - form for editing streams
4. Play stream page (`/play/:id`) - video playback

See `research.md` for detailed migration strategy and component breakdown.