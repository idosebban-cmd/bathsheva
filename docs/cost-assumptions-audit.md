# Cost assumptions audit: Faro

Generated 2026-10-05 20:06 UTC by Product Workbench.

**Configuration:** Best with no compromise to look and feel: a. Base spun or pressed from sheet, with a steel weight plate (Spun), b. Band cut from stock tube or rolled strip (Cut from stock tube); made in China.  
**Unit cost (midpoint) at 500 units:** £73.75.  
**Values feeding it:** 43, of which 43 are unverified.

> Every value below is a model-generated assumption unless its source says otherwise. Verify the top of the list first: it moves the unit cost most.

| # | Assumption | Seed file → entry | Seed value | Used | Source | Confidence | Verified | Impact ±25% | How to verify |
|---|---|---|---|---|---|---|---|---|---|
| 1 | China finishing cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.finishing` | 0.4–0.6 × | 0.5 × | model-generated | low | no | ±£3.87 (5.3%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 2 | China machine cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.machine` | 0.35–0.55 × | 0.45 × | model-generated | low | no | ±£3.45 (4.7%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 3 | Metal spinning machine rate | `seed/cost/process_rates.yaml` → `metal_spinning.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£2.79 (3.8%) | Send the STEP files to 2–3 spinning shops and ask for a unit price at 500 pcs; ask them to split it into material, spinning time and trimming so the hourly rate can be back-calculated. |
| 4 | Wet paint / lacquer minimum charge per part | `seed/cost/finish_rates.yaml` → `wet_lacquer.min_per_part` | £4–£8 | £3.2 | model-generated | low | no | ±£2.68 (3.6%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 5 | Aluminium 1050A (H14) density | `seed/rules/materials.yaml` → `al_1050.density_g_cm3` | 2.71 g/cm³ | 2.71 g/cm³ | model-generated | medium | no | ±£2.41 (3.3%) | Physical constant from the material datasheet; low risk. |
| 6 | Metal spinning handling time per part | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min` | 4–10 min | 7 min | model-generated | low | no | ±£2.21 (3.0%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 7 | Aluminium 1050A (H14) price | `seed/cost/material_prices.yaml` → `al_1050.gbp_per_kg` | £4–£6.5/kg | £5.25/kg | model-generated | low | no | ±£1.91 (2.6%) | Ask an aluminium stockist for a price per kg for this alloy and form (sheet discs or bar) at your quantity; sanity-check against the LME aluminium price plus a typical sheet/bar premium. |
| 8 | Metal spinning material bought per kg of part | `seed/cost/process_rates.yaml` → `metal_spinning.material_utilisation` | 1.3–1.7 × | 1.5 × | model-generated | low | no | ±£1.91 (2.6%) | Ask the shop what blank size they cut per part (disc or strip dimensions) and how much is trimmed off. |
| 9 | Freight and duty to the UK from China | `seed/cost/regions.yaml` → `china.freight_duty_pct` | 8–15 % | 11.5 % | model-generated | low | no | ±£1.90 (2.6%) | Ask a freight forwarder for a per-carton price to the UK and check the UK tariff for table lamps (commodity code 9405) for the duty rate. |
| 10 | Certified constant-current LED driver (mains) price | `seed/cost/bought_in.yaml` → `led_driver_mains` | £3–£9 | £6 | model-generated | low | no | ±£1.67 (2.3%) | Get a certified driver/adapter price at 500 pcs from a distributor, with its certificates for the target markets. |
| 11 | Mains cable with plug and inline switch (2 m, fabric) price | `seed/cost/bought_in.yaml` → `mains_cable_plug_switch` | £3–£8 | £5.5 | model-generated | low | no | ±£1.53 (2.1%) | Ask a cable-assembly maker to quote the cable with plug, switch and fabric braid at 500 pcs. |
| 12 | LED module (5–8 W, CRI 90+) price | `seed/cost/bought_in.yaml` → `led_module` | £2.5–£8 | £5.25 | model-generated | low | no | ±£1.46 (2.0%) | Get distributor prices (e.g. Mouser, Farnell, LCSC) for the LED module at 500 pcs. |
| 13 | Wet paint / lacquer cost per m² | `seed/cost/finish_rates.yaml` → `wet_lacquer.gbp_per_m2` | £40–£90/m² | £35/m² | model-generated | low | no | ±£1.20 (1.6%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 14 | Retail box with moulded-pulp inserts price | `seed/cost/bought_in.yaml` → `retail_packaging` | £2.5–£6 | £4.25 | model-generated | low | no | ±£1.18 (1.6%) | Ask a packaging supplier to quote the retail box and inserts at 500 pcs. |
| 15 | China tooling cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.tooling` | 0.3–0.5 × | 0.4 × | model-generated | low | no | ±£0.86 (1.2%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 16 | Zinc-plated steel weight plate (~0.8 kg, laser cut) price | `seed/cost/bought_in.yaml` → `steel_weight_plate` | £1.5–£4 | £2.75 | model-generated | low | no | ±£0.77 (1.0%) |  |
| 17 | Final assembly, wiring and test time | `seed/products/faro.yaml` → `cost_items (assembly minutes)` | 20 min | 20 min | model-generated | low | no | ±£0.55 (0.7%) |  |
| 18 | Assembly labour rate | `seed/cost/general.yaml` → `labour_gbp_per_hr` | £15–£25/hr | £5.875/hr | model-generated | low | no | ±£0.55 (0.7%) |  |
| 19 | China labour cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.labour` | 0.2–0.35 × | 0.275 × | model-generated | low | no | ±£0.55 (0.7%) |  |
| 20 | Metal spinning extra time per kg | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min_per_kg` | 3–8 min/kg | 5.5 min/kg | model-generated | low | no | ±£0.50 (0.7%) |  |
| 21 | Cut and polished clear tube machine rate | `seed/cost/process_rates.yaml` → `polymer_tube_cut.machine_gbp_per_hr` | £30–£45/hr | £17.62/hr | model-generated | low | no | ±£0.46 (0.6%) |  |
| 22 | Cut and polished clear tube handling time per part | `seed/cost/process_rates.yaml` → `polymer_tube_cut.cycle_min` | 3–8 min | 5.5 min | model-generated | low | no | ±£0.45 (0.6%) |  |
| 23 | Silicone gasket ring price | `seed/cost/bought_in.yaml` → `silicone_gasket` | £0.3–£1.2 | £0.75 | model-generated | low | no | ±£0.42 (0.6%) |  |
| 24 | Acrylic (PMMA) density | `seed/rules/materials.yaml` → `pmma.density_g_cm3` | 1.18 g/cm³ | 1.18 g/cm³ | model-generated | medium | no | ±£0.32 (0.4%) |  |
| 25 | Acrylic (PMMA) price | `seed/cost/material_prices.yaml` → `pmma.gbp_per_kg` | £8–£16/kg | £12/kg | model-generated | low | no | ±£0.31 (0.4%) |  |
| 26 | Cut and polished clear tube material bought per kg of part | `seed/cost/process_rates.yaml` → `polymer_tube_cut.material_utilisation` | 1.1–1.3 × | 1.2 × | model-generated | low | no | ±£0.31 (0.4%) |  |
| 27 | Tooling for base (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 28 | Tooling for main body (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 29 | Tooling for top cap (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 30 | Extrusion (cut to length) machine rate | `seed/cost/process_rates.yaml` → `extrusion.machine_gbp_per_hr` | £35–£50/hr | £19.88/hr | model-generated | low | no | ±£0.20 (0.3%) |  |
| 31 | Extrusion (cut to length) handling time per part | `seed/cost/process_rates.yaml` → `extrusion.cycle_min` | 1–3 min | 2 min | model-generated | low | no | ±£0.18 (0.3%) |  |
| 32 | M4 rivet nut (threaded insert for thin sheet) price | `seed/cost/bought_in.yaml` → `rivet_nut_m4` | £0.08–£0.25 | £0.165 | model-generated | medium | no | ±£0.14 (0.2%) |  |
| 33 | Aluminium 6063 (T5/T6) price | `seed/cost/material_prices.yaml` → `al_6063.gbp_per_kg` | £4–£6.5/kg | £5.25/kg | model-generated | low | no | ±£0.13 (0.2%) |  |
| 34 | Extrusion (cut to length) material bought per kg of part | `seed/cost/process_rates.yaml` → `extrusion.material_utilisation` | 1.05–1.15 × | 1.1 × | model-generated | low | no | ±£0.13 (0.2%) |  |
| 35 | Aluminium 6063 (T5/T6) density | `seed/rules/materials.yaml` → `al_6063.density_g_cm3` | 2.7 g/cm³ | 2.7 g/cm³ | model-generated | high | no | ±£0.13 (0.2%) |  |
| 36 | Strain-relief cable grommet price | `seed/cost/bought_in.yaml` → `cable_grommet` | £0.15–£0.6 | £0.375 | model-generated | medium | no | ±£0.10 (0.1%) |  |
| 37 | Metal spinning setup time per batch | `seed/cost/process_rates.yaml` → `metal_spinning.setup_hours` | 1–3 hours | 2 hours | model-generated | low | no | ±£0.08 (0.1%) |  |
| 38 | M4 stainless machine screw price | `seed/cost/bought_in.yaml` → `screw_m4` | £0.03–£0.1 | £0.065 | model-generated | medium | no | ±£0.05 (0.1%) |  |
| 39 | M3 stainless machine screw price | `seed/cost/bought_in.yaml` → `screw_m3` | £0.02–£0.08 | £0.05 | model-generated | medium | no | ±£0.03 (0.0%) |  |
| 40 | Cut and polished clear tube extra time per kg | `seed/cost/process_rates.yaml` → `polymer_tube_cut.cycle_min_per_kg` | 0–2 min/kg | 1 min/kg | model-generated | low | no | ±£0.01 (0.0%) |  |
| 41 | Extrusion (cut to length) setup time per batch | `seed/cost/process_rates.yaml` → `extrusion.setup_hours` | 0.5–1 hours | 0.75 hours | model-generated | low | no | ±£0.01 (0.0%) |  |
| 42 | Cut and polished clear tube setup time per batch | `seed/cost/process_rates.yaml` → `polymer_tube_cut.setup_hours` | 0.5–1 hours | 0.75 hours | model-generated | low | no | ±£0.01 (0.0%) |  |
| 43 | Extrusion (cut to length) extra time per kg | `seed/cost/process_rates.yaml` → `extrusion.cycle_min_per_kg` | 0–1 min/kg | 0.5 min/kg | model-generated | low | no | ±£0.00 (0.0%) |  |

## Notes

- Impact: each value moved ±25% with everything else at its midpoint, at 500 units (the Manufacturing tab's sensitivity method). Regional multipliers move all the inputs they scale together.
- 'Seed value' is the seed file's own low–high. 'Used' is the midpoint the model uses in this configuration, after the region scales machine, labour, tooling and finishing values.
- Densities are physical constants from material datasheets: they rank high because part weight drives material and spinning time, but they are low-risk and not a verification priority.
- Range widening for confidence affects the range only, not the midpoint, so it is not listed.
