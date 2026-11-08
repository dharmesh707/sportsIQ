# Annotation Manifest Schema

Status: specification proposal aligned with
[SPORTSIQ_DATASET_PROTOCOL.md](./SPORTSIQ_DATASET_PROTOCOL.md). This document
does not define a training pipeline or a reviewed dataset.

The manifest is a CSV with one row per contiguous annotated phase interval.
It references the existing temporal-feature CSV and source video; it does not
duplicate per-frame feature values.

## Identifier semantics

The recommended approach is globally unique opaque IDs for all four identifier
fields. Global uniqueness avoids ambiguity when manifests are merged across
dataset versions or storage locations. IDs should be stable after creation and
must not encode personal information. A UUID or a project-generated opaque
string is suitable; the examples below use synthetic readable IDs only.

- `video_id` identifies the original source recording. One source video has
  one `video_id`, even when it contains multiple candidate movements.
- `movement_id` identifies one complete candidate badminton movement within a
  source video and therefore maps to exactly one `video_id`. A movement can
  contain several adjacent phase intervals.
- `sequence_id` identifies the pose-feature sequence extracted from a
  video/movement context. It maps to exactly one `video_id` and one movement
  context. It is the parent sequence referenced by one or more intervals and
  should remain stable when interval labels are revised. Whether one movement
  may legitimately reference multiple pose-feature sequences is not settled by
  the current protocol; this schema leaves that relationship unresolved rather
  than imposing a rule.
- `interval_id` identifies one annotated phase interval within a sequence and
  is globally unique and identifies exactly one interval. It is not a frame ID.

The parent relationships must still be consistent:
`movement_id` belongs to exactly one `video_id`; `sequence_id` belongs to
exactly one video/movement context; and `interval_id` belongs to exactly one
`sequence_id` and `movement_id`. Repeating the same `video_id`, `movement_id`,
or `sequence_id` across rows is valid when the rows refer to the same parent
entity. Global uniqueness means one ID cannot identify two different entities;
it does not prohibit repeated parent references.

## Canonical CSV

There is exactly one row per annotated interval. The canonical header is:

```csv
movement_id,interval_id,sequence_id,video_id,player_id,racket_side,start_frame,end_frame,movement_label,label_source,annotation_status,contact_candidate_status,contact_evidence,feature_csv_path,source_video_path,camera_view,annotator_id,uncertainty_reason,protocol_version,notes
```

### Field definitions

The protocol approves the phase labels and `unknown` as an abstention outcome.
Values described as **proposed** or **unresolved** below must not be treated as
final controlled vocabularies without project-owner approval.

