# Product Requirements Document: Desktop → Web CSV Browser Migration

**Version:** 0.1  
**Date:** 2025-12-04  
**Status:** Draft

---

## 1. Executive Summary

The desktop CSV Browser (Tkinter + pandastable) delivers a power-user workflow with advanced file management, filtering, and plotting capabilities. The Streamlit-based web prototype offers easier distribution but lacks most of the desktop feature set. This PRD describes how to migrate the complete desktop functionality to a modern web experience while maintaining the performance, workflow depth, and reliability that existing users depend on.

### Recent Progress (2025-12-04)

- ✅ Streamlit sidebar now exposes multi-select **Copy**, **Move**, **Rename**, and **Delete** actions with overwrite handling and confirmation flows.
- ✅ File operation destinations and rename templates reuse the shared `saved_filters` store, giving users persistent presets (parity with desktop quick-pick menus).
- ✅ Automated tests cover rename-template formatting and copy/move flows to guard against regressions.
- ✅ Plot parity workstream unlocked: 3D scatter/surface/wireframe, Gantt timelines, Touchstone-based S-parameter plots, jitter histograms, and phase-noise charts are live in the Streamlit UI with persisted settings.

---

## 2. Goals & Non-Goals

### 2.1 Goals

1. **Feature Parity:** Deliver all high-value desktop features (file browser, filters, plotting, file ops, settings persistence) in the web UI.
2. **Unified Codebase:** Share business logic for filtering, plotting, and settings where possible to reduce duplication.
3. **Improved Collaboration:** Enable browser-based access with shareable URLs and optional authentication.
4. **Progressive Rollout:** Allow staged rollout so teams can validate workflows before sunsetting the desktop app.

### 2.2 Non-Goals

- Rewriting pandastable or PlotViewer internals.
- Adding completely new analysis modes beyond those in the desktop app.
- Supporting offline browser usage (desktop app remains for air-gapped users during transition).

---

## 3. Current State Overview

| Area | Desktop (Tkinter) | Web (Streamlit) | Gap Impact |
|------|-------------------|-----------------|------------|
| File Browser | Rich table (sorting, filters, filename fields) | Simple list filter | Loss of discovery efficiency |
| File Ops | Move/Copy/Delete/Merge/Rename, open in Excel/Spotfire | None | Missing core workflow |
| CSV Viewer | Pandastable grid with column search/filter/save | Basic `st.dataframe` | Lacks column ops & persistence |
| Plotting | pandastable PlotViewer with save/load settings | Simple Matplotlib buttons | Advanced plotting unavailable |
| Settings | JSON persistence (recent dirs, filters, plots) | None | No continuity between sessions |
| Shortcuts | Ctrl+F/O/R, F5, Escape, custom tooltips | None | Lower productivity |

---

## 4. Product Requirements

### 4.1 Functional Requirements

1. **File Browser & Management**
   - FR1.1: Render directory tree + tabular file list with sortable columns and multi-select actions.
   - FR1.2: Support include/exclude filters, saved filters, and recent directories.
   - FR1.3: Provide Move, Copy, Delete (Recycle Bin if Windows), Merge CSV, Rename from field pattern, and Open-in (Excel/Spotfire) equivalents where possible.
   - FR1.4: Surface file metadata (size, modified) and parsed filename fields.

2. **CSV Viewing & Filtering**
   - FR2.1: Provide a column-aware grid (fixed header, horizontal scroll) with row filtering syntax identical to desktop (`query`, text, `@`, wildcard).
   - FR2.2: Implement column search, column filter (`!`, quotes, `*`), save/load filter presets, and “Move column to start”.
   - FR2.3: Allow saving filtered data to CSV.

3. **Plotting & Analysis**
   - FR3.1: Reuse plotting utilities (scatter, line, histogram, shmoo, bathtub, eye) with parameter UI parity.
   - FR3.2: Persist plot settings per user/session (global options, matplotlib opts, layout) and auto-restore on plot open.
   - FR3.3: Provide correlation analysis workflow (Top N, plots, export).
   - FR3.4: Deliver interactive viewer features (zoom, pan, hover) comparable to PlotViewer (likely via Plotly or matplotlib widgets).
   - FR3.5: Implement S-parameter plotting that ingests `.s2p`/`.s4p` Touchstone files (magnitude/phase, multi-port selection, log-frequency axes) instead of CSV-only inputs.
   - FR3.6: Expose the desktop 3D plot suite—scatter3D, surface, wireframe—with data-mode controls (grid vs parametric), stride settings, color maps, and optional point overlays.
   - FR3.7: Provide jitter analysis via histogram plots with Gaussian overlays, configurable bins, and stats panel (mean/σ/min/max) matching desktop tooling.
   - FR3.8: Provide phase-noise plots with log-scaled offset frequency, selectable noise columns, carrier-frequency annotations, and export parity with the desktop viewer.

4. **Settings & Persistence**
   - FR4.1: Store recent directories, saved filters, plot/table settings in a backend (filesystem, DB, or user config file) with user scoping.
   - FR4.2: Support import/export of settings for migration.

5. **User Experience**
   - FR5.1: Provide keyboard shortcuts for frequent actions.
   - FR5.2: Mirror tooltip/help content from desktop (filter instructions, column tips).
   - FR5.3: Support light/dark theme toggles aligned with Streamlit’s styling.

### 4.2 Technical Requirements

- TR1: Adopt Streamlit (or Streamlit + React components) as the primary framework; ensure compatibility with existing `utils.py` / `plotting_utils.py` (refactor to shared core module if needed).
- TR2: Create a service layer for file operations with OS safeguards (permission checks, undo where possible).
- TR3: Implement state persistence via Streamlit session state + server-side storage (e.g., SQLite/JSON per user) to survive reruns.
- TR4: Replace pandastable-specific plotting hooks with a web-friendly component (Plotly, matplotlib in Streamlit, or custom JS) that can apply saved settings.
- TR5: Ensure large CSV handling remains performant by streaming previews or chunked loading.

