# Product ideas from the standard-parts library

Fifteen concepts for Bathsheva London, built mostly from parts in [`library.md`](library.md) plus light custom work: cutting, drilling, lacquering, simple laser-cut and turned pieces. The aim is mid-century-inspired products at £150–250 retail.

## Ground rules applied

- **Real metal only.** Anything that looks metallic is real metal. Visible brass is solid brass (CZ108/CZ121 stock, S. Lilley or Peter Willetts parts, The Mesh Company brass mesh). No brass-plated steel is used where it shows, so the Lampspares brass-plated harp, the Lamparte plated lampholders and the Mesh Warehouse "brass" meshes are all left out. The Lampspares fixed "brass" harps may be S. Lilley's brass-plated harps, so they're left out too until confirmed solid; no concept uses a harp (checked 13 Oct 2026). Black-painted steel (the Visaton grilles) is real metal and reads as black, so it's allowed.
- **Avoided parts:** nothing flagged as discontinued or no longer stocked (the Hificollective 25 mm brass knob, Visaton FRS 8 M at CPC (the driver itself is still current: in stock at SOS Electronic, 13 Oct 2026), Peerless TC9FD18-08, Bridgelux 2916910), and nothing out of stock at the snapshot (Lampfix brass tube, Dayton PC68-8, Tang Band W3-881SJ, Wondom AA-JA32173).
- **Listed prices over quote-only parts.** Quote-only parts (metal spinners, trade glass cylinders, Essex Tube Windings) appear only as the route to scale, never in a cost.
- **Premium before cheapest.** Glass before acrylic, solid brass before plated, and ply-stack or turned beech before MDF.
- **Wording:** "mid-century inspired". No claims of Italian design.

## How the costs are worked out

