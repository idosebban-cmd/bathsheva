# Faro logo: master artwork

A half sun with seven rays rising over the sea. Eleven black shapes (seven rays, the sun and three sea bands) inside one true circle. There is no border ring: the circle is formed by the ends of the shapes.

| File | Use |
|---|---|
| `faro_logo.svg` | Master vector, Ø100 mm (scale freely) |
| `faro_logo.pdf` | Same, for print |
| `faro_logo.dxf` | Same, for CAD / cutting (mm, centred on the origin, layer `LOGO`, outlines plus solid hatch) |
| `faro_logo.png` | 2048 × 2048, black on a transparent background |
| `faro_logo_master.json` | The shape outlines (unit radius, +Y up), used to build everything above |
| `faro_logo_curves.json` | The traced curves the shapes are built from |

How it was made: `scripts/trace_logo.py` traces the grooves of the reference image (`backend/seed/artwork/reference/logo_reference.webp`). It finds the plate edges either side of every groove, takes the centre-line and width, and fits smooth curves. The grooves line up with the reference to a median of 1 px (90 % within 2.5 px) on a medallion about 1,120 px across. The reference medallion is slightly out of round, so the master uses the true circle that best fits it.

Regenerate the files with `backend/.venv/bin/python scripts/export_nameplate_artwork.py`. Change the curves, never the files by hand.

The knob engraving (`backend/seed/artwork/F-11_knob_logo.*`) is made from this master. On the knob only, the horizon line is widened to 0.3 mm and a 0.3 mm edge groove runs round the medallion, so every engraved line is at least 0.3 mm at Ø16 mm.
