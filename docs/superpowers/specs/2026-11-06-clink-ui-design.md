# VideoResizer Clink UI and output naming

Approved direction: the user requested implementation after the three-step Clink proposal, and explicitly added output filename settings and flow improvements.

Keep Python/PyQt5 and the existing FFmpeg processing, profiles, three ratios, logo controls and outro behavior. Apply the provided Figma navy/yellow palette, Be Vietnam Pro typography, rounded controls, three-step navigation, persistent preview and export footer. Adapt to desktop height with independently scrolling workspace/sidebar. Do not add Clink's separate hook-combination engine.

1. Sources: add/drop videos, select/remove entries, optional outro per ratio, per-video scale/logo with apply-all.
2. Settings: ratios, performance, encoder, FPS, naming. Tokens %F original stem, %N continuous output sequence, %S ratio (9x16/16x9/1x1), %D batch date YYYYMMDD, %% literal percent. Default %F_%S; number start >=1, padding 1-6. Preserve source extension. Show live names, validation and collision resolution.
3. Review: real planned output paths, source and ratio; total outputs, export and progress/log. Number increases per output, not per source. Export uses precisely the reviewed plan, with private retry staging and exclusive publishing; never overwrites inputs/existing files. Automatically suffix duplicate basenames.

Persist naming/format choices in profiles; legacy profiles load defaults. Keep source files and old installer intact. Ship 1.1.0 installer with local fonts/assets and tests. Verify offscreen PyQt renders, real FFmpeg integration and bundle contents. Application Control previously blocked unsigned EXEs, so report any remaining launch/install limitation.

Approach: refactor setup_ui into a focused PyQt UI module, share a pure output planner between UI/worker, use QSS. A recolor alone does not improve flow; rewriting in web/Electron would add a second runtime unnecessarily.