- **Parts only.** The costs are library prices added as listed. They don't include labour for the custom work, finishing, packaging, freight, certification, or the parts the library doesn't cover (each concept lists those).
- **Prices come from the library's search snapshots**, a mix of ex-VAT and inc-VAT, and none are verified. If VAT is reclaimed, inc-VAT lines overstate the cost by up to a sixth.
- **Price breaks** are applied only where the library lists one, and only once the order reaches it: the order is the build quantity × the quantity per product. The Morplan tube break (£0.75 at 100+) applies at both 100 and 500. The Hi-Line strip break (£33.60 per 5 m roll at 200 rolls) applies to none of the concepts, which use under a third of a roll each. Everything else is the same price at 100 and 500. In practice suppliers would discount at 500, so the 500 figures are conservative. (Corrected 13 Oct 2026: the first version applied both breaks at 500 only. That understated Morel, Lantern, Reed and Beacon at 500 by up to £0.59 and overstated Reed at 100 by £0.32.)
- **Machine-readable parts lists:** each concept ends with a hidden `<!-- concept-parts -->` list (part id from the library; a quantity in the part's priced unit, or a length or width × height in mm with a count and waste %; a note; an optional price variant). The workbench's Standard Parts page reads it to cost the concept and to open it in the concept builder, and a test checks it reproduces the costs stated here. Keep the two in step when editing a concept.
- **Materials for custom pieces are costed from library stock prices:**

  | Material | Rate used | Library source |
  |---|---|---|
  | Brass sheet, 1 mm | £0.032/cm² of bounding square | £20 ex VAT per 250 × 250 mm, The Metal Store |
  | Brass tube, 1/2" × 16 swg polished CZ108 | £24/m | £60 per 2.5 m, The Metal Store |
  | Beech plywood, 18 mm | £21.30/m² incl. 30% waste | £48.82 per 2440 × 1220 mm sheet, CTS DIY |
  | Beech turning blank, 4 × 4 × 1.75" | £3.35 | Classic Hand Tools |
  | LED strip, 24 V 3000 K CRI 90 | £8.40/m (£6.72/m at 200 rolls) | Hi-Line Lighting |

- EUR prices are converted at €1 = £0.85 (an assumption).
- **Shared sub-assemblies:**
  - Oaklea brass inline lamp kit (£9.86: cable set, 10 mm brass lampholder, grommets);
  - S. Lilley E27 brass shade ring (£1.39);
  - S. Lilley M10 brass fixing kit (£3.99);
  - three Cousins solid brass 20 mm bun feet (3 × £3.50; the library notes the price mapping on that page is unclear);
  - battery set: Battery 101 1S2P 7000 mAh pack (£16.94) plus Adafruit bq24074 USB-C charger from The Pi Hut (£14.40).
- **Target check:** the workbench's pricing defaults (`backend/seed/cost/pricing.yaml`) put the direct-to-consumer factory-cost target at ex-VAT retail × 0.33: £41 at £150 and £69 at £250. That target is for the whole factory cost, so **parts alone should sit well under it**. "% of target" below is parts ÷ target. Under 75% leaves room for labour and finishing; 75–100% is tight; over 100% doesn't work as specified.

## Summary

| # | Concept | Type | Retail | Parts @100 | Parts @500 | % of DTC target | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Tambour | Mains table lamp, frosted glass cylinder | £250 | £64.84 | £64.84 | 94% | Tight |
| 2 | Lune | Mains table lamp, opal globe on ply stack | £220 | £55.20 | £55.20 | 91% | Tight |
| 3 | Morel | Cordless mushroom lamp | £225 | £69.45 | £69.45 | 112% | Over |
| 4 | Bell | Mains cone-shade table lamp | £195 | £49.51 | £49.51 | 92% | Tight |
| 5 | Lattice | Mains lamp, perforated aluminium shade | £175 | £31.58 | £31.58 | 66% | Room |
| 6 | Halo | Wall sconce, clear glass dome | £175 | £47.06 | £47.06 | 98% | Tight |
| 7 | Lantern | Cordless frosted-cylinder lamp | £250 | £102.88 | £102.88 | 150% | Over |
| 8 | Prism | Mains lamp, frosted acrylic tube | £150 | £29.29 | £29.29 | 71% | Room |
| 9 | Orbit | Opal globe pendant | £230 | £60.67 | £60.67 | 96% | Tight |
| 10 | Sonnet | Bluetooth speaker | £250 | £117.41 | £117.41 | 171% | Over |
| 11 | Pavilion | Passive bookshelf speakers (pair) | £250 | £68.51 | £68.51 | 100% | Tight |
| 12 | Reed | Cordless paper-tube column lamp | £150 | £42.52 | £42.52 | 103% | Over |
| 13 | Trio | Candlesticks, set of three | £165 | £47.77 | £47.77 | 105% | Over |
| 14 | Meridian | Bookends (pair) | £150 | £26.70 | £26.70 | 65% | Room |
| 15 | Beacon | Small cordless bedside light | £165 | £62.36 | £62.36 | 137% | Over |

**Pattern:** every cordless or Bluetooth concept is over target. The dev-board battery set (£31.34) and the Wondom amplifier (£31.95) are prototype modules, and at 500 units a custom board from an ODM would replace them. So cordless concepts only work through the route Faro and Atelier already take. The mains lamps and the non-electrical objects are where the library is strong.

**Shortlist to prototype first:** Lattice (5), Bell (4), Lune (2), Tambour (1), Meridian (14). Then Prism (8) if a cheaper entry product is wanted.

---

## Lighting

### 1. Tambour — frosted glass cylinder table lamp

A slim column of internally frosted borosilicate glass stands on a turned beech plinth. It sits on three solid brass bun feet and glows evenly from top to bottom, like a lit drum. This is the calm, architectural companion to Faro: the same frosted-glass language with none of the lighthouse detail. The beech is lacquered in a warm natural or ebonised finish. The only visible metal is solid brass.

- **Library parts:**
  - J Moncrieff internally frosted cylinder shade, 80 × 210 mm, 40 mm fitter, £35 (§1.5);
  - Oaklea brass inline lamp kit (§3.3);
  - 2 × S. Lilley E27 brass shade rings, one either side of the cylinder's 40 mm fitter (48 mm outer, 37 mm inner Ø) (§3.4);
  - 2 × beech turning blanks, 4 × 4 × 1.75" (§6.1);
  - 3 × Cousins brass bun feet (§4.6).
- **Custom work:** glue up and turn the two blanks into a 100 mm plinth with a seat for the cylinder; bore the cable path; lacquer; drill and fix the feet.
- **Parts cost:** £64.84 at 100 and £64.84 at 500 (cylinder £35.00, kit £9.86, two shade rings £2.78, blanks £6.70, feet £10.50).
- **Not in library:** LED lamp, inline switch or dimmer, plug, packaging.
- **Main risk:** supply at volume. The cylinder is a retail stock item. At 500 it should come through J Moncrieff's trade cylinders (quote only, MOQ 50–200), and that route sets the real cost. Also check that the kit's lampholder takes E27 shade rings: the 40 mm fitter sits between the rings' 37 mm bore and 48 mm outside, so two rings can clamp it.

<!-- concept-parts
- {part: internally-frosted-cylinder-shade--j-moncrieff-uk, qty: 1, note: '80 × 210 mm frosted cylinder'}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder, flex, plug, switch'}
- {part: es-e27-shade-ring-s-lilley-spare--lampspares-uk, qty: 2, note: 'two E27 shade rings clamping the 40 mm fitter'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 2, note: 'two 4 × 4 × 1.75" blanks glued for the plinth'}
- {part: bun-feet--cousins-uk, qty: 3, note: 'three 20 mm bun feet'}
-->

### 2. Lune — opal globe on a plywood stack

A 150 mm gloss opal globe sits in a shallow brass collar on a stepped base of three beech-ply discs. The exposed ply edges are a deliberate mid-century nod to moulded plywood furniture. The lamp is low and moon-like, and the opal glass hides the light source completely.

- **Library parts:**
  - J Moncrieff 150 mm opal globe, 80 mm fitter neck, £30 (§2.3);
  - Oaklea brass lamp kit (§3.3);
  - 18 mm beech plywood, three 160 mm discs (§6.3);
  - 1 mm brass sheet for the collar (§4.3);
  - 3 × brass bun feet (§4.6).
- **Custom work:** CNC-route and laminate the discs with a pocket for the globe neck; laser-cut a 100 mm brass collar ring; brush and lacquer the brass; lacquer the ply.
- **Parts cost:** £55.20 at 100 and £55.20 at 500 (globe £30.00, kit £9.86, ply £1.64, brass collar £3.20, feet £10.50).
- **Not in library:** LED lamp, switch, plug, collar screws.
- **Main risk:** retaining the globe. The library has no 80 mm screw gallery, so the custom collar and its clamp screws must hold the globe safely against a knock. J Moncrieff also showed low stock on the 200 mm size, so check the 150 mm stock depth before committing.

<!-- concept-parts
- {part: 150-mm-opal-globe-80-mm-fitter-neck--j-moncrieff-uk, qty: 1, note: '150 mm opal globe'}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder, flex, plug, switch'}
- {part: premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk, size_mm: [160, 160], count: 3, waste_pct: 30, note: 'three 160 mm discs for the stacked base'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [100, 100], note: '100 mm laser-cut brass collar', option: 1}
- {part: bun-feet--cousins-uk, qty: 3, note: 'three 20 mm bun feet'}
-->

### 3. Morel — cordless mushroom lamp

A small internally frosted glass dome is held on a brushed brass stem by a solid brass ball finial screwed through the dome's 12 mm hole. It stands on a turned beech base that hides the battery. It is a cordless take on the mid-century mushroom lamp, sized for a bedside or dining table and charged by USB-C.

- **Library parts:**
  - J Moncrieff internally frosted dome, 100 × 100 mm, 12 mm fitter hole, £20 (§2.3);
  - In The Light Direction solid brass M10 ball finial, £1 (§3.1);
  - 180 mm of 1/2" CZ108 polished brass tube (§1.3);
  - S. Lilley M10 fixing kit (§3.3);
  - 2 × beech blanks (§6.1);
  - Battery 101 1S2P pack and Adafruit bq24074 charger (§7.4, §7.5);
  - 0.25 m Hi-Line 3000 K CRI 90 strip (§3.5).
- **Custom work:** turn the base with a battery pocket; cut and brush the tube; run M10 rod through the stem; fit the LED strip to a small spine under the dome; lacquer.
- **Parts cost:** £69.45 at 100 and £69.45 at 500 (dome £20.00, finial £1.00, tube £4.32, M10 kit £3.99, blanks £6.70, battery set £31.34, strip £2.10).
- **Not in library:** LED driver (the 24 V strip needs a boost driver from the 3.7 V pack), touch or rotary dimmer, USB-C port, fire-safe battery enclosure.
- **Main risk:** cost and certification. The battery set is a dev module with no product certification and takes the concept over target. It's viable only with a custom driver and charger board and a pre-certified pack, as on Faro.

<!-- concept-parts
- {part: internally-frosted-dome-12-mm-fitter--j-moncrieff-uk, qty: 1, note: '100 × 100 mm frosted dome'}
- {part: solid-brass-ball-finial-7112--in-the-light-direction-uk, qty: 1, note: 'M10 ball finial holding the dome'}
- {part: cz108-round-tube-polished--the-metal-store-uk, length_mm: 180, note: '180 mm brass stem'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 2, note: 'two blanks for the base'}
- {part: 1s2p-li-ion-pack-3-7-v-7000-mah--battery-101-uk, qty: 1, note: '1S2P battery pack'}
- {part: adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk, qty: 1, note: 'USB-C charger board'}
- {part: m10-lampholder-fixing-kit-s-lilley--light-and-power-solutions-uk, qty: 1, note: 'M10 rod, nut and washers'}
- {part: cob-led-strip-24-v-3000-k-cri-90-15-w-m-1500-lm-m--hi-line-lighting-uk, length_mm: 250, note: '0.25 m of LED strip'}
-->

### 4. Bell — cone shade table lamp

A hand-spun aluminium cone, lacquered inside and out in one of the Bathsheva colours (oxblood, cream or satin black), sits on a slender brushed brass stem and a stepped beech-ply base. It's a classic mid-century desk-lamp silhouette, kept simple: one colour, one metal, one wood.

- **Library parts:**
  - hand-spun aluminium shade, 8.25", £14.50, from an Etsy UK seller (§2.1);
  - Oaklea brass lamp kit (§3.3);
  - S. Lilley E27 brass shade ring (§3.4);
  - 300 mm of 1/2" brass tube (§1.3);
  - S. Lilley M10 fixing kit (§3.3);
  - 18 mm beech plywood, three 180 mm discs (§6.3);
  - 3 × brass bun feet (§4.6).
- **Custom work:** lacquer the shade, with a contrasting cream inside for reflectance; ream the shade neck to suit the E27 ring; cut and brush the stem; rout and laminate the base; lacquer.
- **Parts cost:** £49.51 at 100 and £49.51 at 500 (shade £14.50, kit £9.86, ring £1.39, tube £7.20, M10 kit £3.99, ply £2.07, feet £10.50).
- **Not in library:** LED lamp, switch, plug.
- **Main risk:** the shade source. An Etsy maker can't reliably supply 100–500 identical shades. At volume the shade moves to a UK metal spinner (Excell, Winward, Calder: quote only, possibly reusing an existing former), and that quote decides the cost.

<!-- concept-parts
- {part: hand-spun-aluminium-shades--etsy-uk-sellers-marketplace, qty: 1, note: '8.25" spun aluminium shade', option: 1}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder, flex, plug, switch'}
- {part: es-e27-shade-ring-s-lilley-spare--lampspares-uk, qty: 1, note: 'E27 shade ring'}
- {part: cz108-round-tube-polished--the-metal-store-uk, length_mm: 300, note: '300 mm brass stem'}
- {part: m10-lampholder-fixing-kit-s-lilley--light-and-power-solutions-uk, qty: 1, note: 'M10 rod, nut and washers'}
- {part: premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk, size_mm: [180, 180], count: 3, waste_pct: 30, note: 'three 180 mm discs for the base'}
- {part: bun-feet--cousins-uk, qty: 3, note: 'three 20 mm bun feet'}
-->

### 5. Lattice — perforated aluminium shade lamp

A cylinder of round-hole perforated aluminium, lacquered in a solid colour, wraps a frosted inner tube. The light comes through as a fine dot pattern, recalling mid-century perforated-metal furniture and lighting. Laser-cut brass rings cap the top and bottom, and the cylinder stands on a two-disc beech-ply base. It's the simplest concept to make and has the most cost headroom.

- **Library parts:**
  - F H Brundle perforated aluminium R3 T6, 2 × 1 m × 1.5 mm, £56.90 ex VAT per sheet, about 21 shades per sheet (§5.1);
  - Clear Plastic Shop 60 × 5 mm clear acrylic tube, 250 mm per lamp (§1.4);
  - 1 mm brass sheet, two 130 mm rings (§4.3);
  - 18 mm beech plywood, two 160 mm discs (§6.3);
  - Oaklea brass lamp kit (§3.3).
- **Custom work:** cut the perforated blanks and roll them to 120 mm diameter with a hidden seam; lacquer; sandblast the acrylic for a frosted finish; laser-cut, brush and lacquer the brass rings; rout the base.
- **Parts cost:** £31.58 at 100 and £31.58 at 500 (perforated sheet £2.71, acrylic £7.11, brass rings £10.82, ply £1.09, kit £9.86). Brundle lists a break at 18+ sheets but doesn't show the price, so it isn't applied. For hand-made prototypes, the Modelshop 400 × 250 mm sheet (£11.60, one shade each) is easier to buy.
- **Not in library:** LED lamp, switch, plug.
- **Main risk:** the pattern and finish. Brundle's listing gives conflicting open areas (53% and 23%), which changes how bright and how "dotted" the lamp looks, so order a sheet before deciding. Lacquer adhesion and seam neatness on rolled 1.5 mm aluminium need a sample.

<!-- concept-parts
- {part: perforated-aluminium-r3-t6-1-5-mm--f-h-brundle-uk, qty: 0.04762, note: 'one rolled 120 mm shade (about 21 per 2 × 1 m sheet)'}
- {part: clear-extruded-tube-60-5-mm-1-m--the-clear-plastic-shop-uk, length_mm: 250, note: '250 mm frosted inner tube'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [130, 130], count: 2, note: 'two 130 mm brass rings', option: 1}
- {part: premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk, size_mm: [160, 160], count: 2, waste_pct: 30, note: 'two 160 mm discs for the base'}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder, flex, plug, switch'}
-->

### 6. Halo — glass dome wall sconce

A small clear glass dome sits under a short brushed brass arm on a laser-cut brass back plate: a compact mid-century sconce for hallways and bedsides, sold in pairs as well as singly.

- **Library parts:**
  - J Moncrieff small clear glass dome, 70 × 75 mm, 30 mm fitter, £25 (§2.3);
  - 1 mm brass sheet for a 120 mm back plate (§4.3);
  - 150 mm of 1/2" brass tube (§1.3);
  - S. Lilley M10 fixing kit (§3.3);
  - Oaklea brass lamp kit, for the lampholder and grommets (§3.3).
- **Custom work:** laser-cut the back plate with fixing slots; cut, bend or braze the arm to the plate; brush and lacquer.
- **Parts cost:** £47.06 at 100 and £47.06 at 500 (dome £25.00, plate £4.61, tube £3.60, M10 kit £3.99, kit £9.86).
- **Not in library:** BC lampholder (the dome fits a BC holder; confirm whether the Oaklea kit's holder is BC), wall box, LED lamp.
- **Main risk:** compliance for fixed wiring. A hard-wired wall light is installed by an electrician, and needs the right enclosure, earthing of the brass, and UKCA/LVD testing. A plug-in version with a fabric flex is simpler to certify.

<!-- concept-parts
- {part: small-clear-glass-dome-30-mm-fitter--j-moncrieff-uk, qty: 1, note: '70 × 75 mm clear dome'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [120, 120], note: '120 mm brass back plate', option: 1}
- {part: cz108-round-tube-polished--the-metal-store-uk, length_mm: 150, note: '150 mm brass arm'}
- {part: m10-lampholder-fixing-kit-s-lilley--light-and-power-solutions-uk, qty: 1, note: 'M10 rod, nut and washers'}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder and grommets'}
-->

### 7. Lantern — cordless frosted cylinder lamp

A rechargeable version of Tambour, with a turned beech base, a brass cap and a solid brass knob that dims the light. It's a portable lamp for dining tables and terraces, charged by USB-C.

- **Library parts:**
  - J Moncrieff frosted cylinder, 80 × 210 mm (§1.5);
  - battery set (§7.4, §7.5);
  - 0.3 m Hi-Line LED strip (§3.5);
  - 1 mm brass sheet for a 90 mm cap (§4.3);
  - brass ball finial (§3.1);
  - 2 × beech blanks (§6.1);
  - Hificollective Audio Note 12 mm brass knob, £13.23 ex VAT (§4.5);
  - 3 × brass bun feet (§4.6).
- **Custom work:** turn the base with a battery pocket and knob boss; laser-cut and dome the cap; fit the strip to a central spine; lacquer.
- **Parts cost:** £102.88 at 100 and £102.88 at 500 (cylinder £35.00, battery set £31.34, strip £2.52, cap £2.59, finial £1.00, blanks £6.70, knob £13.23, feet £10.50).
- **Not in library:** LED driver and boost, dimmer potentiometer, USB-C port, fire enclosure.
- **Main risk:** too close to Faro and too expensive. At 150% of target it only works with a custom board, and it competes with Faro for the same customer. It's better treated as a Faro accessory or a later "Faro Petite".

<!-- concept-parts
- {part: internally-frosted-cylinder-shade--j-moncrieff-uk, qty: 1, note: '80 × 210 mm frosted cylinder'}
- {part: 1s2p-li-ion-pack-3-7-v-7000-mah--battery-101-uk, qty: 1, note: '1S2P battery pack'}
- {part: adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk, qty: 1, note: 'USB-C charger board'}
- {part: cob-led-strip-24-v-3000-k-cri-90-15-w-m-1500-lm-m--hi-line-lighting-uk, length_mm: 300, note: '0.3 m of LED strip'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [90, 90], note: '90 mm brass cap', option: 1}
- {part: solid-brass-ball-finial-7112--in-the-light-direction-uk, qty: 1, note: 'ball finial'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 2, note: 'two blanks for the base'}
- {part: audio-note-brass-knob-mwk-01-9000-9001--hificollective-uk, qty: 1, note: '12 mm brass dimmer knob', option: 1}
- {part: bun-feet--cousins-uk, qty: 3, note: 'three 20 mm bun feet'}
-->

### 8. Prism — frosted acrylic column lamp

An entry-price lamp: a sandblasted acrylic tube between two laser-cut brass end caps, finished with a brass ball finial and set on a turned beech foot. It has Tambour's look at a lower price and weight, and it's safer for children's rooms because it can't shatter.

- **Library parts:**
  - Clear Plastic Shop 60 × 5 mm clear acrylic tube, 280 mm per lamp (§1.4);
  - 1 mm brass sheet, two 70 mm caps (§4.3);
  - brass ball finial (§3.1);
  - S. Lilley M10 fixing kit (§3.3);
  - Oaklea brass lamp kit (§3.3);
  - 1 × beech blank (§6.1).
- **Custom work:** cut and sandblast the tube; laser-cut the caps with an M10 hole and brush them; turn the foot; lacquer.
- **Parts cost:** £29.29 at 100 and £29.29 at 500 (acrylic £7.96, caps £3.14, finial £1.00, M10 kit £3.99, kit £9.86, blank £3.35).
- **Not in library:** LED lamp, switch, plug.
- **Main risk:** premium perception. Acrylic can read as cheaper than glass, and it scratches and attracts dust. Test whether the frosted acrylic passes the "premium before cheapest" bar next to Tambour. If it doesn't, drop it rather than discount the brand.

<!-- concept-parts
- {part: clear-extruded-tube-60-5-mm-1-m--the-clear-plastic-shop-uk, length_mm: 280, note: '280 mm tube, sandblasted'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [70, 70], count: 2, note: 'two 70 mm brass end caps', option: 1}
- {part: solid-brass-ball-finial-7112--in-the-light-direction-uk, qty: 1, note: 'ball finial'}
- {part: m10-lampholder-fixing-kit-s-lilley--light-and-power-solutions-uk, qty: 1, note: 'M10 rod, nut and washers'}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder, flex, plug, switch'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 1, note: 'one blank for the foot'}
-->

### 9. Orbit — opal globe pendant

A 200 mm matt opal globe hangs from a brushed brass drop rod, held by a laser-cut brass collar, with a turned beech ceiling cup. It's a classic mid-century globe pendant made in the brand's materials.

- **Library parts:**
  - J Moncrieff 200 mm opal globe, 80 mm fitter hole, £35 (§2.3);
  - 300 mm of 1/2" brass tube (§1.3);
  - 1 × beech blank for the ceiling cup (§6.1);
  - 1 mm brass sheet for a 110 mm collar (§4.3);
  - Oaklea brass lamp kit (§3.3);
  - S. Lilley E27 brass shade ring (§3.4).
- **Custom work:** turn the ceiling cup; laser-cut the collar and fit three thumbscrews; cut and brush the rod; lacquer.
- **Parts cost:** £60.67 at 100 and £60.67 at 500 (globe £35.00, tube £7.20, blank £3.35, collar £3.87, kit £9.86, ring £1.39).
- **Not in library:** ceiling plate and bracket, strain relief, LED lamp.
- **Main risk:** supply and installation. Only 5 globes were in stock at the snapshot. It's a hard-wired ceiling fitting (electrician install, UKCA/LVD), and a wooden ceiling cup needs a non-combustible inner cover over the terminals.

<!-- concept-parts
- {part: 200-mm-opal-globe-80-mm-fitter-hole--j-moncrieff-uk, qty: 1, note: '200 mm opal globe'}
- {part: cz108-round-tube-polished--the-metal-store-uk, length_mm: 300, note: '300 mm brass drop rod'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 1, note: 'one blank for the ceiling cup'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [110, 110], note: '110 mm brass collar', option: 1}
- {part: brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk, qty: 1, note: 'lampholder and flex'}
- {part: es-e27-shade-ring-s-lilley-spare--lampspares-uk, qty: 1, note: 'E27 shade ring'}
-->

## Audio

### 10. Sonnet — Bluetooth desk speaker

A compact mono speaker: a stack of beech-ply rings, a solid brass mesh front framed by a brass ring, and a gold Audio Note brass knob for volume. It's a smaller, simpler sibling to Atelier, with an 80 mm German full-range driver.

- **Library parts:**
  - Visaton FRS 8/8 (2004) from SOS Electronic, £11.37 ex VAT, £10.69 at 4+ (§7.1; was €12.56 from Toutlehautparleur);
  - Wondom JAB3+ 2 × 50 W Bluetooth 5.0 / ADAU1701 DSP board from eBay UK, ~£31.95 (§7.3);
  - battery set (§7.4, §7.5);
  - The Mesh Company fine brass mesh, 200 × 150 mm, two grilles per sheet (§5.2);
  - Hificollective Audio Note 26 mm brass knob (gold), £24.21 ex VAT (§4.5);
  - 18 mm beech plywood, five 160 mm discs routed as rings (§6.3);
  - 3 × brass bun feet (§4.6).
- **Custom work:** rout and laminate the ply rings into a sealed box; laser-cut a brass bezel; tension and lacquer the mesh; tune the DSP (bass boost and limiter).
- **Parts cost:** £117.41 at 100 and £117.41 at 500 (driver £10.69 at the 4-off price, amplifier £31.95, battery set £31.34, mesh £6.00, knob £24.21, ply £2.73, feet £10.50).
- **Not in library:** boost converter for the amplifier supply, USB-C port, wiring, damping.
- **Main risk:** this is a dev-board stack, not a product. Check the JAB3+ supply voltage against a 3.7 V 1S2P pack (a boost converter is probably needed). The module has no radio certification for a finished product. At 171% of target, it only works with an ODM board, the route Atelier already takes. Useful as an acoustic mock-up, not as a product.

<!-- concept-parts
- {part: visaton-frs-8-8-2004--sos-electronic-eu, qty: 1, note: '80 mm full-range driver'}
- {part: wondom-jab3-2-50-w-bt-5-0-adau1701-dsp--ebay-uk, qty: 1, note: 'Bluetooth amplifier / DSP board'}
- {part: 1s2p-li-ion-pack-3-7-v-7000-mah--battery-101-uk, qty: 1, note: '1S2P battery pack'}
- {part: adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk, qty: 1, note: 'USB-C charger board'}
- {part: fine-brass-mesh--the-mesh-company-ebay-uk, size_mm: [100, 150], note: 'half a 200 × 150 mm sheet for the grille'}
- {part: audio-note-brass-knob-mwk-01-9000-9001--hificollective-uk, qty: 1, note: '26 mm gold brass knob'}
- {part: premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk, size_mm: [160, 160], count: 5, waste_pct: 30, note: 'five 160 mm discs routed as rings'}
- {part: bun-feet--cousins-uk, qty: 3, note: 'three 20 mm bun feet'}
-->

### 11. Pavilion — passive bookshelf speakers (pair)

A pair of small passive speakers in solid-edged beech-ply cabinets, each with a brass mesh front in a laser-cut brass bezel, standing on brass bun feet. They're made for vintage-style amplifiers and turntables: the mid-century hi-fi corner in miniature.

- **Library parts:**
  - 2 × Visaton FRS 8/8 (2004) from SOS Electronic, £11.37 ex VAT, £10.69 each at 4+ (§7.1; was €12.56 from Toutlehautparleur);
  - The Mesh Company fine brass mesh, 200 × 150 mm, enough for two fronts (§5.2);
  - 1 mm brass sheet, two 110 mm bezels (§4.3);
  - 18 mm beech plywood, about 0.39 m² per pair (§6.3);
  - 6 × brass bun feet (§4.6).
- **Custom work:** CNC-cut and assemble the cabinets; laser-cut, brush and lacquer the bezels; lacquer; wire the drivers.
- **Parts cost:** £68.51 per pair at 100 and £68.51 at 500 (drivers £21.38 at the 4-off price, mesh £11.99, bezels £7.74, ply £6.40, feet £21.00). The black-steel Visaton GRILLE 10 RS (£8.06, £7.63 at 3+) is a cheaper front, but the brass mesh is more on-brand.
- **Not in library:** speaker terminals, internal wire, damping.
- **Main risk:** the market. Passive speakers need the customer's own amplifier, which narrows the audience, and a single 80 mm full-range driver has limited bass. Price and position them honestly, as a "desk or bedroom hi-fi" pair.

<!-- concept-parts
- {part: visaton-frs-8-8-2004--sos-electronic-eu, qty: 2, note: 'two 80 mm full-range drivers'}
- {part: fine-brass-mesh--the-mesh-company-ebay-uk, size_mm: [200, 150], note: 'one 200 × 150 mm sheet for both fronts'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [110, 110], count: 2, note: 'two 110 mm brass bezels', option: 1}
- {part: premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk, size_mm: [650, 600], note: 'cabinets, about 0.39 m² for the pair'}
- {part: bun-feet--cousins-uk, qty: 6, note: 'six 20 mm bun feet'}
-->

## Lighting from paper and objects

### 12. Reed — paper tube column lamp

A tall, thin spiral-wound tube, lacquered in deep oxblood and pierced with a pattern of small holes. It has brass end caps and a turned beech foot, and runs on battery. It's a playful, lightweight object whose kraft-paper body is the point.

- **Library parts:**
  - Morplan 63 × 483 mm postal tube, £1.07 (£0.75 at 100+) (§1.1);
  - battery set (§7.4, §7.5);
  - 0.35 m Hi-Line LED strip (§3.5);
  - 1 mm brass sheet, two 70 mm caps (§4.3);
  - 1 × beech blank (§6.1);
  - brass ball finial (§3.1).
- **Custom work:** cut the tube; seal and lacquer it; drill the hole pattern; laser-cut the caps; turn the foot.
- **Parts cost:** £42.52 at 100 and £42.52 at 500 (battery set £31.34, strip £2.94, tube £0.75 (the 100+ break applies at both quantities), caps £3.14, blank £3.35, finial £1.00).
- **Not in library:** LED driver, USB-C port, switch, fire enclosure.
- **Main risk:** both premium feel and fire safety. A 65 gsm postal tube may dent and feel cheap, and a stiffer bespoke tube is quote-only (Essex Tube Windings). Paper can't be the fire enclosure round a Li-ion pack; this is the same issue as Atelier's wood option, and the battery needs a steel enclosure. This is the weakest concept on brand fit.

<!-- concept-parts
- {part: 1s2p-li-ion-pack-3-7-v-7000-mah--battery-101-uk, qty: 1, note: '1S2P battery pack'}
- {part: adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk, qty: 1, note: 'USB-C charger board'}
- {part: cob-led-strip-24-v-3000-k-cri-90-15-w-m-1500-lm-m--hi-line-lighting-uk, length_mm: 350, note: '0.35 m of LED strip'}
- {part: postal-tubes-with-end-caps-raja--morplan-uk, qty: 1, note: '63 × 483 mm tube, cut to 400 mm'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [70, 70], count: 2, note: 'two 70 mm brass end caps', option: 1}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 1, note: 'one blank for the foot'}
- {part: solid-brass-ball-finial-7112--in-the-light-direction-uk, qty: 1, note: 'ball finial'}
-->

### 13. Trio — candlesticks, set of three

Three solid brass stems in stepped heights on turned beech feet, each topped with a beech cup and a laser-cut brass drip plate. It's a giftable mid-century table set.

- **Library parts:**
  - 510 mm of 1/2" CZ108 polished brass tube, cut 120 / 170 / 220 mm (§1.3);
  - 6 × beech blanks, for three feet and three cups (§6.1);
  - 3 × S. Lilley M10 fixing kits, as the joining rod (§3.3);
  - 1 mm brass sheet, three 60 mm drip plates (§4.3).
- **Custom work:** turn the feet and cups; cut and brush the stems; laser-cut the drip plates; lacquer.
- **Parts cost:** £47.77 per set at 100 and £47.77 at 500 (tube £12.24, blanks £20.10, M10 kits £11.97, plates £3.46).
- **Not in library:** felt pads, packaging.
- **Main risk:** candle fire safety. The candle must sit in a non-combustible socket. A beech cup needs a brass sleeve or a spike in the drip plate, and the set needs a fire-safety assessment and labelling. The cost is also slightly over target: plain M10 studding instead of three full kits would bring it under.

<!-- concept-parts
- {part: cz108-round-tube-polished--the-metal-store-uk, length_mm: 510, note: 'three stems: 120, 170 and 220 mm'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 6, note: 'three feet and three cups'}
- {part: m10-lampholder-fixing-kit-s-lilley--light-and-power-solutions-uk, qty: 3, note: 'joining rod for each candlestick'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [60, 60], count: 3, note: 'three 60 mm drip plates', option: 1}
-->

### 14. Meridian — brass and beech bookends (pair)

Each bookend is an L of solid 1/8" × 2" brass flat bar, brushed and lacquered, carrying a turned beech sphere as a counterweight and visual full stop. Strict geometry and warm materials make a quiet mid-century object with no electrics.

- **Library parts:**
  - 2 × Noggin End CZ121 brass flat bar, 1/8" × 2" × 12", £10 each (§4.2);
  - 2 × beech blanks for the spheres (§6.1).
- **Custom work:** cut and bend the bar, with a radiused inside corner; brush and lacquer; turn the spheres; fix them with a concealed screw.
- **Parts cost:** £26.70 per pair at 100 and £26.70 at 500 (flat bar £20.00, blanks £6.70).
- **Not in library:** felt or cork base pads, packaging.
- **Main risk:** weight and grip. Each brass L weighs only about 0.4 kg, which is too light to hold a full shelf of books. They may need a longer base leg slipped under the books, or a weighted sphere, and the bend needs a sample to check for cracking at the corner.

<!-- concept-parts
- {part: brass-flat-bar-12-lengths--noggin-end-metals-stoke-on-trent, length_mm: 304.8, count: 2, note: 'two 1/8 × 2" × 12" bars, one per bookend', option: 1}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 2, note: 'two blanks for the spheres'}
-->