### 4.3 Success Metrics

- SM1: ≥90% of surveyed desktop power users report feature parity for their workflows.
- SM2: Web app opens, filters, and plots a 500k-row CSV within 5 seconds for typical operations.
- SM3: <5% regression tickets after sunset of desktop app.

---

## 5. User Stories

1. **As a validation engineer**, I can apply my saved filename filters in the browser to locate test runs within 2 clicks.
2. **As a data analyst**, I can adjust shmoo thresholds and replot without losing my previous column selection.
3. **As a lab technician**, I can rename batches of CSVs using embedded metadata from the filename via the web UI.
4. **As a team lead**, I can share a URL that opens the browser to the same directory and filters for review.

---

## 6. Architecture & Design Considerations

- **Shared Core Modules:** Move filtering logic (`utils.apply_row_filter`, `apply_column_filter`) and plotting helpers into a common `csv_browser_core` package imported by both desktop and web.
- **State Persistence:** Introduce a storage abstraction (e.g., `SettingsStore`) with implementations for desktop (JSON) and web (server-side DB) to keep behavior consistent.
- **Plot Viewer Replacement:** Evaluate Plotly Express + custom controls to replicate PlotViewer’s zoom/pan/hover while honoring saved settings.
- **File Operations API:** Encapsulate file operations in a backend API to mitigate Streamlit’s stateless reruns and allow future multi-user governance.
- **Security:** Add optional authentication (e.g., environment-controlled basic auth) when exposing file operations over the network.

---

## 7. Migration Plan & Milestones

| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| Phase 0 – Foundations | Week 1-2 | Shared core module, settings store abstraction, Streamlit layout scaffolding |
| Phase 1 – File Browser Parity | Week 3-5 | Advanced file list, filters, saved filters, recent dirs, file ops API |
| Phase 2 – CSV Viewer & Filters | Week 6-8 | Column search/filter UI, save/load presets, column move, export filtered CSV |
| Phase 3 – Plotting & Analysis | Week 9-12 | Plot controls, Plotly-based viewer, plot settings persistence, correlation analysis |
| Phase 4 – QA & Rollout | Week 13-14 | Performance testing, regression suite, user acceptance, documentation, desktop sunset plan |

### 7.1 Plot Parity Workstream (New Types)

| Milestone | Scope | Notes |
|-----------|-------|-------|
| P3.A – S-Parameter Loader | Implement Touchstone parser (`.s2p`/`.s4p`), port/phase plotting, magnitude/phase toggles, log-frequency axes, multi-port selection, trace overlays | ✅ Completed – Streamlit special plots now accept uploads/browser selections, persist selection state, and render via new Touchstone utilities |
| P3.B – Jitter & Phase Noise Plots | Reuse desktop algorithms for TJ/dual-Dirac decomposition and phase-noise integration; add controls for histogram bins, Gaussian overlays, carrier frequency, offset range, and stats panel | ✅ Completed – Added `plot_jitter`/`plot_phase_noise`, UI controls, and plot-state persistence |
| P3.C – Gantt View | Provide task/group aggregations against datetime columns, progress bars, “today” marker, milestone overlay, sort/group options | ✅ Completed – Matplotlib Gantt helper + Streamlit controls with saved state |
| P3.D – 3D Plot Suite | Bring scatter3D, surface, wireframe modes with parametric/grid modes, stride sliders, point overlays, and camera controls (azimuth/elevation/dist) | ✅ Completed – 3D plotting helpers wired into special plots tab with stride/log controls |
| P3.E – Integration & Persistence | Extend plot-state schema to capture new controls (Touchstone port selection, 3D view angles, jitter options) and ensure import/export paths cover them | ✅ Completed – `DEFAULT_PLOT_STATE` expanded for 3D, Gantt, S-parameters, jitter, and phase-noise settings |

Each milestone is scoped to ~1 week of dev/test effort and can be executed sequentially within Phase 3 or pulled earlier if bandwidth allows.

---

## 8. Dependencies

- Availability of backend storage (local filesystem vs managed DB) for settings.
- Plotly or equivalent library licensing/compatibility.
- Operations approval for exposing file operations over network.
- Desktop code refactoring bandwidth to create shared modules.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation for large CSVs in browser | High | Use lazy loading, caching, and profiling early (Phase 0 prototypes). |
| File operation permissions in multi-user environments | Medium | Run Streamlit app under service account with scoped ACLs; add confirmation dialogs. |
| Plot parity gap due to PlotViewer-specific behavior | Medium | Map essential features first (zoom, pan, annotations) and document deltas; keep desktop fallback until parity confirmed. |
| Session state loss on Streamlit reruns | Medium | Centralize state in server-side store and wrap long operations in cached functions. |
| User adoption resistance | Low/Medium | Provide dual-run period, training docs, and change log. |

---

## 10. Acceptance Criteria

1. All FR items validated via automated + manual tests.
2. Comparison checklist (from `CSV_BROWSER_COMPARISON.md`) shows no “Desktop-only” items remaining except explicit non-goals.
3. Performance benchmark met (SM2).
4. Documentation updated (Quick Start, User Guides, Admin Guide).
5. Sign-off from at least three representative power users.

---

## 11. Open Questions

1. Do we require authentication/authorization out of the gate, or is LAN-only deployment acceptable initially?
2. Should file operations be logged/audited for compliance?
3. How do we handle external integrations (Excel/Spotfire) in environments without those applications installed?
4. Do we need multi-user concurrency controls when multiple people edit filters/settings simultaneously?
