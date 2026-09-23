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
BASE_H = 27.0                 # slimmer than the first read (the concept's includes a sliver of the top face)
BASE_TOP_ROUND = 6.0         # generous rounding on the top edge, as in the concept
BASE_BOTTOM_ROUND = 1.5
BASE_WALL = 4.0              # hollow base: side wall
BASE_TOP_WALL = 3.5          # top of the battery bay (keeps >= 2.8 mm of walnut under the rounded edge)
BASE_WIRE_HOLE = 20.0        # hole through the base top for the wiring up the tower
# User-replaceable battery: the walnut base is an open ring; a bottom plate sits
# flush in a rebate and screws into 4 bosses inside the base. A felt pad covers
# the screws: felt laminated to a thin steel disc, held by 4 magnets in the plate,
# so it lifts off and goes back as often as needed.
PLATE_THICK = 3.0
PLATE_REBATE = 2.0           # walnut skin left outside the plate's rebate
PLATE_CLEAR = 0.2
SCREWS = 4                   # M3 countersunk (M3 brass threaded inserts in the walnut bosses)
SCREW_R = 40.0               # screw circle radius
SCREW_ANGLE0 = 45.0          # first screw angle (clears the battery)
SCREW_CLEAR_DIA = 3.4
SCREW_HEAD_DIA = 6.4
BOSS_DIA = 8.0
BOSS_PILOT_DIA = 4.0         # for an M3 heat-set/threaded insert
MAGNETS = 4                  # between the screws
MAGNET_DIA = 6.0
MAGNET_THICK = 1.5
FELT_THICK = 1.5             # felt + 0.4 mm steel backing
FELT_RECESS = 1.0            # recess in the plate's underside; the felt stands proud by the rest
FELT_INSET = 3.0             # felt edge inside the plate edge
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
LANTERN_RING_H = 2.5         # brass ring at the lantern's bottom
# Removable cap (bayonet / twist-lock). The lantern's top band has an inner lip
# with slots; lugs on a spigot under the cap drop through, then turn under the
# lip until they hit a stop. Take the cap off to reach the LED module.
TOP_BAND_H = 6.0             # brass band at the lantern's top (holds the bayonet)
LIP_H = 2.5                  # the lip the lugs lock under
GROOVE_R = 26.3              # lug channel radius under the lip
LOCK_LUGS = 4                # multiple of the mullion spacing, so slots sit mid-panel
LOCK_LUG_W = 6.0
LOCK_LUG_H = 2.6
LOCK_TURN_DEG = -20.0        # turn to lock; negative = clockwise seen from above
SPIGOT_WALL = 1.5
FIT_CLEAR = 0.2
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
CREAM_HEX = "#F9F2E1"        # warm cream lacquer (matched to the concept's lit tower)
WALNUT_HEX = "#4A2F20"       # dark walnut
GLOW_HEX = "#FFD7A0"         # lit frosted panels
LACQUER_ROUGHNESS = 0.12
LACQUER_CLEARCOAT = 0.9
BRASS_ROUGHNESS = 0.35
WALNUT_ROUGHNESS = 0.55
LIGHT_GAIN = 1.27            # Faro's studio is a touch brighter than Atelier's
RENDER_SIZE = (1200, 1600)
