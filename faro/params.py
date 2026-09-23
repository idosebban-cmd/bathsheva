"""
Faro lighthouse table lamp: every dimension lives here (mm unless noted).

Proportions are measured from the concept's straight front view
(faro/reference/fit_concept.py) at OVERALL_HEIGHT = 300 mm. Heights are given
as absolute z values at 300 mm and scaled with OVERALL_HEIGHT; the small
physical details (walls, knob, railing posts, USB-C) don't scale.

Coordinate system (as for Atelier): Z up, ground at 0, front faces -Y.
"""

# ---------------------------------------------------------------------------
# Overall
# ---------------------------------------------------------------------------
OVERALL_HEIGHT = 300.0       # ground to the top of the finial ball
REF_HEIGHT = 300.0           # the height the z values below were measured at

# ---------------------------------------------------------------------------
# 1. Walnut base
# ---------------------------------------------------------------------------
BASE_DIA = 113.0
BASE_H = 28.0
BASE_TOP_ROUND = 2.5         # rounding on the top edge
BASE_BOTTOM_ROUND = 1.5
BASE_WALL = 4.0              # hollow base: side wall / top thickness
BASE_FLOOR = 3.0             # bottom plate (felt pad goes under it)
NAMEPLATE_W = 37.0
NAMEPLATE_H = 11.5
NAMEPLATE_Z = 14.0           # centre height on the base front
NAMEPLATE_THICK = 1.2        # brass plate, sits in a recess and stands 0.6 proud
NAMEPLATE_RECESS = 0.6
NAMEPLATE_TEXT = "FARO"
NAMEPLATE_TEXT_H = 5.5       # letter height
NAMEPLATE_TEXT_RAISE = 0.4

# ---------------------------------------------------------------------------
# 2. Cream band + red band
# ---------------------------------------------------------------------------
CREAM_BAND_DIA = 97.0
CREAM_BAND_H = 6.0
CREAM_BAND_ROUND = 1.0
RED_BAND_TOP_Z = 69.0        # the red band is the lower part of the tower cone
KNOB_DIA = 20.0
KNOB_PROUD = 6.0             # how far the knob stands off the band
KNOB_Z = 52.0

# ---------------------------------------------------------------------------
# 3. Tower (one straight cone, from the cream band to the gallery; the red band
#    is its lower part)
# ---------------------------------------------------------------------------
TOWER_BOTTOM_DIA = 92.0      # at the top of the cream band
TOWER_TOP_DIA = 65.0
TOWER_TOP_Z = 197.0
SHELL_WALL = 2.5
WINDOW_W = 11.7
WINDOW_H = 21.0              # overall, including the round top
WINDOW_Z = (113.0, 165.0)    # window centres (two on the front, as in the concept)
DIFFUSER_THICK = 1.0         # frosted insert behind each window
DIFFUSER_MARGIN = 2.0        # how far it overlaps the window edge

# ---------------------------------------------------------------------------
# 4. Brass gallery
# ---------------------------------------------------------------------------
GALLERY_DIA = 90.0
GALLERY_THICK = 9.7          # platform ring height
GALLERY_ROUND = 1.0
RAIL_DIA = 88.0              # railing circle (post centres)
RAIL_H = 14.0
RAIL_POSTS = 16
RAIL_POST_DIA = 1.6          # >= 1.0 for resin, >= 1.5 for FDM
RAIL_BAR_DIA = 1.6           # top rail and mid rail
RAIL_MID_FRAC = 0.5          # mid rail height (fraction of RAIL_H)

# ---------------------------------------------------------------------------
# 5. Lantern
# ---------------------------------------------------------------------------
LANTERN_DIA = 55.0
LANTERN_TOP_Z = 248.0        # the lantern runs from the gallery top to here
MULLIONS = 8                 # a panel faces straight to the front
MULLION_W = 2.2
MULLION_DEPTH = 2.2
LANTERN_RING_H = 2.5         # brass rings at the lantern's top and bottom
GLASS_THICK = 1.2            # frosted panel ring, just inside the mullions

# ---------------------------------------------------------------------------
# 6. Cap and finial
# ---------------------------------------------------------------------------
CAP_RIM_DIA = 71.0
CAP_RIM_H = 6.0
CAP_DOME_DIA = 58.5
CAP_TOP_Z = 281.0            # top of the dome
CAP_BOSS_DIA = 14.0          # small flared red collar on top of the dome (bottom dia)
CAP_BOSS_H = 4.5
FINIAL_DIA = 14.0

# ---------------------------------------------------------------------------
# Power (placeholders; cordless, rechargeable)
# ---------------------------------------------------------------------------
USBC_W = 8.94 + 2 * 0.35     # receptacle opening + clearance
USBC_H = 3.26 + 2 * 0.35
USBC_Z = 11.0                # low on the rear (+Y) of the walnut base
BATTERY_SIZE = (65.0, 37.0, 19.0)   # 2 x 18650 pack, lying flat in the base
LED_DIA = 20.0               # LED module placeholder in the lantern
LED_H = 12.0

# ---------------------------------------------------------------------------
# Colours and finishes (renders)
# ---------------------------------------------------------------------------
RED_HEX = "#8A1C15"          # same as Atelier
BRASS_HEX = "#C4A15A"        # same as Atelier
CREAM_HEX = "#F4ECDC"        # warm cream lacquer
WALNUT_HEX = "#4A2F20"       # dark walnut
GLOW_HEX = "#FFD7A0"         # lit frosted panels
LACQUER_ROUGHNESS = 0.12
LACQUER_CLEARCOAT = 0.9
BRASS_ROUGHNESS = 0.35
WALNUT_ROUGHNESS = 0.55
RENDER_SIZE = (1200, 1600)
