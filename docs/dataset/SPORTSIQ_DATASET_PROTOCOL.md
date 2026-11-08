# SportsIQ Initial Pose-Sequence Dataset Protocol

Status: proposal for dataset planning and pilot annotation.  
This document does not describe a trained model or an existing labeled dataset.

## 1. Initial ML objective

The first proposed objective is **movement-phase recognition for a badminton
overhead-smash-like movement**, using a timestamped pose sequence and its
diagnostic quality metadata. The first dataset should recognize the phase of a
candidate movement, rather than decide whether a player performed a technically
good stroke.

These are different tasks:

- **Movement-phase recognition:** identify where a candidate movement is in its
  preparation, swing, contact-adjacent, or recovery timeline.
- **Stroke classification:** identify the stroke type, such as overhead smash,
  clear, or drop. This requires broader stroke coverage and should not be
  inferred from the phase labels alone.
- **Technique-quality assessment:** judge execution quality against a defined
  coaching rubric. This requires reviewed quality criteria and likely
  player/context information; it is not supplied by the current pose features.

The current system only extracts pose observations and diagnostic features. It
does not currently perform any of these three tasks, and no classifier should
be considered trained until a reviewed dataset and training/evaluation
pipeline exist.

## 2. Candidate label taxonomy

Each interval receives one movement-phase label. `unknown` is an abstention
outcome, not a normal movement phase. `contact` is a special evidence-backed
event label/status and is not part of the initial classifier target by default.

| Label | Operational definition | Observable pose cues | Likely ambiguity | First version |
|---|---|---|---|---|
| `preparation` | The player is organizing the body and racket before the backswing or loading action begins. | Stable or preparatory racket-arm position; shoulder and wrist begin positioning; trunk/feet may be preparing. | Boundary with `recovery` from a prior movement and with early `backswing`; pose-only cues may be subtle. | Yes, if the start boundary can be reviewed in video. |
| `backswing` | The racket arm is moving into the loaded position before forward acceleration. | Racket-side wrist/elbow trajectory moves toward the loaded position; shoulder/arm elevation may increase. | Camera view, occlusion, and partial clips can make direction ambiguous; pose motion alone does not establish intent. | Yes, provisionally. |
| `forward_swing` | The racket arm and associated body segments are moving toward the presumed striking region after loading. | Increasing forward/upward wrist movement, changing elbow angle, and continued shoulder/arm motion. | The exact transition from backswing is subjective; velocity features are not ground truth for stroke intent. | Yes, provisionally. |
| `contact` | A narrowly defined event in which available video evidence supports actual shuttle contact. | Video may show racket/shuttle interaction; pose may provide context but does not prove contact. | The shuttle and racket may be occluded or absent; a single frame is especially hard to verify. | Exclude from the first classifier target unless verified examples exist and the project owner approves inclusion. |
| `follow_through` | The movement after the presumed striking event while the arm/body continue past the striking position. | Wrist and elbow continue beyond the presumed contact configuration; motion direction/angle changes after the peak event. | Without verified contact, the boundary from late `forward_swing` is uncertain. | Yes, only with a documented boundary rule. |
| `recovery` | The player returns from the overhead movement toward a neutral or ready position. | Arm lowers or returns; pose motion settles toward the next ready position. | May overlap with preparation for the next stroke, and short clips may not include enough recovery. | Yes when the return is visible. |
| `unknown` | The phase cannot be assigned reliably from the available video and pose evidence. | Missing/low-confidence landmarks, occlusion, cut-off clip, unclear movement, or disagreement between reviewers. | It is an abstention outcome rather than a normal movement class; its reasons must be retained. | Yes, as an explicit abstention outcome. |

`contact_candidate` is an annotation status or event marker, not an ordinary
movement-phase class. It records that the interval deserves contact review or
contains a possible contact event. It must not be assigned solely from wrist
displacement, elbow angle, landmark visibility, or a temporal feature peak.
`contact` is assigned only when the available video evidence supports actual
shuttle contact, which may require visible shuttle/racket interaction. If that
evidence is unavailable, retain `contact_candidate` evidence/status and use
`unknown` for the phase when necessary. The initial classifier target excludes
`contact` unless verified examples are available and the project owner
explicitly approves inclusion.

