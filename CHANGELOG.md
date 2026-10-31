# Changelog

## [0.2.0] - 2026-10-31

This is the first feature release since v0.1.0. Because the public API is
still pre-1.0, the two stricter import-error behaviours below are included in
the 0.2 minor release rather than a 1.0 major release.

### Added

- Expanded the formula engine with comparison and boolean expressions,
  short-circuiting conditionals, error propagation, absolute/mixed
  references, named expressions, and comprehensive math, statistical, text,
  date/time, lookup, criterion, information, and financial function families.
- Added CSV, native JSON, and XLSX import/export; XLSX import supports DEFLATE
  and shared strings when run on the zlib EigenScript build.
- Added stable sorting, find/replace, filtering, validation, pivot tables,
  Goal Seek, user-defined functions, cell styles, conditional formatting, and
  number formats.
- Added spreadsheet UI editing, formula bar and headers, range selection with
  live aggregates, copy/paste with relative-reference adjustment, undo/redo,
  delete-to-clear, and mouse-driven insertion.
- Added independent model, LibreOffice differential, data-operation, render,
  style, mouse, scale, clock-replay, and persistence oracles in CI.

### Changed

- Recalculation now uses an O(V+E) dependency pass and reuses evaluator state
  for substantially better large-sheet behaviour.
- The minimum supported EigenScript runtime is v0.48.0.

### Breaking changes

- Invalid XLSX and saved-sheet JSON inputs now raise filename-bearing errors instead of succeeding with an empty or damaged sheet (#75).
- `from_xlsx` now rejects structurally truncated worksheet and shared-string XML instead of hanging or partially importing it (#88).

### Fixed

- Sheet saves and XLSX exports now atomically replace their destination, preventing interrupted writes from corrupting an existing file (#68).
- Approximate VLOOKUP, HLOOKUP, LOOKUP, and MATCH now skip blank range cells (#70).
- `IRR` now returns `#NUM!` for same-sign cashflows and failed root searches (#71).
- The standalone setup now uses CI's pinned, zlib-enabled EigenScript runtime so XLSX imports work (#72).
- Spreadsheet aggregates now accept comma-separated ranges, cells, numbers, and expressions (#74).
- Malformed formulas, out-of-range cell references, and arithmetic overflow now report spreadsheet errors instead of plausible values (#76).
- Scientific-notation literals are now treated as numbers in typed input and imported files (#89).
- Exact-match lookup functions now skip blank cells instead of treating them as numeric zero (#90).

### Internal

- Documented a reproducible library install, synchronized release metadata, and added release automation (#77).
- CI now checks formula error branches, recalc resilience, and that xlsx import support cannot silently skip (#78).
