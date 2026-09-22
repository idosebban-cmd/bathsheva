"""
ATELIER rocket speaker: every design parameter lives in this file.

Change a value, then run `python build.py` to regenerate the CAD, STLs,
renders and report in ./output.

Conventions
-----------
* Units are millimetres, degrees, grams and g/cm^3.
* Z is up, the ground is at Z = 0 and the rocket's axis is the Z axis.
* The FRONT of the product (grille, knob) faces -Y. Angles around the axis
  are measured from the front, positive towards +X (clockwise seen from above).
* Values named *_FRAC are ratios, so the design scales when you change the
  two master dimensions. Values without _FRAC are real physical sizes
  (wall thickness, knob size, USB-C port...) that should NOT scale.
"""

# ---------------------------------------------------------------------------
# 1. Master dimensions: change these two and everything else follows
# ---------------------------------------------------------------------------
OVERALL_HEIGHT = 280.0   # ground to nose tip
BODY_MAX_DIA = 95.0      # widest point of the red body

# ---------------------------------------------------------------------------
# 2. Vertical budget
#    OVERALL_HEIGHT = base clearance + body height + nose cone height
# ---------------------------------------------------------------------------
BASE_CLEARANCE_FRAC = 0.065  # ground to the underside of the red body, as a fraction of OVERALL_HEIGHT
CONE_HEIGHT_FRAC = 0.22      # nose cone height as a fraction of BODY height (the brief asked for 20-25%)

# ---------------------------------------------------------------------------
# 3. Body (red lacquer shell). Its side profile is a smooth spline that is
#    spun around the Z axis. Fractions below are of body height (vertical)
#    or BODY_MAX_DIA (horizontal).
# ---------------------------------------------------------------------------
BODY_MAX_AT_FRAC = 0.45     # height of the widest point (0 = bottom, 1 = top of body)
BODY_TOP_DIA_FRAC = 0.62     # diameter at the nose-cone joint
BODY_BOTTOM_DIA_FRAC = 0.55  # diameter where the body meets the gold base collar
BODY_TOP_FULLNESS = 2.7      # shape of the upper body. 2 = smooth egg taper; higher = straighter,
                             # more cylindrical sides that turn in late. The nose cone
                             # continues the slope at the joint, so the joint stays smooth.
BODY_BOTTOM_FULLNESS = 2.4   # same for the lower body (higher = rounder "belly" that tucks in late)
WALL = 2.5                   # shell wall thickness

# ---------------------------------------------------------------------------
# 4. Split lines: how the body comes apart so the electronics can go in
#    "nose"          - the nose cone is the only removable lid; the body bottom is closed.
#                      No seam on the red, but everything loads through the top.
#    "nose_tail"     - (recommended) the nose cone AND the gold base collar are removable.
#                      Both seams sit on existing gold/red colour breaks. The battery
#                      loads from below, the knob/LED board from the top, and the
#                      driver from the front under the grille.
#    "fin_clamshell" - the body splits vertically into a front shell (the 120 deg between
#                      the two front fins) and a rear shell. Easiest to assemble, but
#                      the seam shows on the red above the fins. Early prototypes only.
# ---------------------------------------------------------------------------
SPLIT_MODE = "nose_tail"
FIT_CLEARANCE = 0.2          # radial gap between mating spigots and the body (per side)

# ---------------------------------------------------------------------------
# 5. Nose cone (gold)
# ---------------------------------------------------------------------------
CONE_OGIVE = 1.0             # 0 = straight cone; 1 = fully curved ogive whose base
                             # continues the body's slope with no crease
CONE_TIP_HALF_ANGLE_DEG = 32.0  # sharpness of the tip (half the included angle)
CONE_WALL = 2.0              # wall thickness of the hollow cone
JOINT_SHADOW_LINE = 0.4     # small chamfer on both sides of the body/cone joint: the surfaces
                             # stay flush and read as one form, split by a thin dark line
CONE_SPIGOT_DEPTH = 7.0      # how far the cone's locating spigot drops into the body
CONE_SPIGOT_WALL = 2.0       # wall thickness of that spigot ring

