# Implementation decisions to confirm

Where the brief left room or a literal reading was not buildable, these choices were made. Each
one is easy to change. Please confirm or correct (brief, principle 8).

| # | Topic | Brief | Implemented | Why |
|---|---|---|---|---|
| 1 | Order of anisotropy rotation | step 9, after periodisation | rotation of the raw raster **before** crop + periodisation | rotating a periodic field by an arbitrary angle breaks periodicity |
| 2 | Combining functional + texture layer | "addieren" | channels are **carved**: `min(texture, channel)`; channel floor at a guaranteed depth below the reference plane | guaranteed channel dimensions; total relief stays within 20 mm |
| 3 | Total relief | macro ≤ 20, meso ≤ 5 | texture (macro + meso) scaled down if it exceeds 20 mm | 20 mm upper bound for stamping (brief 3.3) |
| 4 | Auto rotation | always | skipped when anisotropy index < 0.15 | direction of near-isotropic textures is noise |
| 5 | Meso band | residual of the macro low-pass | additionally low-passed at 1 mm | FDM cannot print finer; triangulation noise would be amplified by normalisation |
| 6 | Draft check | morphological opening with a cone | grey erosion with a cone (largest surface ≤ relief with flank ≤ 85°) | only removes tile material, never deepens; pits become funnels |
| 7 | Anchor-hole pitch | ca. 20 mm | 21.2 mm (lattice q = 30 mm along x−y) | lattice must stay periodic in 150 mm |
| 8 | Registration | flange 4-5 mm + pins | 5 mm flange, 3 mm plinth (lateral index of the frame), 4 pins Ø 2.4 at the flange corners | plinth gives lateral registration without thin pin walls |
| 9 | Fit clearance 0.3 mm | "Passungsspiel" | 0.3 mm **per side** | common FDM practice |
| 10 | Collecting groove position | not specified | centre 10 mm behind the reference plane, no inward tilt yet | placeholder in `constants.py` |
| 11 | Design ID | `BT-D-` + 6 chars as PK | UUID as primary key, `code` (BT-D-…) assigned at first export | the ID depends on the height field, which only exists after export |
| 12 | Framed edge | 10 mm band, run-out over last 5 mm | outer 5 mm flat, relief ramps in over the inner 5 mm | interpretation of "Auslauf auf null" |
| 13 | Library samples in mock mode | – | library entries map to synthetic GLB stand-ins; `source_type = procedural` | honest labelling until real photos are recorded |
| 14 | Keyhole | head Ø 10, slot 5.5 × 10, pocket 6 mm | cookie-cutter for the keyhole outline, 6 mm deep | an undercut pocket cannot be cut by a straight cutter; check with a clay test |
| 15 | Smr | Smr | Smr(c = 1 mm below the top) | surfalize needs a height `c` |
| 16 | Observation moderation | pending → approved | auto-approved in the MVP | moderation is v1 |
| 17 | EXIF | – | stripped on every upload (photos re-encoded) | privacy: GPS in photos |
| 18 | Moss starter | diagonal channels | **moss nests** (default) in the natural hollows + rills along the valleys; diagonal channels in "More settings" | decision 2026-10-03 |
| 19 | Hanging | keyhole | **slanted holes** (Ø 8, 40° up, 18 mm) from the back, guided by the back plate; pins on the adapter | decision 2026-10-03 (option a) |
| 20 | Code | ID on the back | **pattern code on the front** (BT-XXXXXX, 1 mm deep, on a small flattened field); tile numbers -001… via registration | decision 2026-10-03; one mould = one code |
| 21 | Seams | continuous | also smooth: fine band cross-faded with the half-shifted copy near the edges (no crease) | visible line in raking light |
| 22 | Hexagon | – | Barcelona mode: hex lattice (flat-to-flat = size), frame in two halves; 150 mm needs a 256 mm bed | decision 2026-10-03 |
| 23 | Positions | coarse only | optional exact position; public: rounded ~100 m (or exact by choice, never for schools) | decision 2026-10-03 |
| 24 | Registration | – | invite codes only (HMAC-stored, single/multi use, expiry) | decision 2026-10-03 |
| 25 | Printer choice | A1 mini / P1S | removed from the UI; check: "fits 180 mm" (pass) / "needs 256 mm" (warn) | decision 2026-10-03 |

## Verified against the Tripo docs (2026-10-03)

* `POST /v3/files`: multipart field `file`, response `data.file_token`, JPEG/PNG ≤ 20 MB.
* `GET /v3/tasks/{id}`: `status`, `progress`, `output.model_url`, `output.rendered_image_url`,
  `credits_consumed`, `error_code`, `error_message`.
* The image-to-model page did not render for the doc fetcher: the request body is taken verbatim
  from brief 7.3. **Check on the first live run.** WebP support of `/v3/files` is unconfirmed, so WebP
  uploads are converted to PNG server side.
* Text-to-image v3 uses different parameters than the old H3 docs (`model: seedream_v4 …`, `size`,
  `output_format`). This is relevant for the text mode (v1).
