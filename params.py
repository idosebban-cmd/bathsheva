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
BODY_MAX_DIA = 96.8      # widest point of the red body (fitted to the concept at 280 mm tall)

# ---------------------------------------------------------------------------
# 2. Vertical budget
#    OVERALL_HEIGHT = base clearance + body height + nose cone height
# ---------------------------------------------------------------------------
BASE_CLEARANCE_FRAC = 0.092  # ground to the underside of the red body, as a fraction of OVERALL_HEIGHT
CONE_HEIGHT_FRAC = 0.216     # nose cone height as a fraction of BODY height (the brief asked for 20-25%)

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
# The body side profile comes either from the measured concept ("points") or
# from the simple "fullness" curves above ("fullness").
BODY_PROFILE_MODE = "points"
# (height fraction 0 = bottom .. 1 = cone joint, radius / max radius), measured
# from reference/atelier_concept.png by reference/fit_concept.py. Below knob
# height (t < 0.34) the points are halfway between the fitted concept profile and
# a smooth taper, ending at a wide bottom that meets a wide, shallow collar.
BODY_PROFILE_POINTS = [
    (0.0000, 0.5200), (0.0200, 0.5463), (0.0500, 0.6222), (0.1000, 0.7296),
    (0.1600, 0.8381), (0.2200, 0.9209), (0.2800, 0.9628), (0.3611, 0.9873),
    (0.4150, 0.9995), (0.4689, 1.0000), (0.5227, 0.9900), (0.5766, 0.9784),
    (0.6305, 0.9559), (0.6843, 0.9253), (0.7382, 0.8857), (0.7921, 0.8387),
    (0.8460, 0.7826), (0.8998, 0.7101), (0.9537, 0.6331), (0.9806, 0.5879),
    (1.0000, 0.5542),
]
BODY_BOTTOM_LAND = 3.0       # flat land round the bottom opening (opening = bottom radius - this)
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
CONE_PROFILE_MODE = "points"  # "points" = measured concept shape; "ogive" = the two values below
# (height fraction 0 = joint .. 1 = tip, radius / base radius). The base continues
# the body's slope (flush joint); the concept's cone is ~2 mm narrower at the base,
# faded out towards the tip.
CONE_PROFILE_POINTS = [(0.000, 1.000), (0.047, 0.975), (0.202, 0.873), (0.358, 0.751), (0.514, 0.623), (0.669, 0.475), (0.747, 0.384), (0.825, 0.289), (0.903, 0.171), (0.965, 0.079), (1.000, 0.000)]
CONE_TIP_SOFTNESS = 0.0      # 0 = tip ends level (soft, rounded point, like the concept); higher = sharper
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
FIN_TIP_REACH_FRAC = 1.632   # distance from the axis to a fin tip, as a multiple of the body RADIUS
FIN_ROOT_TOP_FRAC = 0.310    # where the fin's upper edge leaves the body (fraction of body height)
FIN_ROOT_BOTTOM_FRAC = 0.0   # where the fin's underside meets the body
FIN_OUTER_BULGE = 0.850      # 0 = straight upper edge; higher = rounder "shoulder"
FIN_UNDERCUT = 0.400         # 0 = straight underside; higher = deeper arch under the fin
FIN_ROOT_THICK = 8.0         # thickness where the fin meets the body
FIN_TIP_THICK = 8.0          # thickness at the tip. Equal to the root = flat, parallel faces (concept)
FIN_TIP_FLAT = 8.0           # length of the flat pad at the tip that touches the ground
FIN_TOP_TAPER = 25.0         # the top this-many mm of each fin thins to a point into the body
FIN_TOP_THICK = 1.0          # thickness at the very top of the fin
FIN_EDGE_FILLET = 2.8        # rounding on the fin edges. Just under half of FIN_TIP_THICK
                             # gives fully rounded, cast-looking edges

FIN_WALL = 3.0               # die-cast wall thickness. The fin is hollow, open on the side facing
                             # the body (like a production casting); 0 = solid
FIN_BOLTS_Z_FRAC = (0.50, 0.62)  # bolt heights, as fractions along the fin root (bottom to top)
FIN_BOLT_CLEAR = 4.5         # M4 clearance hole through the body wall and the chassis ring
FIN_BOLT_PILOT = 3.3         # M4 tapping hole in the fin's internal boss
FIN_BOSS_DIA = 9.0           # cast boss inside the hollow fin that the bolt screws into
FIN_BOSS_LENGTH = 14.0