### 15. Beacon — small cordless bedside light

A slim 50 mm clear glass cylinder with a single line of warm LED light down its centre, on a turned beech foot, with a brass cap and a knurled aluminium knob for dimming. It's a small bedside or bathroom-shelf light, charged by USB-C.

- **Library parts:**
  - J Moncrieff 50 mm clear glass cylinder, 240 mm, from £20 (§1.5);
  - 0.2 m Hi-Line LED strip (§3.5);
  - battery set (§7.4, §7.5);
  - 1 × beech blank (§6.1);
  - 1 mm brass sheet, 60 mm cap (§4.3);
  - brass ball finial (§3.1);
  - Knobzone ridged solid aluminium knob, £3.84 (§4.5).
- **Custom work:** turn the foot with a battery pocket; laser-cut and brush the cap; mount the strip on a central spine; lacquer.
- **Parts cost:** £62.36 at 100 and £62.36 at 500 (cylinder £20.00, strip £1.68, battery set £31.34, blank £3.35, cap £1.15, finial £1.00, knob £3.84).
- **Not in library:** LED driver, dimmer, USB-C port, fire enclosure.
- **Main risk:** cost. At 137% of target for a £165 product, the battery electronics alone exceed what the price can carry. It works only on a shared custom board with Faro, or with a much smaller cell.

