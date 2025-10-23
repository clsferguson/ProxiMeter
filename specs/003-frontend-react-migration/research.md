# Research Findings: Frontend React Migration

**Date**: 2025-10-19  
**Feature**: 003-frontend-react-migration  

## Decisions

### React 19.2 Adoption
**Decision**: Use React 19.2 as mandated by Constitution v2.3.0.  
**Rationale**: Constitution requires React 19.2 for the frontend SPA. React 19.2 is stable and provides improved performance, better TypeScript integration, and modern React features.  
**Alternatives Considered**: React 18.x - rejected due to constitution requirement.  
**Evidence**: React 19.2 release notes confirm stability for production use.

### TypeScript 5+ Configuration
**Decision**: Use TypeScript 5.6+ with strict mode enabled.  
**Rationale**: Constitution mandates TypeScript 5+ with strict mode. Provides better type safety and developer experience.  
**Alternatives Considered**: TypeScript 4.x - outdated and not compliant.  
**Evidence**: TypeScript 5.6 is the latest stable version with improved React support.

### Build Tool: Vite
**Decision**: Use Vite as the bundler.  
**Rationale**: Constitution specifies Vite for bundling. Offers fast development server, optimized production builds, and native TypeScript support.  
**Alternatives Considered**: Create React App, Webpack - Vite provides better performance and modern tooling.  
**Evidence**: Vite documentation recommends it for React projects.

### Routing Solution
**Decision**: Use React Router v6 for client-side routing.  
**Rationale**: Standard solution for React SPAs. Supports nested routes, code splitting, and history API.  
**Alternatives Considered**: No routing (single page) - rejected as spec requires multiple pages.  
**Evidence**: React Router is the most popular and well-maintained routing library for React.

### API Integration
**Decision**: Use native Fetch API for HTTP requests.  
**Rationale**: Modern browsers support Fetch natively, no additional dependencies needed. Provides Promise-based API that integrates well with async/await.  
**Alternatives Considered**: Axios - adds unnecessary bundle size for simple REST API calls.  
**Evidence**: Fetch API is standardized and sufficient for REST API integration.

### State Management
**Decision**: Use React's built-in useState and useContext hooks.  
**Rationale**: Application has simple state needs (stream CRUD, form state). No complex global state required.  
**Alternatives Considered**: Redux, Zustand - overkill for this scope.  
**Evidence**: React 19.2 improves hook performance, making built-in state management sufficient.

### Styling Approach
**Decision**: Use CSS modules with existing CSS as base.  
**Rationale**: Preserves existing UI/UX design while providing component-scoped styling. Allows gradual migration.  
**Alternatives Considered**: Styled-components, Tailwind CSS - would require complete redesign, violating spec requirement to preserve UI.  
**Evidence**: CSS modules provide scoping without framework overhead.

### Testing Framework
**Decision**: Use Vitest with React Testing Library.  
**Rationale**: Vite ecosystem integration, fast execution, and RTL provides component testing best practices.  
**Alternatives Considered**: Jest alone - Vitest provides better Vite integration.  
**Evidence**: Vitest is designed for modern bundlers and provides excellent developer experience.

### Animation Libraries (Optional)
**Decision**: Implement basic animations with CSS transitions, evaluate framer-motion if time permits.  
**Rationale**: Constitution allows optional animation libraries. Start with CSS for core functionality, add framer-motion for enhanced UX if scope allows.  
**Alternatives Considered**: react-bits, aceternity UI, motion-bits - framer-motion is most mature and widely adopted.  
**Evidence**: Framer Motion has excellent React integration and performance.

### Component Architecture
**Decision**: Use functional components with hooks, organize by feature.  
**Rationale**: Modern React patterns, better performance with React 19.2. Feature-based organization scales better than type-based.  
**Alternatives Considered**: Class components - outdated pattern.  
**Evidence**: React documentation recommends functional components with hooks.

### Form Handling
**Decision**: Use controlled components with React state.  
**Rationale**: Simple forms, no complex validation libraries needed initially.  
**Alternatives Considered**: React Hook Form - overkill for basic CRUD forms.  
**Evidence**: Controlled components provide full control and integrate well with TypeScript.

## Migration Strategy

### Page Conversion Order
1. Dashboard (index.html) - most complex, shows all streams
2. Add Stream (add_stream.html) - form-based
3. Edit Stream (edit_stream.html) - pre-populated form
4. Play Stream (play.html) - video display

### Common Components to Extract
- StreamListItem
- StreamForm
- VideoPlayer
- Navigation
- LoadingSpinner
- ErrorMessage

### API Integration Points
- GET /streams - fetch all streams
- POST /streams - create stream
- PUT /streams/{id} - update stream
- GET /streams/{id}/play - stream video
- SSE /events - real-time status updates

### Build Configuration
- Vite with TypeScript
- ESLint + Prettier
- Path aliases for clean imports
- Environment variables for API base URL

## Risks and Mitigations

### Risk: Bundle Size >500KB gzipped
**Mitigation**: Use tree shaking, lazy loading for routes, minimize dependencies.

### Risk: TypeScript Strict Mode Errors
**Mitigation**: Gradual adoption, use `any` temporarily if needed, fix during testing.

### Risk: Browser Compatibility
**Mitigation**: Target modern browsers as specified, use Vite's default targets.

### Risk: API Integration Issues
**Mitigation**: Test against existing backend endpoints, mock for development.