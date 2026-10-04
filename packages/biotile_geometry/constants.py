"""Central physical and scientific constants for BIOTILE.

Every literature value carries a short citation (see docs/PROJECT_BRIEF.de.md, section 19).
All lengths are in millimetres unless the name says otherwise. Values marked
"placeholder" are engineering starting points that must be validated in the workshop.

Coordinate convention used throughout the package (tile in installed position):
    x  -> right, y -> up (towards the top edge), z -> out of the wall (front).
    The *reference plane* (z = 0) is the highest relief point / rim; recesses are negative.
"""

from __future__ import annotations

# --------------------------------------------------------------------------------------
# Versioning
# --------------------------------------------------------------------------------------
# Bump on ANY change that alters generated geometry. Stored on every design.
PIPELINE_VERSION = "0.3.0"  # 0.2: seam healing · 0.3: lattices (hex), moss nests, front code
# Mounting interface (hanging points, rim). Bump only if tiles stop being interchangeable.
INTERFACE_VERSION = "1"

# --------------------------------------------------------------------------------------
# Tile module (brief 5.1)
# --------------------------------------------------------------------------------------
TILE_SIZE_MM = 150.0  # finished size of the 1x1 module
TILE_THICKNESS_MM = 40.0  # back face to reference plane
TILE_FORMATS = {"1x1": (1, 1), "2x1": (2, 1), "2x2": (2, 2)}
# Selectable sizes (square: side, hex: flat-to-flat). 150 is the standard for comparable data;
# other sizes are not normed for the trial wall.
TILE_SIZES_MM = (100.0, 120.0, 150.0, 180.0)
TILE_SHAPES = ("square", "hex")  # hex = "Barcelona mode" (after Gaudí's paving tile)
DEFAULT_TEXTURE_PERIOD_MM = 150.0  # brief 5.10: later wrappable around posts (U/n)

# --------------------------------------------------------------------------------------
# Relief depths (brief 5.6)
# --------------------------------------------------------------------------------------
# Mustafa et al. 2021, sec. 4.2: macro depth max 20 mm at H/W 0.2-0.3 (broad, shallow hollows).
MACRO_DEPTH_MAX_MM = 20.0
MACRO_DEPTH_DEFAULT_MM = 15.0
MACRO_HW_RATIO_RANGE = (0.2, 0.3)
# Mustafa et al. 2021, sec. 4.2: micro grooves 5 mm deep -> our "meso" band.
MESO_DEPTH_MAX_MM = 5.0
MESO_DEPTH_DEFAULT_MM = 4.0
# Micro band from PBR normal map (v1, not in MVP).
MICRO_DEPTH_MAX_MM = 1.0
MICRO_DEPTH_DEFAULT_MM = 0.6
# Total relief must stay within the stamp-able range (brief 3.3: 10-20 mm upper bound).
TOTAL_RELIEF_MAX_MM = MACRO_DEPTH_MAX_MM

# Band separation: Gaussian low-pass cut-off between macro and meso (engineering choice;
# macro hollows are 65-100 mm wide, meso grooves a few mm).
MACRO_MESO_CUTOFF_MM = 12.0
# Short-wave limit of the meso band: FDM (0.4 mm nozzle, 0.2 mm export grid) cannot print
# finer, and mesh-triangulation noise would otherwise be amplified by the depth normalisation.
# Finer detail is the micro band's job (normal map, v1).
MESO_MIN_WAVELENGTH_MM = 1.0

# --------------------------------------------------------------------------------------
# Functional layer (brief 5.5.1)
# --------------------------------------------------------------------------------------
# Booster channels: Jakubovskis 2025, sec. 3/4 - continuous diagonal booster shapes
# distributed water best. Values are starting points from the brief.
BOOSTER_CHANNEL_DEPTH_RANGE_MM = (10.0, 15.0)
BOOSTER_CHANNEL_DEPTH_DEFAULT_MM = 12.0
BOOSTER_CHANNEL_WIDTH_RANGE_MM = (12.0, 20.0)
BOOSTER_CHANNEL_WIDTH_DEFAULT_MM = 16.0
# Channel spacing must divide the tile size, otherwise the pattern does not tile.
CHANNEL_SPACINGS_MM = (75.0, 50.0, 37.5)
CHANNEL_SPACING_DEFAULT_MM = 75.0
# Anchor holes in the channel floor replace an undercut dovetail (rigid stamp cannot demould
# it); paper-pulp fibres interlock in them.
ANCHOR_HOLE_DIAMETER_MM = 3.5  # brief: 3-4 mm
ANCHOR_HOLE_DEPTH_MM = 9.0  # brief: 8-10 mm
ANCHOR_HOLE_PITCH_MM = 20.0
# Moss nests (default functional layer, see functional.py). Pockets with a steep lower flank
# (a shelf that holds moss on a vertical tile) and a gentle upper flank where water runs in.
NEST_WIDTH_DEFAULT_MM = 24.0
NEST_WIDTH_RANGE_MM = (16.0, 36.0)
NEST_DEPTH_DEFAULT_MM = 14.0
NEST_DEPTH_RANGE_MM = (8.0, 18.0)
NEST_SPACING_DEFAULT_MM = 34.0
NEST_SPACING_RANGE_MM = (28.0, 70.0)
NEST_UP_FACTOR = 0.75  # upper half-height relative to the width
NEST_DOWN_FACTOR = 0.3  # lower half-height: short = steep shelf
RILL_DEPTH_MM = 3.5  # cut relative to the surface
RILL_WIDTH_MM = 5.0