# ---------------------------------------------------------------------------
# 6. Fins x3 (gold). They are the legs, and their tips are the only ground contact.
# ---------------------------------------------------------------------------
FIN_COUNT = 3
FIN_ANGLE_OFFSET_DEG = 60.0  # angle of the first fin from the front; the others follow at 360/N.
                             # 60 puts two fins either side of the front and one at the rear.
FIN_TIP_REACH_FRAC = 1.70    # distance from the axis to a fin tip, as a multiple of the body RADIUS
FIN_ROOT_TOP_FRAC = 0.38     # where the fin's upper edge leaves the body (fraction of body height)
FIN_ROOT_BOTTOM_FRAC = 0.07  # where the fin's underside meets the body
FIN_OUTER_BULGE = 0.60       # 0 = straight upper edge; higher = rounder "shoulder"
FIN_UNDERCUT = 0.25          # 0 = straight underside; higher = deeper arch under the fin
FIN_ROOT_THICK = 17.0        # thickness where the fin meets the body
FIN_TIP_THICK = 8.0          # thickness at the tip (the fin tapers between the two)
FIN_TIP_FLAT = 7.0           # length of the flat pad at the tip that touches the ground
FIN_EDGE_FILLET = 3.8        # rounding on the fin edges. Just under half of FIN_TIP_THICK
                             # gives fully rounded, cast-looking edges

# ---------------------------------------------------------------------------
# 7. Foot and base collar (gold, one part). The collar is the gold ring under
#    the body; the foot is the short cylinder below it, kept clear of the ground.
# ---------------------------------------------------------------------------
COLLAR_HEIGHT_FRAC = 0.35    # collar height as a fraction of the base clearance
FOOT_DIA_FRAC = 0.35         # foot diameter as a fraction of BODY_MAX_DIA
FOOT_GROUND_GAP = 2.0        # gap between the foot and the ground (the fins carry the weight)
FOOT_SPIGOT_HEIGHT = 6.0     # in "nose_tail" mode: solid spigot that plugs into the body
                             # (it also acts as ballast and as the floor under the battery)

# ---------------------------------------------------------------------------
# 8. Grille, bezel, knob, LED (front, at 0 deg)
# ---------------------------------------------------------------------------
GRILLE_Z_FRAC = 0.62         # grille centre height (fraction of body height)
GRILLE_DIA_FRAC = 0.70       # grille diameter as a fraction of the body width at that height
GRILLE_THICK = 1.2           # perforated sheet thickness
GRILLE_RECESS = 1.5          # depth of the pocket the grille and bezel sit in
GRILLE_LEDGE = 2.5           # width of the ledge the grille rests on (the sound opening is smaller by this)
HEX_PATTERN_ENABLED = False  # honeycomb holes. False = plain disc (much faster while iterating on shape)
HEX_HOLE = 2.2               # hexagon size across the flats
HEX_WEB = 0.7                # metal left between neighbouring holes

BEZEL_WIDTH = 4.0            # radial width of the raised gold ring
BEZEL_PROUD = 1.5            # how far the ring stands above the red surface

KNOB_DIA = 18.0
KNOB_PROUD = 5.0             # knob face distance from the body surface (low, flat disc)
KNOB_GAP_FRAC = 0.085        # clear gap between the bezel and the top of the knob (fraction of body height)
KNOB_BODY_GAP = 0.5          # air gap behind the knob so it turns freely
KNOB_SHAFT_DIA = 6.0         # potentiometer/encoder shaft (6 mm is standard)
KNOB_BOSS_DIA = 10.0         # hidden boss on the back of the knob; it sits in a hole in the body
KNOB_BOSS_LENGTH = 3.0       # (hidden under the knob) so the low knob still grips the shaft
KNOB_FACE_SKIN = 1.2         # material left in front of the blind shaft bore
LED_DIA = 3.0                # LED hole; centred between the bezel and the knob