| Field | Meaning | Type | Required | Values and constraints | Null/empty handling |
|---|---|---|---|---|---|
| `movement_id` | Complete candidate movement containing this interval. | String ID | Yes | Globally unique opaque ID. | Never empty. |
| `interval_id` | This contiguous labeled interval. | String ID | Yes | Globally unique opaque ID. | Never empty. |
| `sequence_id` | Pose-feature sequence parent for the interval. | String ID | Yes | Globally unique opaque ID; must resolve to the feature CSV context. | Never empty. |
| `video_id` | Original source recording identity. | String ID | Yes | Globally unique opaque ID; all intervals from it share one split. | Never empty. |
| `player_id` | Anonymous player grouping identifier. | String ID | Yes | Stable anonymous ID; no names or personal data. | Never empty for the pilot; use an explicit project-approved placeholder only if the protocol is later revised. |
| `racket_side` | Arm metadata used when temporal features were exported. | Enum | Yes | `left`, `right`, or `unknown`, matching `PoseSequence`. | Never empty. |
| `start_frame` | First frame in the interval. | Non-negative integer | Yes | Zero-based source-video frame index; `start_frame <= end_frame`. | Never empty. |
| `end_frame` | Last frame in the interval. | Non-negative integer | Yes | Zero-based source-video frame index; inclusive. | Never empty. |
| `movement_label` | Phase label for this interval or abstention outcome. | Enum | Yes | `preparation`, `backswing`, `forward_swing`, `follow_through`, `recovery`, or `unknown`. `contact` is excluded from the initial classifier target unless verified and approved. | Never empty; use `unknown` when abstaining, not an empty value. |
| `label_source` | Evidence/process used to assign the label. | Enum/string | Yes | Protocol-proposed values: `manual_video_review`, `manual_video_and_shuttle_review`, `consensus_review`. Final controlled list is unresolved. | Never empty for annotated rows. |
| `annotation_status` | Lifecycle state of this annotation. | Enum | Yes | Protocol-proposed values: `unreviewed`, `provisional`, `second_reviewed`, `adjudicated`, `frozen`, `rejected`. | Never empty. |
| `contact_candidate_status` | Separate marker for possible or reviewed contact; not a phase label. | Enum | Yes | Protocol-proposed values: `not_marked`, `candidate`, `verified_contact`, `not_contact`, `uncertain`. | Use `not_marked` when no contact event is being considered; do not leave empty. |
| `contact_evidence` | Evidence supporting the contact marker. | Enum/string | Conditional | Protocol-proposed values include `shuttle_visible`, `racket_shuttle_interaction_visible`, `video_review_only`, `not_observed`, `unclear`. Final controlled list is unresolved. Verified contact requires supporting video evidence. | Required when status is `candidate`, `verified_contact`, or `uncertain`; use `not_observed` for `not_marked`/`not_contact`. |
| `feature_csv_path` | Path to the exported temporal-feature CSV. | Relative path | Yes | Must resolve within the approved dataset storage root; should contain the interval's frame rows. | Never empty. |
| `source_video_path` | Path to the original video reviewed by annotators. | Relative path/approved URI | Yes | Must resolve within approved video storage; must correspond to `video_id`. | Never empty. |
| `camera_view` | Viewpoint metadata relevant to visibility and generalization. | Enum/string | Yes | Protocol-proposed examples: `side`, `front`, `rear`, `diagonal`, `unknown`. Final controlled list is unresolved. | Use `unknown` when not established, not empty. |
| `annotator_id` | Anonymous reviewer identity. | String ID | Yes | Stable anonymous reviewer ID. | Never empty for reviewed rows; `unassigned` is not approved unless the protocol is revised. |
| `uncertainty_reason` | Reason for `unknown` or uncertain boundaries/contact. | Enum/string | Conditional | Proposed list: `occlusion`, `low_pose_confidence`, `ambiguous_phase_boundary`, `unclear_movement`, `insufficient_video_context`, `reviewer_disagreement`, `other`. | Required for `unknown` or `contact_candidate_status=uncertain`; otherwise empty is allowed. |
| `protocol_version` | Rules used for annotation. | Version string | Yes | Must match the dataset's declared protocol version, e.g. `v0.1`. | Never empty. |
| `notes` | Review context, boundary rationale, or evidence details. | String | Optional | No personal sensitive data; free text. | Empty allowed. |

`review_status` is not included because the current protocol revision names
`annotation_status` as the canonical lifecycle field. A future schema version
must not add both fields for the same state without defining their separate
semantics.

Different intervals within one movement may have different
`annotation_status` values. For example, one interval may be `second_reviewed`
while an adjacent interval remains `provisional`; this does not make the
parent movement review-complete.

A movement is **review-complete** only when every intended interval for that
movement has been annotated, required boundary and uncertainty decisions have
been recorded, and the project's required second review/adjudication gate has
been met. A dataset is **review-complete** only when every included movement
has reached that state, all required artifact and split checks pass, and the
dataset version is frozen. The exact second-review subset, agreement
threshold, and freeze gate are unresolved and require approval before dataset
freeze.

## Interval rules

### Frame indexing and bounds

Frame indices are **zero-based**. This follows the current extractor's
`PoseFrame.frame_index` and the existing pose-sequence CSV, whose first
observation is frame `0`. The temporal exporter preserves those source frame
indices.

`start_frame` and `end_frame` are inclusive. Therefore:

- both values are non-negative integers;
- `start_frame <= end_frame`;
- both frame indices must exist in the referenced source sequence/video;
- the interval contains every represented source frame from start through end;
- no fixed duration is assumed.

### Ordering, gaps, and overlap

Intervals within one `movement_id` must be ordered by `start_frame` and must
not overlap. Adjacent intervals are allowed, including intervals that share a
movement but have different labels. Gaps are permitted: uncertain or
unreviewed frames must not be forced into a phase merely to make coverage
continuous.

