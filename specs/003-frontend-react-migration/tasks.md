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

- [ ] T001 Create frontend/ directory structure per plan.md (frontend/src/components/, pages/, hooks/, services/, lib/)
- [ ] T002 Initialize Vite + React 19.2 + TypeScript 5+ project in frontend/ with package.json, tsconfig.json, vite.config.ts
- [ ] T003 [P] Install core dependencies: react, react-dom, react-router-dom, fetch (native), vitest, @testing-library/react
- [ ] T004 [P] Configure TypeScript strict mode in tsconfig.json per research.md decisions
- [ ] T005 [P] Configure Vite for production builds with proper asset handling and environment variables
- [ ] T006 [P] Set up ESLint and Prettier configuration for code quality
- [ ] T007 Create basic HTML template (index.html) and main.tsx entry point
- [ ] T008 Update Dockerfile for multi-stage build: Node.js frontend build → serve static files from backend
- [ ] T009 Update docker-compose.yml to expose frontend port and mount static files
- [ ] T010 Create .env.local template with VITE_API_BASE_URL=http://localhost:8000/api

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 [P] Create TypeScript interfaces for API contracts in frontend/src/lib/types.ts (Stream, StreamResponse, NewStreamRequest, EditStreamRequest, ErrorResponse)
- [ ] T012 [P] Implement API service layer in frontend/src/services/api.ts using native Fetch with error handling, timeouts, and type safety
- [ ] T013 [P] Create utility functions in frontend/src/lib/utils.ts for URL masking, validation helpers, and common operations
- [ ] T014 [P] Set up React Router v6 configuration in App.tsx with routes for dashboard, add, edit, play pages
- [ ] T015 [P] Create shared layout component in frontend/src/components/Layout.tsx with navigation and consistent styling
- [ ] T016 [P] Port existing CSS from src/templates/*.html to frontend/src/lib/styles.css preserving visual design
- [ ] T017 [P] Create reusable UI components: Button, Input, LoadingSpinner, ErrorMessage in frontend/src/components/ui/
- [ ] T018 [P] Implement custom hooks: useStreams for stream management, useApi for API state in frontend/src/hooks/

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Stream Dashboard (Priority: P1) 🎯 MVP

**Goal**: Display main dashboard showing all configured RTSP streams with real-time status

**Independent Test**: Load dashboard URL and verify stream list displays with status indicators updating every 2 seconds

### Implementation for User Story 1

- [ ] T019 [US1] Create Dashboard page component in frontend/src/pages/Dashboard.tsx with stream list layout
- [ ] T020 [P] [US1] Create StreamCard component in frontend/src/components/StreamCard.tsx showing name, masked URL, status badge, and action buttons
- [ ] T021 [P] [US1] Create EmptyState component in frontend/src/components/EmptyState.tsx for when no streams exist
- [ ] T022 [US1] Implement real-time status polling in Dashboard using useStreams hook (every 2 seconds)
- [ ] T023 [US1] Add navigation header with "ProxiMeter" title and "Add Stream" button in Layout component
- [ ] T024 [US1] Implement stream list rendering with responsive card layout (768px+ breakpoint)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Add New Stream (Priority: P1)

**Goal**: Provide form interface for adding new RTSP streams with validation

**Independent Test**: Navigate to add stream form, submit valid data, verify stream appears in dashboard

### Implementation for User Story 2

- [ ] T025 [US2] Create AddStream page component in frontend/src/pages/AddStream.tsx with form layout
- [ ] T026 [P] [US2] Create StreamForm component in frontend/src/components/StreamForm.tsx (reusable for add/edit) with validation
- [ ] T027 [US2] Implement form validation: name required, RTSP URL format, threshold 0-1 range
- [ ] T028 [US2] Add form submission handling with loading states and error display
- [ ] T029 [US2] Implement success navigation back to dashboard after stream creation
- [ ] T030 [US2] Add cancel button returning to dashboard without saving

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Edit Existing Stream (Priority: P2)

**Goal**: Allow modification of existing stream configuration

**Independent Test**: Edit a stream via dashboard action, verify changes persist and display correctly

### Implementation for User Story 3

- [ ] T031 [US3] Create EditStream page component in frontend/src/pages/EditStream.tsx with pre-populated form
- [ ] T032 [US3] Reuse StreamForm component for edit functionality with initial values
- [ ] T033 [US3] Implement route parameter handling for stream ID in edit page
- [ ] T034 [US3] Add delete stream functionality with confirmation dialog
- [ ] T035 [US3] Handle stream not found errors with redirect to dashboard
- [ ] T036 [US3] Implement form pre-population from API data on page load

**Checkpoint**: User Stories 1, 2, AND 3 should now be independently functional

---

## Phase 6: User Story 4 - Play Live Stream (Priority: P2)

**Goal**: Display live RTSP stream video in browser with controls

**Independent Test**: Select play action from dashboard, verify video playback starts within 3 seconds

### Implementation for User Story 4

- [ ] T037 [US4] Create PlayStream page component in frontend/src/pages/PlayStream.tsx with video container
- [ ] T038 [P] [US4] Create VideoPlayer component in frontend/src/components/VideoPlayer.tsx with HTML5 video element
- [ ] T039 [US4] Implement MJPEG stream URL construction and video source setup
- [ ] T040 [US4] Add video player controls: play/pause, volume, fullscreen
- [ ] T041 [US4] Implement error states: stream unavailable, unsupported codec, network error
- [ ] T042 [US4] Add loading state with spinner during video initialization
- [ ] T043 [US4] Implement back navigation to dashboard from play page

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T044 [P] Update README.md with frontend development setup and build instructions
- [ ] T045 [P] Add component documentation and prop types in code comments
- [ ] T046 [P] Optimize bundle size and verify <500KB gzipped production build
- [ ] T047 [P] Implement responsive design touch targets (minimum 44x44px)
- [ ] T048 [P] Add error boundaries for graceful error handling across components
- [ ] T049 [P] Update artifacts/versions.md with React 19.2, TypeScript, Node.js versions
- [ ] T050 [P] Test production build in Docker environment
- [ ] T051 [P] Validate quickstart.md instructions work correctly

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