## 3. Dataset unit and annotation rules

### Dataset unit

The initial annotation unit is one contiguous labeled frame interval within
one source video, representing one phase of a candidate movement by one player.
A complete candidate movement may contain multiple intervals, such as
`preparation`, `backswing`, `forward_swing`, `follow_through`, and `recovery`.
Do not require one dominant label for the complete movement. Adjacent
intervals may belong to the same movement.

Each interval receives exactly one phase label or an explicit `unknown`
abstention outcome. The interval references the exported temporal-feature CSV;
it does not duplicate feature values in the annotation metadata.

The current exporter produces one row per frame with `frame_index` and
`timestamp_ms`, normalized racket-arm coordinates, 2D/optional 3D elbow angle,
shoulder elevation, wrist displacement/velocity, elbow angular velocity,
visibility/presence, and overall/racket-arm quality fields. These are the
feature fields available for a first pilot. Their formulas and the existing
confidence threshold remain unchanged.

### Start and end frames

Annotators should choose the earliest and latest frames needed to show the
candidate movement and enough context to establish its phase boundaries. Do not
assume a fixed number of frames or duration: the current validation artifact
contains 159 pose rows with timestamps, but that is an observation about one
artifact, not a dataset-wide duration rule.

Start and end are inclusive source-video frame indices. The corresponding
timestamps should be retained for review, but `start_frame` and `end_frame`
remain the primary reproducible range identifiers.

### Phase boundaries and transitions

- Assign exactly one phase label to each contiguous interval.
- Keep adjacent intervals from the same complete movement as separate samples
  when their phase boundaries are reviewable.
- Prefer boundaries at observable changes in movement direction or intent,
  documented in reviewer notes.
- `start_frame` and `end_frame` are inclusive source-video frame indices.
- Intervals must not overlap within the same movement. Overlapping intervals
  require a future protocol version that explicitly defines how overlapping
  labels are represented and evaluated.
- Uncertain boundaries must be documented in `uncertainty_reason` and `notes`;
  use `unknown` when the phase cannot be assigned reliably rather than
  concealing the uncertainty in a dominant label.
- If the pilot shows that transitional intervals are common and materially
  different, add a versioned transition policy rather than silently changing
  labels.
- Do not create labels from the feature CSV alone when the original video is
  needed to determine intent or contact.

### Uncertainty and pose quality

Annotators must be able to mark an interval uncertain. Use `unknown` when the
phase or boundaries cannot be assigned with reasonable confidence, and record
the reason in the manifest. The following controlled uncertainty-reason list is
proposed for pilot review: `occlusion`, `low_pose_confidence`,
`ambiguous_phase_boundary`, `unclear_movement`, `insufficient_video_context`,
`reviewer_disagreement`, and `other`. This list is not final until reviewed
against pilot annotation cases.

Missing landmarks and low-confidence observations are preserved as missing in
the feature CSV. They must not be interpolated or replaced with zeros during
annotation. A sample may remain in the pilot when the racket arm is usable but
the bilateral overall quality is unreliable; the per-frame
`racket_arm_quality_status` and reasons must be retained for later filtering.
Samples with insufficient usable evidence should be labeled `unknown`, not
silently discarded. The exact minimum usable-frame rule is an open decision for
the pilot and should be measured before being fixed.

## 4. Dataset metadata schema

The following is a proposed row-level manifest schema. It is separate from the
feature CSV and should be versioned with it.