An unannotated gap is not the same as `unknown`:

- An **unannotated gap** has no manifest row and means the interval has not
  been assigned an annotation under this dataset version.
- `unknown` is an explicit row covering an interval that was reviewed but
  could not be assigned a reliable phase.

Uncertain boundaries must be recorded with
`uncertainty_reason=ambiguous_phase_boundary` (or another applicable proposed
reason) and explained in `notes`. If a boundary cannot be placed reliably,
annotators may leave a gap or create an `unknown` interval; they must not
silently expand a neighboring label.

Overlapping intervals are invalid in this version, including overlaps between
different labels within the same movement. Overlap requires a future protocol
version that explicitly defines multilabel representation and evaluation.

## Contact handling

Contact is deliberately separate from ordinary movement phases:

- `contact_candidate_status=candidate` marks a possible contact event or an
  interval that needs contact review.
- `contact_candidate_status=verified_contact` marks contact supported by
  available video evidence. It is an event/status marker, not automatically a
  classifier phase.
- `contact_candidate_status=uncertain` records unresolved contact evidence and
  requires `uncertainty_reason`.
- `movement_label` remains a phase label. `contact` must not be used as an
  ordinary phase in the initial classifier target.

Verified contact requires manual video evidence sufficient for the reviewer to
support actual shuttle contact, preferably visible racket/shuttle interaction
or another explicitly documented visual basis. `video_review_only` is a
description of the review source, not proof that contact occurred; it requires
specific supporting observations in `notes` or the approved evidence
representation. The current protocol does not define a complete evidence
rubric, minimum visibility standard, or adjudication threshold; these are
unresolved and require project-owner approval.

No contact status may be inferred solely from an elbow-angle peak, wrist
displacement/velocity, landmark confidence, 2D/3D disagreement, or any other
temporal pose feature. `contact_evidence` must record the available basis.

Structural validation can check that `verified_contact` has non-empty evidence
and an appropriate manual-review `label_source`; it cannot determine whether
the evidence semantically proves shuttle contact. Human semantic review and
the future evidence rubric must make that determination.

## Validation requirements

This section specifies validation behavior; it does not implement a validator.

### Required fields and missing values

Reject rows missing any required field or containing whitespace-only required
values. Empty `notes` is allowed. Conditional fields follow the rules above.
Do not silently convert missing required values to `unknown`, zero, or a
fabricated identifier.

### Identifier consistency

Reject duplicate globally unique IDs for any of `video_id`, `movement_id`,
`sequence_id`, or `interval_id` when they identify different records. Repeated
references are allowed only when they refer to the same parent entity:
multiple movements may share a video, and multiple intervals may share a
movement/sequence. Validate that each movement maps to one video and each
interval maps to one movement and sequence.

### Frames and ordering

Reject non-integer, negative, missing, or out-of-range frame values; reject
`start_frame > end_frame`; reject intervals not ordered within a movement; and
reject overlaps within a movement. A gap is valid and should remain a gap.

### Labels and annotation status

Reject labels outside the approved phase taxonomy plus `unknown`. Treat
`contact` as invalid for the initial classifier manifest unless the project
owner approves verified contact inclusion and a protocol version explicitly
adds it. Reject missing or unapproved `annotation_status` values. A frozen
row must have completed review evidence; the exact review gate is proposed and
must be finalized before dataset freeze.

### Contact consistency

Structurally reject `verified_contact` without non-empty supporting
`contact_evidence` and an appropriate manual review source. Do not treat
`video_review_only` or any other vague source description as automatic proof
of actual contact. Reject `uncertain` without `uncertainty_reason`. Reject a
contact evidence value that claims verification while the status is
`not_marked` or `not_contact`. A `candidate` status does not make
`movement_label=contact` valid. Human semantic review must separately confirm
that the evidence meets the unresolved contact rubric.

### Paths and protocol version

Resolve `feature_csv_path` and `source_video_path` against the approved dataset
root, not the current working directory. Reject missing or inaccessible
artifacts, mismatched `video_id` references, and feature CSVs that do not
contain the inclusive interval frame range. All rows in one manifest must use
one declared `protocol_version`; changes create a new dataset version rather
than silently reinterpreting old rows.