# ---------------------------------------------------------------------------
# 7. Foot and base collar (gold, one part). The collar is the gold ring under
#    the body; the foot is the short cylinder below it, kept clear of the ground.
# ---------------------------------------------------------------------------
COLLAR_HEIGHT_FRAC = 0.35    # collar height as a fraction of the base clearance
FOOT_DIA_FRAC = 0.183        # foot diameter as a fraction of BODY_MAX_DIA
FOOT_GROUND_GAP = 2.0        # gap between the foot and the ground (the fins carry the weight)
FOOT_SPIGOT_HEIGHT = 6.0     # in "nose_tail" mode: solid spigot that plugs into the body
                             # (it also acts as ballast and as the floor under the battery)

# ---------------------------------------------------------------------------
# 8. Grille, bezel, knob, LED (front, at 0 deg)
# ---------------------------------------------------------------------------
GRILLE_Z_FRAC = 0.652        # grille centre height (fraction of body height)
GRILLE_DIA_FRAC = 0.809      # grille diameter as a fraction of the body width at that height
GRILLE_THICK = 1.2           # perforated sheet thickness
GRILLE_RECESS = 1.5          # depth of the pocket the grille and bezel sit in
GRILLE_WRAPPED = True        # grille/bezel outline wraps round the body (full height, narrower seen
                             # from the front), as in the concept. False = true circle seen from the front
GRILLE_LEDGE = 2.5           # width of the ledge the grille rests on (the sound opening is smaller by this)
HEX_PATTERN_ENABLED = True   # honeycomb holes (front grille and rear cover). False = plain disc,
                             # which builds much faster while you iterate on the shape
HEX_HOLE = 2.2               # hexagon size across the flats
HEX_WEB = 0.7                # metal left between neighbouring holes

GRILLE_BACKING_THICK = 0.4   # charcoal acoustic cloth behind the grille (0 = none)
BEZEL_WIDTH = 3.0            # radial width of the raised gold ring
BEZEL_PROUD = 1.5            # how far the ring stands above the red surface

KNOB_DIA = 18.0
KNOB_PROUD = 5.0             # knob face distance from the body surface (low, flat disc)
KNOB_GAP_FRAC = 0.075        # clear gap between the bezel and the top of the knob (fraction of body height)
KNOB_BODY_GAP = 0.5          # air gap behind the knob so it turns freely
KNOB_SHAFT_DIA = 6.0         # potentiometer/encoder shaft (6 mm is standard)
KNOB_BOSS_DIA = 10.0         # hidden boss on the back of the knob; it sits in a hole in the body
KNOB_BOSS_LENGTH = 3.0       # (hidden under the knob) so the low knob still grips the shaft
KNOB_FACE_SKIN = 1.2         # material left in front of the blind shaft bore
LED_DIA = 3.0                # LED hole; centred between the bezel and the knob

# ---------------------------------------------------------------------------
# 9. USB-C port
# ---------------------------------------------------------------------------
# "collar": sealed port in the gold collar cup, facing down between two fins, so
#           it's hidden in normal viewing and the cable drops between the fins.
# "body":   the older port low on the red body (uses USBC_Z_FRAC). The rear and base
#           radiator layouts have no solid collar, so they always use this.
USBC_POSITION = "collar"
USBC_ANGLE_DEG = 120.0       # from the front; 120 is midway between the side fin (60) and rear fin (180)
USBC_TILT_DEG = 45.0         # "collar": the port faces this far below horizontal
USBC_Z_FRAC = 0.14           # "body": height of the port centre (fraction of body height)
# "collar" port: the face centre is put as low as possible while a standard plug's
# rigid overmold still clears the ground by USBC_PLUG_GROUND_CLEAR
USBC_PLUG_OVERMOLD = (12.35, 6.5, 16.0)  # plug overmold w x h (USB-IF max) x rigid length
USBC_PLUG_RELIEF = (5.0, 6.0)            # flexible strain relief dia x length (bends)
USBC_CABLE_DIA = 4.0
USBC_PLUG_GROUND_CLEAR = 2.0
# The product ships with a right-angle cable; its plug is checked too, with the
# cable leaving in each of the four directions (USB-C plugs go in either way up)
USBC_RA_HEAD_LEN = 11.0      # right-angle plug: head length along the port axis
USBC_RA_BOOT = (8.0, 20.0)   # boot width x length from the port axis, cable leaving sideways
USBC_RECESS_CLEAR = 0.5      # recess round the overmold, so it seats on the flat port face
USBC_RECEPTACLE = (10.6, 4.9, 9.5)  # sealed (IP67, gasketed) mid-mount receptacle envelope: w x h x length
USBC_RECEPTACLE_MASS = 3.0   # g, receptacle + its small board
USBC_COLLAR_POCKET = (11.6, 6.0, 13.0)  # pocket behind the port face for the receptacle + its small board: w x h x depth
USBC_WIRE_HOLE = 4.0         # wire channel from the pocket up into the battery bay
USBC_WIRE_SLOT = (5.0, 4.0)  # slot in the ballast cup's battery pocket that the wires run up
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