| Field | Purpose | Proposed valid values |
|---|---|---|
| `movement_id` | Groups all phase intervals belonging to one complete candidate movement. | Stable opaque identifier, e.g. `movement_<id>`. |
| `interval_id` | Identifies one contiguous labeled interval within the movement. | Unique opaque identifier, e.g. `interval_<id>`. |
| `sequence_id` | Stable identifier for the feature-sequence source or exported sample. | Unique opaque identifier; may reference the source feature sequence. |
| `video_id` | Links samples to the source recording and prevents split leakage. | Stable identifier for one source video. |
| `player_id` | Anonymous grouping key for player-level split checks. | Anonymous stable ID; never a name or personal identifier. |
| `racket_side` | Selects the arm used by the temporal feature extractor. | `left`, `right`, or `unknown`, matching `PoseSequence`. |
| `start_frame` | Inclusive first source-video frame. | Non-negative integer. |
| `end_frame` | Inclusive last source-video frame. | Integer greater than or equal to `start_frame`. |
| `movement_label` | Phase assigned to this interval or an abstention outcome. | `preparation`, `backswing`, `forward_swing`, `follow_through`, `recovery`, or `unknown`; `contact` requires the special evidence rule below. |
| `label_source` | Explains how the label was established. | Proposed values: `manual_video_review`, `manual_video_and_shuttle_review`, `consensus_review`; do not use `model` for this first dataset. |
| `annotation_status` | Describes the maturity of this interval annotation. | Proposed values: `unreviewed`, `provisional`, `second_reviewed`, `adjudicated`, `frozen`, `rejected`. |
| `contact_candidate_status` | Records whether contact review was requested or a possible event was observed without making it a phase class. | Proposed values: `not_marked`, `candidate`, `verified_contact`, `not_contact`, `uncertain`. |
| `contact_evidence` | Describes evidence supporting a contact candidate or verified contact. | Proposed values such as `shuttle_visible`, `racket_shuttle_interaction_visible`, `video_review_only`, `not_observed`, `unclear`; exact controlled list is open. |
| `feature_csv_path` | Reproducible path to the exported feature rows. | Repository-relative or dataset-manifest-relative path. |
| `source_video_path` | Identifies the original video used in review. | Controlled storage path or URI; access rules are an open operational decision. |
| `camera_view` | Records viewpoint differences that may affect visibility. | Proposed controlled value such as `side`, `front`, `rear`, `diagonal`, `unknown`. |
| `annotator_id` | Records who made the annotation without exposing personal identity. | Anonymous reviewer ID. |
| `uncertainty_reason` | Records why an interval is `unknown` or has uncertain boundaries. | Proposed controlled list: `occlusion`, `low_pose_confidence`, `ambiguous_phase_boundary`, `unclear_movement`, `insufficient_video_context`, `reviewer_disagreement`, `other`. |
| `protocol_version` | Ties each row to the rules used. | Version string such as `v0.1`. |
| `notes` | Captures boundary, occlusion, shuttle visibility, or review context. | Free text with no sensitive personal data. |

The current exporter writes `quality_status`, `quality_reasons`,
`racket_arm_quality_status`, and `racket_arm_quality_reasons` per frame. The
manifest need not duplicate these values; it should point to the feature CSV
and use notes or summary fields only when an interval-level decision is needed.
`annotation_status` is the canonical annotation lifecycle field; it replaces
the earlier draft's `review_status` name to avoid maintaining two fields for
the same state.

## 5. Annotation workflow

1. **Select candidate clips.** Identify source-video intervals that may contain
   an overhead movement. Assign a `movement_id`, then identify contiguous
   phase intervals within it. Record video and player grouping metadata before
   splitting or labeling.
2. **Export pose features and diagnostics.** Run the existing validation and
   temporal-feature exporters with the known racket side when available.
3. **Review original video beside overlays.** Use the diagnostic tooling to
   compare the original frames, MediaPipe landmarks, angles, confidence, and
   missingness. Treat model-relative `z` as diagnostic only, not calibrated
   physical depth.
4. **Assign provisional interval labels.** Record one label per contiguous
   interval, inclusive frame boundaries, evidence, and any contact/shuttle
   visibility. Adjacent intervals may belong to the same movement.
5. **Mark uncertainty.** Use `unknown` or an uncertainty field for occlusion,
   unclear boundaries, missing evidence, or disagreement with the pose
   overlay. Never turn a diagnostic angle peak into a contact label
   automatically.
