# Annotation Manifest Validator

The standalone validator checks the CSV schema and structural annotation rules
defined in [annotation_manifest_schema.md](./annotation_manifest_schema.md). It
does not infer labels, judge whether contact evidence is semantically
sufficient, create splits, or modify feature CSVs.

Run from `backend/`:

```powershell
python -m app.ml.scripts.validate_annotation_manifest `
  path\to\annotation_manifest.csv `
  --dataset-root path\to\dataset
```

Use `--json` for deterministic machine-readable diagnostics. Use
`--strict-single-sequence` only when a future approved policy requires one
feature sequence per movement; the current schema leaves multiple sequences per
movement unresolved.

Split leakage is checked only from explicit assignments; the validator never
creates splits. Provide a separate CSV with `video_id,split` and optional
`player_id` columns:

```powershell
python -m app.ml.scripts.validate_annotation_manifest `
  path\to\annotation_manifest.csv `
  --split-assignments path\to\split_assignments.csv `
  --check-player-split-leakage
```

Video grouping is always checked when assignments are supplied. Player
grouping is checked only with `--check-player-split-leakage`.

Diagnostics contain severity, CSV row number when applicable, field, and a
message. Missing external videos or feature CSVs are reported as warnings by
default so manifests can be checked before all external artifacts are mounted.
When `--dataset-root` is supplied, absolute and relative paths must resolve
inside that root; traversal and symlink escapes are errors. Missing but valid
paths remain warnings.
When a feature CSV is available, inclusive frame coverage is checked. Contact
validation is structural: `verified_contact` requires non-empty evidence and
an approved manual-review source. Ambiguous evidence remains a warning for
human semantic review; the validator does not determine whether contact
actually occurred.