<!-- concept-parts
- {part: clear-glass-cylinder-shades--j-moncrieff-uk, qty: 1, note: '50 mm clear cylinder, 240 mm'}
- {part: cob-led-strip-24-v-3000-k-cri-90-15-w-m-1500-lm-m--hi-line-lighting-uk, length_mm: 200, note: '0.2 m of LED strip'}
- {part: 1s2p-li-ion-pack-3-7-v-7000-mah--battery-101-uk, qty: 1, note: '1S2P battery pack'}
- {part: adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk, qty: 1, note: 'USB-C charger board'}
- {part: beech-turning-blanks--classic-hand-tools-uk, qty: 1, note: 'one blank for the foot'}
- {part: brass-sheet-sample-small-sheet--the-metal-store-uk, size_mm: [60, 60], note: '60 mm brass cap', option: 1}
- {part: solid-brass-ball-finial-7112--in-the-light-direction-uk, qty: 1, note: 'ball finial'}
- {part: solid-metal-control-knobs--knobzone-uk, qty: 1, note: 'ridged aluminium dimmer knob', option: 1}
-->

---

## Open questions across all concepts

1. **Lampholders.** This is now partly answered; see "Oaklea kit lampholder: fitting and impact" below. The fitting is still unconfirmed.
2. **Mains compliance.** Every mains concept needs UKCA/LVD and EMC testing, which is a one-off cost not included here. It's best shared by designing two or three lamps round the same holder and flex.
3. **Volume pricing.** Almost no library supplier publishes a 500-unit price. Before choosing between concepts, ask J Moncrieff (globes, cylinders, domes) and The Metal Store (brass tube and sheet) for 100/500 prices.
4. **Custom labour.** Turning, laser cutting, brushing and lacquering are excluded. Get one quote from a UK repetition turner and one from a laser-cut-and-finish shop, then add those costs to the shortlisted concepts.