# ---------------------------------------------------------------------------
# 9. USB-C port (rear, offset to one side and low, near the battery and USB board)
# ---------------------------------------------------------------------------
USBC_ANGLE_DEG = 150.0       # 180 is dead rear; 150 is 30 deg to one side of the rear fin
USBC_Z_FRAC = 0.14           # height of the port centre (fraction of body height)
USBC_W = 8.94 + 2 * 0.35     # USB-C receptacle opening (8.94 x 3.26 per spec) + clearance
USBC_H = 3.26 + 2 * 0.35
USBC_POCKET_W = 14.0         # pocket cut on the INSIDE so the receptacle sits closer to the
USBC_POCKET_H = 8.0          # surface; the plug needs about 6.5 mm of engagement
USBC_WALL_AT_PORT = 1.0      # wall thickness left at the port after the inside pocket

# ---------------------------------------------------------------------------
# 10. Internals
# ---------------------------------------------------------------------------
DRIVER_DIA = 57.0            # full-range driver, outer frame diameter
DRIVER_DEPTH = 30.0          # driver depth, frame to magnet back
DRIVER_CLEARANCE = 0.4       # radial clearance around the driver frame
# The driver is FRONT-loaded: it goes in through the sound opening behind the grille
# (the top and bottom openings are too small), then screws onto a moulded ring.
# The build checks the sound opening is big enough (see the report).
DRIVER_FLANGE_WIDTH = 4.0    # how much of the driver frame rests on the mounting ring
DRIVER_RING_WIDTH = 5.0      # how far the mounting ring extends beyond the driver
DRIVER_MOUNT_THICK = 3.0     # thickness of the flat mounting ring
DRIVER_SCREW_HOLE = 2.5      # pilot holes for M3 self-tappers
DRIVER_SCREW_COUNT = 4

BATTERY_SIZE = (65.0, 37.0, 19.0)  # battery envelope L x W x H (default: 2 x 18650 side by side)
BATTERY_CLEARANCE = 1.0      # gap kept between the battery and the inner wall
# The build tries every orientation of the battery box and picks the one that
# sits lowest in the body (lowest centre of mass).

# Masses of bought-in parts, used for the centre of mass (grams)
BATTERY_MASS = 95.0
DRIVER_MASS = 65.0
PCB_MASS = 30.0              # amplifier, BT and USB board, assumed just above the battery
PCB_ABOVE_BATTERY = 12.0     # centre of the PCB mass above the top of the battery

# ---------------------------------------------------------------------------
# 11. Materials: production intent, used for mass and centre of mass.
#     Change a part's material by editing PART_MATERIALS.
# ---------------------------------------------------------------------------
MATERIAL_DENSITY = {          # g/cm^3
    "pc_abs": 1.20,           # moulded PC/ABS, then gloss lacquered
    "aluminium": 2.70,        # gold-anodised aluminium
    "zinc_diecast": 6.60,     # Zamak die-cast, gold plated
    "stainless": 7.90,
    "brass": 8.50,
    "pla": 1.24,              # typical FDM prototype
}
PART_MATERIALS = {
    "body": "pc_abs",
    "nose_cone": "aluminium",
    "fins": "zinc_diecast",
    "foot": "zinc_diecast",   # includes the base collar
    "grille": "aluminium",    # perforated sheet
    "bezel": "aluminium",
    "knob": "aluminium",
}

# ---------------------------------------------------------------------------
# 12. Output
# ---------------------------------------------------------------------------
STL_TOLERANCE = 0.05         # mm, maximum deviation of the STL triangles from the true surface
STL_ANGULAR_TOLERANCE = 0.2  # radians
RENDER_SIZE = (1200, 1600)   # width, height in pixels

# ---------------------------------------------------------------------------
# 13. Render look (PNG previews only; also used as the STEP part colours)
# ---------------------------------------------------------------------------
RED_HEX = "#8A1C15"          # warm deep oxblood lacquer
GOLD_HEX = "#C4A15A"         # soft brushed brass
BODY_ROUGHNESS = 0.22        # base paint under the clear coat
BODY_CLEARCOAT = 1.0         # 0 = none, 1 = full gloss clear coat on top
BODY_CLEARCOAT_ROUGHNESS = 0.04
GOLD_METALLIC = 1.0
GOLD_ROUGHNESS = 0.35        # soft, brushed reflections
LED_HEX = "#FFE2B0"          # warm white status LED