# Tile code embossed on the front (one code per mould: BT-XXXXXX)
FRONT_CODE_HEIGHT_MM = 5.0
FRONT_CODE_DEPTH_MM = 1.0
FRONT_CODE_MARGIN_MM = 6.0  # from the bottom / right edge

# Optional origin glyph (front corner).
ORIGIN_GLYPH_SIZE_MM = 8.0

# --------------------------------------------------------------------------------------
# Edges (brief 5.5.2, 5.5.3) - formed by ribs on the casting-frame walls
# --------------------------------------------------------------------------------------
EDGE_CHAMFER_MM = 2.0  # periodic mode
FRAMED_BAND_MM = 10.0  # framed mode
FRAMED_RUNOUT_MM = 5.0  # relief fades to zero over the outer 5 mm of the band

# Top: collecting groove (Jakubovskis 2025: upper area receives water from above).
COLLECTING_GROOVE_WIDTH_MM = 8.0  # measured in z (through the thickness)
COLLECTING_GROOVE_DEPTH_MM = 6.0  # measured into the tile (-y)
COLLECTING_GROOVE_CENTER_BEHIND_FRONT_MM = 10.0  # placeholder; brief gives no position
# Bottom: drip groove so water does not creep to the back.
DRIP_GROOVE_SIZE_MM = 4.0  # 4 x 4 mm
DRIP_GROOVE_BEHIND_FRONT_MM = 6.0  # front edge of the groove behind the reference plane
# Sides: vertical half channels, diameter 8 mm, 12 mm behind front (v1 default "edge_half").
HALF_CHANNEL_DIAMETER_MM = 8.0
HALF_CHANNEL_CENTER_BEHIND_FRONT_MM = 12.0
# Joint: 4 mm nominal (cascade wall, v2) / >= 20 mm (trial wall).
JOINT_CASCADE_MM = 4.0

# Cascade-wall preparation (brief 4.6): fixed relative to the hanging points so v2 needs
# no new tile geometry. Drip groove sits above the collecting groove of the tile below.
CASCADE_GRID_HORIZONTAL_MM = TILE_SIZE_MM + JOINT_CASCADE_MM  # 154 mm

# --------------------------------------------------------------------------------------
# Trial wall (brief 4.5)
# --------------------------------------------------------------------------------------
TRIAL_WALL_GAP_VERTICAL_MIN_MM = 50.0  # drip water of the upper tile must not hit the lower
TRIAL_WALL_GAP_HORIZONTAL_MIN_MM = 20.0  # no shared gutter between neighbouring half channels
TRIAL_WALL_GRID_MM = (170.0, 200.0)  # drill template raster (h x v)

# --------------------------------------------------------------------------------------
# Back side (brief 5.5.4) and mounting interface (brief 5.7)
# --------------------------------------------------------------------------------------
RIM_WIDTH_MM = 10.0
CLAY_SHELL_THICKNESS_RANGE_MM = (12.0, 15.0)
HANGING_POINT_COUNT = 2
HANGING_POINT_SPACING_MM = 100.0  # axis distance
HANGING_POINT_BELOW_TOP_MM = 30.0
HANGING_PAD_DIAMETER_MIN_MM = 30.0
# Hanging (decision 2026-10-03, option a): two slanted blind holes from the back, angled
# upwards into the tile; the tile hangs on two stainless pins of the wall adapter.
HANG_HOLE_DIAMETER_MM = 8.0
HANG_HOLE_ANGLE_DEG = 40.0  # between hole axis and tile normal, pointing up
HANG_HOLE_DEPTH_MM = 18.0  # along the axis
HANG_PIN_DIAMETER_MM = 6.0
HANG_PAD_DIAMETER_MM = 34.0  # flat, solid pad around each hole (pressed flat by the back plate)
HEX_HANGING_POINT_SPACING_MM = 80.0  # pads must stay inside the hexagon
# Clay keyhole (superseded by the slanted holes; kept for reference).
KEYHOLE_HEAD_DIAMETER_MM = 10.0
KEYHOLE_SLOT_WIDTH_MM = 5.5
KEYHOLE_SLOT_LENGTH_MM = 10.0  # upwards from the head centre
KEYHOLE_POCKET_DEPTH_MM = 6.0
# Concrete: cast-in stainless threaded sleeves M6 (v1).
THREADED_SLEEVE = "M6"