## Oaklea kit lampholder: fitting and impact

**What the listing says (checked 13 Oct 2026):** the Oaklea Brass Inline Lamp Kit (OAKLK1, £9.86) has a "brass lamp holder with a 10 mm entry". It **doesn't name the cap** (E27, E14 or BC/B22), and it **doesn't say whether the holder is solid brass or brass-plated**. Oaklea's other 10 mm holders are BC/B22, which makes BC the likely fitting, but nothing confirms it. Ask Oaklea, or buy one kit and check, before any concept depends on it.

**Seven concepts use the kit, not six.** The earlier open question left out Tambour (1). The seven are Tambour (1), Lune (2), Bell (4), Lattice (5), Halo (6), Prism (8) and Orbit (9).

**Which cap limits bulb choice in the UK:**
- **BC/B22** is the most common household cap in the UK, so it doesn't restrict bulb choice there. It does conflict with the E27 shade rings specified below, and it would limit sales in the EU, where E27 is standard.
- **E14 (SES)** is the cap that limits UK bulb choice: smaller candle and golf-ball bulbs, with less light output.
- **E27** is widely sold in the UK and matches the shade rings already specified.

| # | Concept | How it uses the holder | If it's BC/B22 (likely) | If it's E14 |
|---|---|---|---|---|
| 1 | Tambour | Hidden inside the frosted cylinder; two E27 shade rings clamp the 40 mm fitter | **Affected:** the E27 shade ring won't fit a BC holder, so it needs a BC shade ring or a different way to seat the cylinder. Bulb choice is fine. | **Affected:** limited bulbs, and the E27 ring doesn't fit. |
| 2 | Lune | Hidden inside the opal globe; the globe is held by the custom collar | Not affected. | **Affected:** limited bulbs. A small E14 bulb may also sit low in the 150 mm globe and light it unevenly. |
| 4 | Bell | Visible under the cone; E27 shade ring holds the shade | **Affected:** the E27 shade ring won't fit, so it needs a BC shade-carrier or ring. Bulb choice is fine. | **Affected:** limited bulbs, and the E27 ring doesn't fit. |
| 5 | Lattice | Hidden inside the frosted tube | Not affected. | **Affected:** limited bulbs (it needs a bulb that fits inside the 50 mm-bore tube; check either way). |
| 6 | Halo | Visible through the clear dome; the dome's 30 mm fitter is made to sit on a BC holder | Not affected: BC is what the dome needs. | **Affected:** the dome won't seat on an E14 holder, and bulb choice is limited. |
| 8 | Prism | Hidden inside the frosted acrylic tube | Not affected. | **Affected:** limited bulbs. |
| 9 | Orbit | Hidden inside the opal globe; E27 shade ring | **Affected:** the E27 shade ring won't fit. Bulb choice is fine. | **Affected:** limited bulbs (a 200 mm globe wants a larger bulb), and the E27 ring doesn't fit. |

**Solid brass:** the listing doesn't say whether the holder is solid brass or brass-plated. Under the brand rule, a plated holder can't be where it shows. That matters for **Bell** (seen under the cone) and **Halo** (seen through the clear dome). In the other five, the holder sits behind frosted or opal glass, acrylic or perforated metal.

**What to do:**
- **If the kit's holder is BC:** keep it for Lune, Lattice, Halo and Prism. Swap the E27 shade rings in Tambour, Bell and Orbit for BC equivalents, or move those three to an E27 holder (Sinolec brass E27 with 10 mm entry, library §3.3; price not shown).
- **For Bell and Halo:** use a lampholder that is stated to be solid brass, from Lampspares KIT1B or Lighting Spares KIT4 (both BC and UK-made, prices not shown), unless Oaklea confirms solid brass.
- **If the kit's holder is E14:** drop the kit for all seven concepts.
- **Costs:** the parts costs above are unchanged until the alternative holders' prices are known.