# Passive radiator (bought-in): rear-facing oval, mounted from inside on a
# moulded flat seat. It goes in through the driver opening before the driver.
PR_W = 40.0                  # oval width (horizontal)
PR_H = 60.0                  # oval height (vertical: fits the tall body better)
PR_DEPTH = 15.0              # frame + diaphragm travel, used as its volume envelope
PR_FLANGE = 4.0              # frame rim that sits on the seat (opening is smaller by this)
PR_RING_WIDTH = 4.0          # seat extends this far beyond the radiator
PR_ANGLE_DEG = 180.0         # 180 = dead rear
PR_Z_FRAC = 0.62             # centre height (fraction of body height); same as the driver
PR_MASS = 60.0
# Where the passive radiator goes:
#   "base" - fires DOWN through the collar into the gap above the ground; the back
#            stays smooth red. It must pass the collar opening, so it's a smaller
#            round unit (below), and the foot stub hangs lower on posts to leave an
#            exit gap, which can raise the body.
#   "rear" - the 60 x 40 oval above on the rear, behind a perforated gold cover.
#   "none" - (default) sealed enclosure, no radiator. The concept base (gold cup +
#            small foot) with no vent; the collar is a solid plug sealing the body.
PR_POSITION = "none"
PR_BASE_DIA = 44.0           # round radiator frame (must pass the ~48 mm collar opening)
PR_BASE_EFFECTIVE_DIA = 35.0 # radiating diameter (about 0.8 x frame)
PR_BASE_DEPTH = 15.0
PR_BASE_MASS = 40.0
PR_BACK_CLEARANCE = 6.0      # air gap behind the radiator before the ballast/battery
PR_EXIT_AREA_RATIO = 1.0     # open (hole) area of the base mesh vs the radiating area (1 = equal)

# How the base looks with PR_POSITION = "base":
#   "vent"   - (concept) slim gold collar, a narrow vent gap under it that reads as a
#              dark shadow line (recessed dark mesh behind it), and a small rounded foot
#   "nozzle" - gold honeycomb mesh ring and stepped rocket-engine nozzle (settings below)
BASE_STYLE = "vent"
BASE_VENT_GAP = 3.5          # height of the vent gap under the collar
BASE_VENT_RECESS = 2.5       # the dark mesh sits this far inside the collar's lower edge
BASE_VENT_MESH_THICK = 0.6   # black woven/perforated mesh ring
BASE_VENT_MESH_OPEN = 0.60   # its open-area ratio (typical fine black stainless mesh)
BASE_VENT_PLATE = 1.0        # dark plate that closes the bottom of the vent, sunk into the foot top
COLLAR_BOTTOM_DIA_FRAC = 0.30   # collar tapers from the body bottom to this (fraction of BODY_MAX_DIA)
COLLAR_TOP_SLOPE = 0.5       # cup starts nearly vertical under the body (a convex bowl)...
COLLAR_END_SLOPE = 1.2       # ...and curves in towards the foot (1 = 45 deg; 2 = a shallow bowl)
COLLAR_WALL = 1.5            # collar bore wall
FOOT_HEIGHT = 10.0           # short rounded knob under the cup (no vent); the "vent" style takes BASE_VENT_GAP off this
FOOT_ROUND = 3.5             # rounding on the foot's lower edge
FIN_CUP_GAP = 0.2            # gap between the fins and the collar cup (hairline, no light showing through)

