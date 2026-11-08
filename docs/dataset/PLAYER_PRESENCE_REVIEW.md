# Reviewed player-presence metadata

This is a manual review layer, not an automatic person detector. It is
separate from MediaPipe pose quality: missing landmarks do not imply that the
player is absent.

## Review CSV

The CSV is keyed by the original zero-based source `frame_index`:

```csv
frame_index,player_presence,notes
```

`player_presence` must be exactly one of:

- `PLAYER_PRESENT`
- `PLAYER_ABSENT`
- `UNCERTAIN`

Frames omitted from the CSV are treated as `UNCERTAIN`. Review rows do not
renumber or filter source frames. `notes` records the human evidence or
ambiguity rationale and may be empty.

## Summarize reviewed intervals

Run from `backend/`:

```powershell
python -m app.ml.scripts.diagnose_pose_sequence `
  path\to\video.mp4 `
  path\to\pose_sequence.csv `
  --output-dir path\to\diagnostics `
  --presence-review path\to\player_presence.csv `
  --presence-summary
```

The command prints one inclusive `start_frame,end_frame` pair per contiguous
`PLAYER_PRESENT` interval. `PLAYER_ABSENT`, `UNCERTAIN`, and frame-index gaps
break intervals. The summary does not alter pose or feature CSVs.
