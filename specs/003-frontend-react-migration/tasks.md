# Tasks: Frontend React Migration

**Input**: Design documents from `/specs/003-frontend-react-migration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create frontend/ directory structure per plan.md (frontend/src/components/, pages/, hooks/, services/, lib/)
- [x] T002 Initialize Vite + React 19.2 + TypeScript 5+ project in frontend/ with package.json, tsconfig.json, vite.config.ts, tailwind.config.ts, postcss.config.cjs
- [x] T003 [P] Install core dependencies: react, react-dom, react-router-dom, fetch (native), vitest, @testing-library/react, tailwindcss, postcss, autoprefixer, class-variance-authority, tailwind-merge, lucide-react, and set up the shadcn/ui CLI
- [x] T004 [P] Run `npx shadcn@latest init` with Tailwind CSS, configure base styles, and commit generated shadcn/ui config
- [x] T005 [P] Configure TypeScript strict mode in tsconfig.json per research.md decisions
- [x] T006 [P] Configure Vite for production builds with Tailwind CSS integration, environment variables, and shadcn/ui tree-shaking
- [x] T007 [P] Set up ESLint and Prettier configuration for code quality (include tailwindcss and shadcn/ui linting rules)
- [X] T008 Create basic HTML template (index.html) and main.tsx entry point wiring Tailwind base styles and shadcn/ui `ThemeProvider`
- [X] T009 Update Dockerfile for multi-stage build: Node.js frontend build → serve static files from backend (ensure Tailwind + shadcn/ui build steps included)
- [X] T010 Update docker-compose.yml to expose frontend port and mount static files
- [X] T011 Create constants.ts with hardcoded API_BASE_URL='/api' (frontend served from backend, no env var needed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T012 [P] Create TypeScript interfaces for API contracts in frontend/src/lib/types.ts (Stream, StreamResponse, NewStreamRequest, EditStreamRequest, ErrorResponse)
- [X] T013 [P] Implement API service layer in frontend/src/services/api.ts using native Fetch with error handling, timeouts, and type safety
- [X] T014 [P] Create utility functions in frontend/src/lib/utils.ts for URL masking, validation helpers, and common operations
- [X] T015 [P] Set up React Router v6 configuration in App.tsx with routes for dashboard, add, edit, play pages and wrap routes with shadcn/ui layout primitives
- [X] T016 [P] Create shared layout component in frontend/src/components/Layout.tsx using shadcn/ui `NavigationMenu`, `Sidebar`, and `Button` components for consistent styling
- [X] T017 [P] Migrate legacy CSS rules into Tailwind design tokens, extend tailwind.config with color/spacing theme, and remove direct usage of src/templates/*.html styles
- [X] T018 [P] Create reusable UI components by running `npx shadcn add` (Button, Input, Select, Dialog, Alert, Card, Badge, Skeleton, Toast) in frontend/src/components/ui/
- [X] T019 [P] Implement custom hooks: useStreams for stream management, useApi for API state in frontend/src/hooks/

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Stream Dashboard (Priority: P1) 🎯 MVP

**Goal**: Display main dashboard showing all configured RTSP streams with real-time status

**Independent Test**: Load dashboard URL and verify stream list displays with status indicators updating every 2 seconds

### Implementation for User Story 1

- [ ] T020 [US1] Create Dashboard page component in frontend/src/pages/Dashboard.tsx using shadcn/ui `PageHeader`, `Breadcrumb`, and responsive grid layout
- [ ] T021 [P] [US1] Create StreamCard component in frontend/src/components/StreamCard.tsx composing shadcn/ui `Card`, `Badge`, `Button`, and iconography from lucide-react
- [ ] T022 [P] [US1] Create EmptyState component in frontend/src/components/EmptyState.tsx using shadcn/ui `Alert` and `Button` for CTA when no streams exist
- [ ] T023 [US1] Implement real-time status polling in Dashboard using useStreams hook (every 2 seconds)
- [ ] T024 [US1] Add navigation header with "ProxiMeter" title and "Add Stream" button using shadcn/ui `NavigationMenu` + `Button`
- [ ] T025 [US1] Implement stream list rendering with responsive card layout (768px+ breakpoint) using Tailwind grid utilities

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Add New Stream (Priority: P1)

**Goal**: Provide form interface for adding new RTSP streams with validation

**Independent Test**: Navigate to add stream form, submit valid data, verify stream appears in dashboard

### Implementation for User Story 2

- [ ] T026 [US2] Create AddStream page component in frontend/src/pages/AddStream.tsx with shadcn/ui `Form` layout and descriptive copy
- [ ] T027 [P] [US2] Create StreamForm component in frontend/src/components/StreamForm.tsx (reusable for add/edit) using shadcn/ui `Form`, `Input`, `Select`, `Switch`, `Textarea`
- [ ] T028 [US2] Implement form validation: name required, RTSP URL format, threshold 0-1 range with react-hook-form + zod integration used by shadcn/ui forms
- [ ] T029 [US2] Add form submission handling with shadcn/ui `Button` loading states and `useToast` for success/error feedback
- [ ] T030 [US2] Implement success navigation back to dashboard after stream creation
- [ ] T031 [US2] Add cancel button returning to dashboard without saving using shadcn/ui `Button` variants

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Edit Existing Stream (Priority: P2)

**Goal**: Allow modification of existing stream configuration

**Independent Test**: Edit a stream via dashboard action, verify changes persist and display correctly

### Implementation for User Story 3

- [ ] T032 [US3] Create EditStream page component in frontend/src/pages/EditStream.tsx with pre-populated form that reuses shadcn/ui `Form`
- [ ] T033 [US3] Reuse StreamForm component for edit functionality with initial values and variant styling
- [ ] T034 [US3] Implement route parameter handling for stream ID in edit page
- [ ] T035 [US3] Add delete stream functionality with shadcn/ui `AlertDialog` confirmation
- [ ] T036 [US3] Handle stream not found errors with redirect to dashboard using shadcn/ui `Alert`
- [ ] T037 [US3] Implement form pre-population from API data on page load

**Checkpoint**: User Stories 1, 2, AND 3 should now be independently functional

---

## Phase 6: User Story 4 - Play Live Stream (Priority: P2)

**Goal**: Display live RTSP stream video in browser with controls

**Independent Test**: Select play action from dashboard, verify video playback starts within 3 seconds

### Implementation for User Story 4

- [ ] T038 [US4] Create PlayStream page component in frontend/src/pages/PlayStream.tsx with shadcn/ui `PageHeader` and layout shell
- [ ] T039 [P] [US4] Create VideoPlayer component in frontend/src/components/VideoPlayer.tsx with HTML5 video element wrapped in shadcn/ui `AspectRatio`
- [ ] T040 [US4] Implement MJPEG stream URL construction and video source setup
- [ ] T041 [US4] Add video player controls: play/pause, volume, fullscreen using shadcn/ui `Button`, `DropdownMenu`
- [ ] T042 [US4] Implement error states: stream unavailable, unsupported codec, network error surfaced via shadcn/ui `Alert`
- [ ] T043 [US4] Add loading state with spinner during video initialization using shadcn/ui `Skeleton`
- [ ] T044 [US4] Implement back navigation to dashboard from play page with shadcn/ui `Button`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T045 [P] Update README.md with frontend development setup, Tailwind guidelines, shadcn/ui component usage, and build instructions
- [ ] T046 [P] Add component documentation and prop types in code comments referencing the shadcn/ui primitives used
- [ ] T047 [P] Optimize bundle size and verify <500KB gzipped production build (tree-shake unused shadcn/ui components)
- [ ] T048 [P] Implement responsive design touch targets (minimum 44x44px) using Tailwind spacing tokens and shadcn/ui variants
- [ ] T049 [P] Add error boundaries for graceful error handling across components leveraging shadcn/ui `Alert` and `Toast`
- [ ] T050 [P] Update artifacts/versions.md with React 19.2, TypeScript, Node.js, shadcn/ui, Tailwind versions
- [ ] T051 [P] Test production build in Docker environment
- [ ] T052 [P] Validate quickstart.md instructions work correctly (include shadcn/ui setup steps)
- [ ] T053 [P] Document Tailwind design tokens and component mapping in artifacts/decisions.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Models before services (but in this case, API types are foundational)
- Services before endpoints (API service is foundational)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all components for User Story 1 together:
Task: "Create StreamCard component in frontend/src/components/StreamCard.tsx"
Task: "Create EmptyState component in frontend/src/components/EmptyState.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. **STOP and VALIDATE**: Test User Stories 1 & 2 independently
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Stories 1 & 2 (P1 features)
   - Developer B: User Stories 3 & 4 (P2 features)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