# ID on the back (brief 5.5.6)
ID_CHAR_HEIGHT_MM = 10.0
ID_CHAR_DEPTH_MM = 1.5

# --------------------------------------------------------------------------------------
# Manufacturing rules (brief 5.6)
# --------------------------------------------------------------------------------------
MIN_MATERIAL_THICKNESS_MM = {"clay": 12.0, "concrete": 15.0, "lime": 15.0, "loam": 12.0}
# Rigid stamps need >= 3-5 deg draft -> max flank angle 85 deg; silicone up to 90 deg.
MAX_FLANK_ANGLE_DEG = {"pla": 85.0, "petg": 85.0, "rpetg": 85.0, "tpu": 88.0, "resin": 85.0,
                       "silicone": 90.0}
VENT_HOLE_DIAMETER_MM = (1.0, 1.5)  # stamp_down only
REGISTRATION_FLANGE_MM = 5.0  # brief: 4-5 mm, not more (build volume with clay shrinkage)
FIT_CLEARANCE_MM = 0.3  # frame / matrix, per side
MATRIX_BASE_MM = 3.0  # flange plate thickness below the plinth (engineering choice)
MATRIX_PLINTH_MM = 3.0  # raised plinth indexes the frame laterally (engineering choice)
REGISTRATION_PIN_DIAMETER_MM = 2.4
REGISTRATION_PIN_HEIGHT_MM = 3.0
FRAME_WALL_THICKNESS_MM = 8.0  # sits on the flange, overhangs outwards
FRAME_TENON_MM = (6.0, 3.0)  # width x depth of the corner tenons
BACKPLATE_THICKNESS_MM = 4.0

# Clay shrinkage wet -> fired: roughly 8-12 % depending on the body. 10 % is a placeholder,
# measure on a test bar (see docs/guides). Tools are enlarged by s = 1 / (1 - shrink).
CLAY_SHRINK_DEFAULT_PCT = 10.0
CLAY_SHRINK_RANGE_PCT = (8.0, 12.0)

# --------------------------------------------------------------------------------------
# Printers (brief 5.1) - build volumes x, y, z
# --------------------------------------------------------------------------------------
PRINTER_PROFILES = {
    "bambu_a1_mini": {"label": "Bambu Lab A1 mini", "volume_mm": (180.0, 180.0, 180.0)},
    "bambu_p1s": {"label": "Bambu Lab P1S", "volume_mm": (256.0, 256.0, 256.0)},
}
DEFAULT_PRINTER = "bambu_a1_mini"

# --------------------------------------------------------------------------------------
# Pipeline resolution (brief 8.2)
# --------------------------------------------------------------------------------------
INTERNAL_RASTER_PX = 2048  # ~0.07 mm/px over the tile
EXPORT_GRID_MM = 0.2  # FDM 0.4 mm nozzle cannot resolve finer
EXPORT_MAX_TRIANGLES = 500_000
RASTER_CROP_FRACTION = 0.7  # central part of the generated sample, avoids mesh borders
DETREND_POLY_ORDER = 2
# Below this anisotropy index the main direction is noise: no automatic rotation.
ANISOTROPY_MIN_FOR_ROTATION = 0.15

# Metrics: scale-separated evaluation (brief 8.5)
METRIC_CUTOFFS_MM = (1.0, 5.0, 10.0, 20.0)
# Working hypotheses for crevice classes (brief 3.2 item 4; only the middle class is
# roughly supported by the Loxosceles refugia study).
CREVICE_CLASSES_MM = {"micro_1_3": (1.0, 3.0), "meso_5_8": (5.0, 8.0), "macro_15_20": (15.0, 20.0)}

# --------------------------------------------------------------------------------------
# Materials (brief 5.9) and processes (brief 5.3)
# --------------------------------------------------------------------------------------
MATERIALS = ("clay", "concrete", "lime", "loam")
PROCESSES = ("press_mould", "matrix_down", "stamp_down")
TOOL_MATERIALS = tuple(MAX_FLANK_ANGLE_DEG)
# Mustafa et al. 2021, Table 1 (bioreceptive concrete mix per m3).
CONCRETE_MIX_MUSTAFA_2021 = {
    "cement": "CEM III/B 32.5 N (75 % GGBS)", "cement_kg": 300, "sand_0_4_kg": 740,
    "gravel_5_8_kg": 1142, "water_kg": 180, "w_c": 0.6, "curing": "none",
}
# Booster (Jakubovskis 2025): waste-paper pulp + local soil crust, crust share >= 50 %.
BOOSTER_MIN_CRUST_FRACTION = 0.5
