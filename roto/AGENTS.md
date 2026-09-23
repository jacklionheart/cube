# Rotisserie analysis boundaries

- Prefer cube-independent functions in this directory, with explicit inputs
  for paths, draft order, metadata, aliases, and analysis thresholds.
- Keep cube source registries, local data, defaults, and workbook layouts in
  `lol/` or `samp/`. Do not make shared algorithms branch on cube names.
- Blog prose and presentation belong in `../blog/`.
- Preserve each cube's results when extracting code. Compare workbook data
  and exercise both ordinary snake and double-pick drafts.