# Base "engine" (only with PR_POSITION = "base" and BASE_STYLE = "nozzle"). Under the gold collar, a ring
# of the same perforated honeycomb sheet as the front grille lets the radiator
# breathe out while hiding the inside. The ring also carries the stepped gold
# nozzle below it, so there are no visible posts.
BASE_MESH_INSET = 1.0        # mesh ring sits this far inside the collar's lower edge (a small reveal)
BASE_MESH_LAND = 1.5         # solid, unperforated band top and bottom, where it bonds to collar and nozzle
FOOT_NOZZLE_HEIGHT = 8.0     # total height of the nozzle (injector plate + throat + bell steps)
FOOT_NOZZLE_PLATE = 1.2      # injector plate that closes the bottom of the mesh ring
FOOT_NOZZLE_STEPS = 3        # stepped bell below the throat, widening towards the ground
FOOT_NOZZLE_THROAT_FRAC = 0.55  # throat radius as a fraction of the nozzle exit radius
BASE_DEFLECTOR = True        # gold cone inside the mesh ring: hides the see-through view and turns
BASE_DEFLECTOR_GAP = 4.0     # the air outward; its base stops this far inside the mesh
FOOT_NOZZLE_DISH = 1.2       # shallow gold dish in the nozzle exit (reads as a nozzle, no dark hole)
FOOT_POSTS = 0               # optional posts from collar to nozzle, hidden inside the mesh ring
                             # (0 = the mesh ring carries the nozzle on its own)
FOOT_POST_DIA = 4.0
REAR_COVER_ENABLED = True    # gold perforated cover + bezel over the radiator opening, same
                             # sheet, hole pattern, ledge, recess and bezel as the front grille

# Internal chassis (steel), fitted in pieces because nothing wider than the
# openings (collar ~48 mm, cone ~54 mm, driver hole ~60 mm) can get inside:
# * 3 fin brackets: curved plates hugging the wall behind each fin. The fin
#   bolts go through the body into them, and each bracket bolts to the ballast cup.
# * a spine plate standing on the ballast cup behind the driver. It carries the
#   PCBs and has a tab under the driver magnet.
CHASSIS_THICK = 1.2          # sheet thickness
CHASSIS_BRACKET_WIDTH = 30.0 # width of each fin bracket along the wall
CHASSIS_WEB_OFFSET = 7.0     # bracket web sits beside the bolt line, clear of the bolt heads
CHASSIS_GAP = 0.3            # clearance to the inner wall

# Ballast: a steel cup round the upright battery, bolted onto the foot. The
# foot, the cup and the battery go in together through the collar opening. Its
# diameter is set by that opening and its height by the mass.
BALLAST_MASS_G = "auto"      # "auto" = sized so the total hits TARGET_MASS_G, or a number in grams
TARGET_MASS_G = 1800.0       # the report compares the total against this
BALLAST_DRIVER_CLEARANCE = 3.0  # the cup stops this far below the driver; if the target needs
                                # more steel than fits, the report shows the shortfall

BUTYL_MASS_G = 50.0          # damping pads on the inside of the shell
BUTYL_DENSITY = 1.6          # used to subtract their volume from the air volume

# Masses of bought-in parts, used for the centre of mass (grams)
BATTERY_MASS = 95.0
DRIVER_MASS = 65.0
PCB_MASS = 30.0              # amplifier + BT board, mounted on the chassis spine

# ---------------------------------------------------------------------------
# 11. Materials: production intent, used for mass and centre of mass.
#     Change a part's material by editing PART_MATERIALS.
# ---------------------------------------------------------------------------
MATERIAL_DENSITY = {          # g/cm^3
    "pc_abs": 1.20,           # moulded PC/ABS, then gloss lacquered
    "aluminium": 2.70,        # gold-anodised aluminium
    "zinc_diecast": 6.60,     # Zamak die-cast, gold plated
    "steel": 7.85,            # galvanised sheet steel / steel bar
    "stainless_304": 8.00,    # perforated stainless sheet, gold PVD
    "brass": 8.50,            # solid brass, turned
    "tungsten_alloy": 17.6,   # W-Ni-Fe heavy alloy ballast option (dense but costly)
    "pla": 1.24,              # typical FDM prototype
    "acoustic_cloth": 0.50,   # charcoal speaker cloth
}
PART_MATERIALS = {
    "body": "pc_abs",
    "nose_cone": "aluminium",
    "fins": "zinc_diecast",   # hollow die-casting, see FIN_WALL
    "foot": "zinc_diecast",   # includes the base collar
    "grille": "stainless_304",
    "bezel": "aluminium",
    "knob": "brass",
    "chassis": "steel",       # internal sled
    "grille_backing": "acoustic_cloth",
    "vent_insert": "stainless_304",  # black PVD mesh + plate in the base vent
    "ballast": "steel",       # internal ballast slug
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
LED_HEX = "#FFE2B0"
CLOTH_HEX = "#2B2A29"        # charcoal grille backing
VENT_HEX = "#3A2B1D"         # the vent insert under the collar: dark bronze, reads as shadow          # warm white status LED