6. **Second-review a subset.** Have a second reviewer independently check a
   predefined subset, including difficult, `unknown`, and contact-candidate
   intervals. Resolve disagreements using an adjudication rule recorded with
   the protocol version.
7. **Freeze a versioned dataset.** Freeze only after metadata validation,
   review completion, source-video grouping checks, and feature-export
   reproducibility checks pass. Later corrections create a new dataset version.

## 6. Dataset split strategy

Do not split adjacent frames from one movement across train and test. Those
frames are highly correlated and can make evaluation appear strong without
testing generalization. A random frame-level split is prohibited. All
intervals from one source video must remain in one split; placing different
intervals from the same source video in different splits leaks camera,
background, player, and movement-specific patterns.

The recommended strategy is grouped splitting by `video_id`. Player-grouped
evaluation is preferred when enough independent players are available, so a
player's movements do not occur in both train and test. A validation split
should use the same grouping rule. Exact
percentages are intentionally not prescribed: they depend on the number of
videos, players, labels, and whether a held-out player evaluation is feasible.
If the pilot is small, report the limitation rather than weakening the
grouping rule to obtain larger frame counts.

The split manifest must record dataset version, split assignment, grouping
keys, and the procedure or seed used to reproduce the assignment. An interval,
movement, and source video must belong to exactly one split.

## 7. First milestone and acceptance criteria

Start with a small pilot covering the available movement diversity and
viewpoints, rather than scaling before the labels are understood. The pilot
does not yet exist; its size and composition are open decisions that should be
set after counting eligible source videos and anonymous players.

The pilot can be accepted as a dataset-protocol milestone when it meets
measurable criteria such as:

- **Label clarity:** every frozen interval has exactly one allowed phase label
  or an explicit `unknown` uncertainty outcome, inclusive valid frame bounds,
  a documented `label_source`, and a recorded uncertainty decision.
  Second-review disagreement and adjudication outcomes are reported; no target
  agreement rate is assumed before the pilot is measured.
- **Interval validity:** `start_frame` and `end_frame` are valid inclusive
  bounds within the source video, and intervals within the same
  `movement_id` do not overlap unless an explicitly approved protocol version
  allows overlap.
- **Contact evidence:** every `contact` label has supporting video evidence
  recorded in `contact_evidence` and a permitted label-source/review status.
  Contact candidates are represented by `contact_candidate_status` and are not
  silently converted into ordinary phase labels.
- **Review completion:** every included sample has at least one completed
  manual review; the predefined second-review subset is complete; unresolved
  disagreements are not marked `frozen`.
- **Feature availability:** every manifest row resolves to an existing source
  video, the expected feature CSV, and the inclusive frame range. Missing
  values remain explicit, and a reported
  coverage summary distinguishes missing/unreliable frames from valid frames.
  No minimum coverage threshold is fixed until pilot distributions are known.
- **Split integrity:** no `video_id` occurs in more than one split, and no
  `player_id` occurs across splits when player-grouped evaluation is selected.
  The check is automated and recorded with the dataset version.
- **Reproducibility:** the source video, feature CSV, frame bounds,
  `racket_side`, exporter command/options, protocol version, and code revision
  are recorded. Re-running the documented exporter reproduces the selected
  rows and schema without interpolation or fabricated values.

## Open decisions

The following are proposals requiring project-owner confirmation:

- Whether the first classifier target should use all phase labels or begin with
  a smaller subset such as `preparation`, `backswing`, `forward_swing`,
  `follow_through`, and `recovery`.
- Whether verified shuttle/racket evidence is sufficient to use `contact`, or
  whether the first release should use `contact_candidate` plus `unknown`.
- The minimum usable racket-arm frame coverage for retaining a sample.
- The controlled uncertainty reason codes and second-review sampling rate.
- The storage/access convention for source videos and feature CSVs.
- The pilot's number of videos, players, viewpoints, and label balance.
