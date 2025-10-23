# ProxiMeter Frontend

React 19.2 + TypeScript SPA powered by Vite, Tailwind CSS 4.1, and shadcn/ui.

## Tech Stack

- React 19.2
- TypeScript 5.9 (strict mode)
- Vite 7.1
- Tailwind CSS 4.1 + `@tailwindcss/vite`
- shadcn/ui component registry
- Vitest + Testing Library
- ESLint (type-aware) + Prettier + Tailwind lint rules

## Getting Started

### Prerequisites

The frontend requires a running backend API. See the main ProxiMeter README for backend setup instructions.

### Development

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on <http://localhost:5173> by default.

**Important**: Make sure the backend is running on `http://localhost:8000` before starting the frontend dev server, or set `VITE_API_URL` to the correct backend URL in `.env.development`.

### Environment Configuration

Create a `.env.development` file for local development (already included with default values):

```bash
VITE_API_URL=http://localhost:8000
VITE_DEV_SERVER_HOST=127.0.0.1
VITE_DEV_SERVER_PORT=5173
```

The Vite dev server automatically proxies `/api/*` requests to the backend API URL.

### Available Scripts

- `npm run dev` – start Vite dev server
- `npm run build` – type-check and produce production build
- `npm run preview` – preview production build
- `npm run lint` – run ESLint with React/Tailwind rules
- `npm run test` – run unit tests with Vitest

## Tailwind & shadcn Setup

- Tailwind CSS is configured via `@tailwindcss/postcss` and `@tailwindcss/vite`.
- Global styles live in `src/styles/tailwind.css` (includes `@tailwind` layers and design tokens).
- shadcn/ui is initialized via `npx shadcn@latest init`; component aliases are defined in `components.json`.
- Use `npx shadcn@latest add <component>` to scaffold new UI primitives (`button`, `card`, etc.).

### Adding Components

```bash
npx shadcn@latest add button
```

Components are output under `src/components/ui/` and rely on Tailwind tokens defined in `src/styles/tailwind.css`.

## Project Structure

```
frontend/
├── components.json         # shadcn/ui configuration
├── src/
│   ├── components/         # shared & shadcn UI components
│   ├── pages/              # route-level views
│   ├── hooks/              # custom React hooks
│   ├── services/           # API clients
│   ├── lib/                # utilities and helpers
│   ├── styles/tailwind.css # Tailwind base + design tokens
│   ├── App.tsx             # root component
│   └── main.tsx            # Vite entrypoint
├── tailwind.config.ts      # Tailwind theme extensions
├── vite.config.ts          # Vite + Tailwind plugin setup
└── tsconfig.*.json         # Strict TypeScript configs
```

## Coding Guidelines

- Compose UI exclusively from shadcn/ui primitives and Tailwind utility classes.
- Keep TypeScript strict (no `any`; prefer typed hooks and services).
- Place reusable utilities in `src/lib/`; API contracts in `src/lib/types.ts` (when implemented).
- Follow shadcn/ui patterns for component variants and class merging (`cn` helper).

## Tailwind Theme Tokens

Design tokens and color palettes live in `src/styles/tailwind.css`. Update `@theme` values to tweak global colors, spacing, and typography.

## Linting & Formatting

- ESLint rules include React, Hooks, Tailwind, and shadcn recommendations.
- Prettier handles formatting (`.prettierrc`).
- Tailwind class ordering enforced via `eslint-plugin-tailwindcss` (v4 alpha).

## Testing

- Vitest configured with JSDOM environment (`vitest.setup.ts`).
- Use Testing Library (`@testing-library/react`) for component tests.

## Deployment Notes

- Production build emits static assets to `frontend/dist/` via `npm run build`.
- Backend Dockerfile will copy these assets into the Python image (see Phase 1 tasks T008/T009).

## Useful Commands

```bash
# generate shadcn/ui component
npx shadcn@latest add card

# run lint checks
npm run lint

# execute tests with coverage
npm run test:coverage
```

Refer to `specs/003-frontend-react-migration/` for full requirements, tasks, and architecture decisions.