The current exporter writes feature CSVs from a video-level sequence and does
not emit manifest identifiers, movement intervals, or contact metadata. The
manifest therefore supplies those annotations externally. The exporter
currently accepts a frame range and writes the selected rows, but it does not
itself validate that a source video path and feature CSV are semantically
matched; that check belongs to manifest validation.

### Split leakage

Reject any split assignment in which:

- intervals from one `video_id` occur in more than one split;
- intervals from one `movement_id` occur in more than one split;
- player-grouped evaluation is enabled and one `player_id` occurs in more than
  one split;
- a random frame-level split is used.

Split assignments must be versioned and reproducible, recording the grouping
keys and assignment procedure/seed. The exact split percentages remain
unresolved until the pilot's number of videos and independent players is known.

## Synthetic examples

These examples are synthetic and do not refer to real players or videos.
They illustrate schema shape only.

### Valid rows

```csv
movement_id,interval_id,sequence_id,video_id,player_id,racket_side,start_frame,end_frame,movement_label,label_source,annotation_status,contact_candidate_status,contact_evidence,feature_csv_path,source_video_path,camera_view,annotator_id,uncertainty_reason,protocol_version,notes
movement_demo_001,interval_demo_001,sequence_demo_001,video_demo_001,player_demo_001,right,12,24,preparation,manual_video_review,second_reviewed,not_marked,not_observed,features/video_demo_001.csv,videos/video_demo_001.mp4,diagonal,reviewer_demo_01,,v0.1,Preparatory interval before loading.
movement_demo_001,interval_demo_002,sequence_demo_001,video_demo_001,player_demo_001,right,25,41,backswing,manual_video_review,provisional,candidate,unclear,features/video_demo_001.csv,videos/video_demo_001.mp4,diagonal,reviewer_demo_01,,v0.1,Possible contact is marked separately for later review.
```

The rows are valid because their intervals are inclusive, ordered, adjacent,
non-overlapping, and share consistent parent identifiers. The repeated
`movement_id`, `sequence_id`, and `video_id` are valid parent references, and
the contact candidate does not change the `backswing` phase label.

### Invalid rows

```csv
# Invalid 1: start_frame is greater than end_frame.
movement_demo_002,interval_demo_003,sequence_demo_002,video_demo_002,player_demo_002,left,50,45,forward_swing,manual_video_review,provisional,not_marked,not_observed,features/video_demo_002.csv,videos/video_demo_002.mp4,side,reviewer_demo_02,,v0.1,Reversed bounds.

# Invalid 2: overlaps another interval in movement_demo_001 (25-41).
movement_demo_001,interval_demo_004,sequence_demo_001,video_demo_001,player_demo_001,right,40,52,follow_through,manual_video_review,provisional,not_marked,not_observed,features/video_demo_001.csv,videos/video_demo_001.mp4,diagonal,reviewer_demo_01,,v0.1,Overlaps interval_demo_002.

# Invalid 3: contact is asserted from a pose-only candidate without approved evidence.
movement_demo_003,interval_demo_005,sequence_demo_003,video_demo_003,player_demo_003,right,60,60,contact,manual_video_review,provisional,candidate,elbow_angle_peak,features/video_demo_003.csv,videos/video_demo_003.mp4,front,reviewer_demo_03,,v0.1,Pose peak only.
```

Invalid 1 violates `start_frame <= end_frame`. Invalid 2 violates the
no-overlap rule within a movement. Invalid 3 uses `contact` as an ordinary
initial phase and cites pose-only evidence; a candidate should instead retain a
normal phase label or `unknown`, with `contact_candidate_status=candidate` and
video-review evidence still pending.

## Unresolved decisions

The protocol leaves these decisions open and this schema does not silently
resolve them:

- The final controlled vocabularies for `label_source`, `camera_view`,
  `contact_evidence`, and `annotation_status` review gates.
- The minimum visual evidence and adjudication rule for verified contact.
- Whether a future approved version will include `contact` as a classifier
  target.
- The approved dataset storage root and whether paths may be URIs.
- The exact pilot coverage threshold for retaining low-quality intervals.
- The split percentages and the minimum number of independent players needed
  for player-grouped evaluation.
