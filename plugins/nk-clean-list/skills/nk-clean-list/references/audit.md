# Audit contract

`audit.json` is UTF-8. Counts are computed from rows, never inferred from group sizes
or report text. A run validates the conservation equation before writing outputs.

## Fixed keys

- `counts`: `in`, `clean`, `merged`, `empty`, `not_contact`, `uncertain_pairs`.
  `clean` counts `kept` rows; other disposition counts use their exact names.
- `sources`: file basename, SHA-256, `header_rows`; XLSX entries also have `sheet`.
- `rows`: one object for every counted input row, with `file`, `row`, `disposition`.
  Contact rows have `record`; merged and not_contact rows have a readable `reason`.
  XLSX rows also have `sheet` to disambiguate equal row numbers on different sheets.
- `uncertain`: objects with exactly two distinct `records`, a `reason`, and source
  `evidence`. Each contact pair appears once; multiple source-row reasons are retained.

## Additional keys

- `rows[].original`: unmodified decoded CSV cells or XLSX cell content. The sequence
  retains column order, empty cells and original spelling. Original numeric XLSX
  tokens, types and formulas are in `cell_metadata`.
- `rows[].cleaned`, `changes`, `issues`: per-row normalized values, before/after
  account, and unsupported/invalid values. Noncontact rows still retain originals.
- `rows[].matched_to`: direct source-row witness for a merge, including sheet.
- `records`: assembled clean contacts, primary name/organisation, all normalized
  variants, observed values, source rows, assembly rule and before/after changes.
- `values_needing_review`: unresolved values, including unsupported or ambiguous
  pinyin names without a candidate partner. These are not invented contact pairs.
- `sources[].original_header_values`, `headers`, `column_roles`: original preamble,
  displayed headers and detected column interpretation.
- `sources[].column_role_evidence`: per-column header hints, sampled value-shape
  counts, selected role and reason. The workbook's Column roles sheet renders it.
- `warnings`: source-specific limitations, including `missing_name_column`. These
  appear before the count in the terminal and report, and in the workbook Summary.
- XLSX source metadata includes original `styles_xml`, `merged_cells`, `date1904`.
- `original_files`: one object per input file, with basename, SHA-256 and `base64`
  containing its original bytes. This preserves quoting, encodings, trailing blanks,
  styles, formulas, and every other source-file property for exact restoration.

The identity of a row is `(file, sheet if present, row)`. A record has exactly one
kept row. Every other member is merged with a direct witness and a checkable reason.

## Recover a row or file

For CSV, `original` gives its cell values without normalization. To recover original
quoting/line endings as well, restore the entire original file. The `--restore`
command validates base64 and SHA-256 before writing into a new folder. It refuses
unsafe filenames, duplicate filenames and an existing output directory.

For XLSX, original values plus cell metadata can reconstruct cell content. Full-file
restoration is the exact route for styles, merged cells and formula caches. Restored
source files may contain their original formulas; the cleaned output workbook does
not execute those formulas.

The report and workbook render audit data. The report is static escaped HTML with a
restrictive content security policy. It needs no server and runs no JavaScript.
