# Compact VideoResizer UI — 2026-11-09

User approved the previous concrete proposal: reduce header clutter, keep only preview in sidebar, move scale/logo to Chỉnh video, show numbering only for %N, and make output settings focus on ratio + names. Implement directly in the existing tool path; preserve existing worker, naming plan, presets and previous installers.

1. resizer_ui.py: one compact header with preset selector, save, and overflow menu; single-line step navigation. Horizontal format choices. One name field with token insertion menu and compact live preview. Hide optional outro/performance sections behind clear expandable labels. Put existing scale/logo widgets in a modeless editor opened from the source selection. Sidebar contains only preview and enlarge action.
2. video_resizer.py: sync numbering visibility using the existing token syntax (%%N is literal), keep saved values when hidden; close/disable editor while exporting and on app close; reuse existing settings handlers. Keep export validation and collision protection unchanged.
3. test_ui.py: RED then GREEN for conditional numbering, editor state and busy lock, optional sections preserving values. Run full unittest discovery and packaged FFmpeg checks. Inspect real rendered screens at 1232x900 and 1100x720.
4. Package 1.1.1 with unchanged AppId, preserve 1.0.0/1.1.0 installers. Read-only reviewer checks changed UI/state integration. Smoke-test install/open/uninstall when permitted.

No new dependency, no new media feature, no profile migration, no Figma edit or remote push. Screenshots go to images/generated/videoresizer-compact-ui as configured by project.config.json.

Verification: 19 unittest tests passed. Package integration converted all three ratios with audio and Unicode paths. Rendered source/settings/review/editor screens inspected; numbering + primary settings fit at 1100x720. Reviewer found one selection-state issue; regression test observed failing, then passed after synchronizing editor close and edit-button state. Version 1.1.1 passed real silent installation, installed GUI startup, bundled FFmpeg encoding and uninstall. Older installers preserved. Separate-machine and real GPU-hardware tests were not run for this UI change.
