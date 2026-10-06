# Cost assumptions audit: Faro

Generated 2026-10-06 15:11 UTC by Product Workbench.

**Configuration:** Best with no compromise to look and feel, power option A: cordless, 2 x 18650 rechargeable over USB-C: no further design changes beyond the accepted decisions; made in China.  
**Unit cost (midpoint) at 500 units:** £166.68.  
**Values feeding it:** 66, of which 66 are unverified.

> Every value below is a model-generated assumption unless its source says otherwise. Verify the top of the list first: it moves the unit cost most.

| # | Assumption | Seed file → entry | Seed value | Used | Source | Confidence | Verified | Impact ±25% | How to verify |
|---|---|---|---|---|---|---|---|---|---|
| 1 | China machine cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.machine` | 0.35–0.55 × | 0.45 × | model-generated | low | no | ±£10.89 (6.5%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 2 | Brass (CZ121 bar / CZ108 sheet) price | `seed/cost/material_prices.yaml` → `brass.gbp_per_kg` | £6.5–£10/kg | £8.25/kg | model-generated | low | no | ±£6.63 (4.0%) | Ask a brass stockist (CZ108 sheet / CZ121 bar) for a price per kg; check against the LME copper and zinc prices. |
| 3 | Brass (CZ121 bar / CZ108 sheet) density | `seed/rules/materials.yaml` → `brass.density_g_cm3` | 8.5 g/cm³ | 8.5 g/cm³ | model-generated | medium | no | ±£6.63 (4.0%) | Physical constant from the material datasheet; low risk. |
| 4 | CNC machining machine rate | `seed/cost/process_rates.yaml` → `cnc_machining.machine_gbp_per_hr` | £45–£80/hr | £29.88/hr | model-generated | low | no | ±£6.13 (3.7%) | Get an online CNC quote (e.g. Xometry) at 500 pcs and ask a local shop for its hourly machine rate. |
| 5 | China finishing cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.finishing` | 0.4–0.6 × | 0.5 × | model-generated | low | no | ±£5.62 (3.4%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 6 | CNC machining handling time per part | `seed/cost/process_rates.yaml` → `cnc_machining.cycle_min` | 3–8 min | 5.5 min | model-generated | low | no | ±£4.58 (2.7%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 7 | Freight and duty to the UK from China | `seed/cost/regions.yaml` → `china.freight_duty_pct` | 8–15 % | 11.5 % | model-generated | low | no | ±£4.30 (2.6%) | Ask a freight forwarder for a per-carton price to the UK and check the UK tariff for table lamps (commodity code 9405) for the duty rate. |
| 8 | Wet paint / lacquer minimum charge per part | `seed/cost/finish_rates.yaml` → `wet_lacquer.min_per_part` | £4–£8 | £3.2 | model-generated | low | no | ±£3.57 (2.1%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 9 | Li-ion battery pack: 2 x 18650 (3,350 mAh, branded cells), protection circuit, holder and leads price | `seed/cost/bought_in.yaml` → `battery_pack` | £7–£13 | £10 | model-generated | low | no | ±£2.79 (1.7%) | Get a distributor or supplier price at 500 pcs. |
| 10 | Metal spinning machine rate | `seed/cost/process_rates.yaml` → `metal_spinning.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£2.43 (1.5%) | Send the STEP files to 2–3 spinning shops and ask for a unit price at 500 pcs; ask them to split it into material, spinning time and trimming so the hourly rate can be back-calculated. |
| 11 | Control board: USB-C charging, 2-cell charger, 2-channel constant-current LED driver, dimmer input price | `seed/cost/bought_in.yaml` → `charge_control_board` | £5–£11 | £8 | model-generated | low | no | ±£2.23 (1.3%) | Get a certified driver/adapter price at 500 pcs from a distributor, with its certificates for the target markets. |
| 12 | Metal spinning handling time per part | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min` | 4–10 min | 7 min | model-generated | low | no | ±£2.21 (1.3%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 13 | Cut and finished glass tube machine rate | `seed/cost/process_rates.yaml` → `glass_tube_cut.machine_gbp_per_hr` | £35–£55/hr | £21.25/hr | model-generated | low | no | ±£1.72 (1.0%) | Ask a supplier for their hourly machine rate, or back-calculate it from a unit-price quote. |
| 14 | Cut and finished glass tube handling time per part | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min` | 5–12 min | 8.5 min | model-generated | low | no | ±£1.68 (1.0%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 15 | Tumble (barrel) polished, clear lacquered minimum charge per part | `seed/cost/finish_rates.yaml` → `tumble_polish.min_per_part` | £0.8–£2.5 | £0.91 | model-generated | low | no | ±£1.52 (0.9%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 16 | China tooling cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.tooling` | 0.3–0.5 × | 0.4 × | model-generated | low | no | ±£1.44 (0.9%) |  |
| 17 | Masked second-colour lacquer section (e.g. a red lower tower) price | `seed/cost/bought_in.yaml` → `masked_stripe` | £3–£7 | £5 | model-generated | low | no | ±£1.39 (0.8%) |  |
| 18 | Laser-cut 5 arched windows in the spun tower (5-axis laser or fixture), deburr price | `seed/cost/bought_in.yaml` → `window_laser_cut` | £2.5–£7 | £4.75 | model-generated | low | no | ±£1.32 (0.8%) |  |
| 19 | CNC machining time per cm³ cut away | `seed/cost/process_rates.yaml` → `cnc_machining.min_per_cm3_removed` | 0.01–0.04 min/cm³ | 0.025 min/cm³ | model-generated | low | no | ±£1.28 (0.8%) |  |
| 20 | Retail box with moulded-pulp inserts price | `seed/cost/bought_in.yaml` → `retail_packaging` | £2.5–£6 | £4.25 | model-generated | low | no | ±£1.18 (0.7%) |  |
| 21 | Zinc-plated steel weight plate (laser cut, ~0.4 kg, battery cut-out, tapped holes) price | `seed/cost/bought_in.yaml` → `steel_weight_plate` | £2–£5 | £3.5 | model-generated | low | no | ±£0.98 (0.6%) |  |
| 22 | Tower light: 4 LED filament strips (2700 K, ~0.8 W total) on an aluminium spine price | `seed/cost/bought_in.yaml` → `tower_light` | £2–£5 | £3.5 | model-generated | low | no | ±£0.98 (0.6%) |  |
| 23 | Borosilicate glass density | `seed/rules/materials.yaml` → `borosilicate.density_g_cm3` | 2.23 g/cm³ | 2.23 g/cm³ | model-generated | medium | no | ±£0.93 (0.6%) |  |
| 24 | Borosilicate glass price | `seed/cost/material_prices.yaml` → `borosilicate.gbp_per_kg` | £10–£25/kg | £17.5/kg | model-generated | low | no | ±£0.91 (0.5%) |  |
| 25 | Cut and finished glass tube material bought per kg of part | `seed/cost/process_rates.yaml` → `glass_tube_cut.material_utilisation` | 1.1–1.3 × | 1.2 × | model-generated | low | no | ±£0.91 (0.5%) |  |
| 26 | Lantern LED: 1.5 W warm white (2700 K, CRI 90+) board on an aluminium spreader price | `seed/cost/bought_in.yaml` → `led_module_lantern` | £1.5–£4 | £2.75 | model-generated | low | no | ±£0.77 (0.5%) |  |
| 27 | Volume price as a share of small-quantity price (merchant material) | `project cost settings (edited by you)` → `volume discount: merchant_material` | 0.5–0.7 × | 0.6 × | user assumption (Oct 2026) | medium | no | ±£0.72 (0.4%) |  |
| 28 | Aluminium 6061 (T6) price | `seed/cost/material_prices.yaml` → `al_6061.gbp_per_kg` | £11.5–£18.6/kg | £15.05/kg | Single UK bars, 6082-T6 as the UK proxy for 6061: Cromwell 4in x 24in 6082 £154 ex VAT / 13.3 kg = £11.5/kg (https://cromwell.co.uk/shop/materials-maintenance-and-standard-parts/engineering-materials/4in-x-24in-aluminium-round-bar-grade-6082-1-pce/p/IND4732376K); RS PRO 4in x 24in bar £248.85 ex VAT / 13.3 kg = £18.6/kg (https://uk.rs-online.com/web/p/metal-bars-metal-rods/0495231). Cross-check: EU 6061-T6 contract $2.30-3.10/lb = £3.8-5.2/kg (https://www.mwalloys.com/es/aluminum-alloy-6061-price-per-pound-2026/). accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked). | medium | no | ±£0.72 (0.4%) |  |
| 29 | Aluminium 6061 (T6) density | `seed/rules/materials.yaml` → `al_6061.density_g_cm3` | 2.7 g/cm³ | 2.7 g/cm³ | model-generated | high | no | ±£0.72 (0.4%) |  |
| 30 | Final assembly, bonding, wiring and test time | `seed/products/faro.yaml` → `cost_items (assembly minutes)` | 24 min | 24 min | model-generated | low | no | ±£0.66 (0.4%) |  |
| 31 | Assembly labour rate | `seed/cost/general.yaml` → `labour_gbp_per_hr` | £15–£25/hr | £5.875/hr | model-generated | low | no | ±£0.66 (0.4%) |  |
| 32 | China labour cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.labour` | 0.2–0.35 × | 0.275 × | model-generated | low | no | ±£0.66 (0.4%) |  |
| 33 | Photo-etched brass sheet (formed after etching) machine rate | `seed/cost/process_rates.yaml` → `photo_etching.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£0.60 (0.4%) |  |
| 34 | Bottom plate, laser-cut 2 mm aluminium, countersunk, black lacquer price | `seed/cost/bought_in.yaml` → `bottom_plate` | £1.2–£3 | £2.1 | model-generated | low | no | ±£0.59 (0.4%) |  |
| 35 | Photo-etched brass sheet (formed after etching) handling time per part | `seed/cost/process_rates.yaml` → `photo_etching.cycle_min` | 1.5–4 min | 2.75 min | model-generated | low | no | ±£0.58 (0.3%) |  |
| 36 | Aluminium 1050A (H14) density | `seed/rules/materials.yaml` → `al_1050.density_g_cm3` | 2.71 g/cm³ | 2.71 g/cm³ | model-generated | medium | no | ±£0.58 (0.3%) |  |
| 37 | USB-C charging cable price | `seed/cost/bought_in.yaml` → `usb_c_cable` | £1–£3 | £2 | model-generated | low | no | ±£0.56 (0.3%) |  |
| 38 | Frosted / diffused minimum charge per part | `seed/cost/finish_rates.yaml` → `frosted.min_per_part` | £2–£5 | £1.9 | model-generated | low | no | ±£0.53 (0.3%) |  |
| 39 | Metal spinning material bought per kg of part | `seed/cost/process_rates.yaml` → `metal_spinning.material_utilisation` | 1.3–1.7 × | 1.5 × | model-generated | low | no | ±£0.43 (0.3%) |  |
| 40 | Silicone gasket ring price | `seed/cost/bought_in.yaml` → `silicone_gasket` | £0.3–£1.2 | £0.75 | model-generated | low | no | ±£0.42 (0.3%) |  |
| 41 | Slim rotary potentiometer with switch (9 mm class, D-shaft) and curved spacer washer price | `seed/cost/bought_in.yaml` → `dimmer_rotary` | £0.6–£1.8 | £1.2 | model-generated | low | no | ±£0.33 (0.2%) |  |
| 42 | Tooling for base (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.2%) |  |
| 43 | Tooling for gallery railing (photo-etched brass sheet (formed after etching)) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.2%) |  |
| 44 | Tooling for cap (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.2%) |  |
| 45 | Tooling for nameplate (photo-etched brass sheet (formed after etching)) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.2%) |  |
| 46 | Tooling for tower (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.2%) |  |
| 47 | Exchange rate (USD per GBP) | `seed/cost/commodities.yaml` → `usd_per_gbp` | 1.3224–1.3241 USD/GBP | 1.323 USD/GBP | GBP/USD 1.32406 on 2 Oct 2026 and 1.3224 on 5 Oct 2026 (https://www.mtfxgroup.com/tools/historical-currency-exchange-rates/gbp-to-usd-rate/, https://www.fxstreet.com/news/british-pound-slides-as-france-fiscal-shock-lifts-the-us-dollar-202610051636); accessed 2026-10-05 | high | no | ±£0.28 (0.2%) |  |
| 48 | Felt pad laminated to a 0.4 mm steel disc price | `seed/cost/bought_in.yaml` → `felt_steel_disc` | £0.5–£1.5 | £1 | model-generated | low | no | ±£0.28 (0.2%) |  |
| 49 | CNC machining setup time per batch | `seed/cost/process_rates.yaml` → `cnc_machining.setup_hours` | 1.5–4 hours | 2.75 hours | model-generated | low | no | ±£0.27 (0.2%) |  |
| 50 | LME aluminium cash price | `seed/cost/commodities.yaml` → `lme_aluminium_cash` | 3110–3129 USD/t | 3,120 USD/t | LME Al cash $3,119.5/t on 1 Oct 2026 and $3,110/t official cash on 2 Oct 2026 (https://www.alcircle.com/news/lme-aluminium-price-drops-2-62-as-stocks-remain-stable-at-241-375t-on-october-1-121399); $3,129/t on 5 Oct 2026 (https://tradingeconomics.com/commodity/aluminum); accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked) | high | no | ±£0.26 (0.2%) |  |
| 51 | M2.5 hex standoff, aluminium (bottom plate to weight plate) price | `seed/cost/bought_in.yaml` → `standoff_m25` | £0.08–£0.25 | £0.165 | model-generated | low | no | ±£0.18 (0.1%) |  |
| 52 | Structural adhesive (tower, gallery, frame and spigot bonds), per lamp price | `seed/cost/bought_in.yaml` → `structural_adhesive` | £0.3–£1 | £0.65 | model-generated | low | no | ±£0.18 (0.1%) |  |
| 53 | Sheet / spinning-circle conversion premium over metal (1050/3003/5052) | `seed/cost/commodities.yaml` → `aluminium_sheet_conversion` | 1–2 GBP/kg | 1.5 GBP/kg | model-generated | low | no | ±£0.16 (0.1%) |  |
| 54 | Metal spinning extra time per kg | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min_per_kg` | 3–8 min/kg | 5.5 min/kg | model-generated | low | no | ±£0.15 (0.1%) |  |
| 55 | N52 magnet disc 6 x 2 mm price | `seed/cost/bought_in.yaml` → `magnet_6x2` | £0.05–£0.15 | £0.1 | model-generated | low | no | ±£0.11 (0.1%) |  |
| 56 | Metal spinning setup time per batch | `seed/cost/process_rates.yaml` → `metal_spinning.setup_hours` | 1–3 hours | 2 hours | model-generated | low | no | ±£0.08 (0.0%) |  |
| 57 | Photo-etched brass sheet (formed after etching) material bought per kg of part | `seed/cost/process_rates.yaml` → `photo_etching.material_utilisation` | 2–3.5 × | 2.75 × | model-generated | low | no | ±£0.07 (0.0%) |  |
| 58 | M2.5 x 6 countersunk screw, hex socket, black price | `seed/cost/bought_in.yaml` → `screw_m25_cs` | £0.02–£0.08 | £0.05 | model-generated | low | no | ±£0.06 (0.0%) |  |
| 59 | M3 stainless machine screw price | `seed/cost/bought_in.yaml` → `screw_m3` | £0.02–£0.08 | £0.05 | model-generated | medium | no | ±£0.04 (0.0%) |  |
| 60 | Photo-etched brass sheet (formed after etching) setup time per batch | `seed/cost/process_rates.yaml` → `photo_etching.setup_hours` | 0.5–1.5 hours | 1 hours | model-generated | low | no | ±£0.03 (0.0%) |  |
| 61 | Cut and finished glass tube extra time per kg | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min_per_kg` | 0–3 min/kg | 1.5 min/kg | model-generated | low | no | ±£0.02 (0.0%) |  |
| 62 | Cut and finished glass tube setup time per batch | `seed/cost/process_rates.yaml` → `glass_tube_cut.setup_hours` | 0.5–1 hours | 0.75 hours | model-generated | low | no | ±£0.02 (0.0%) |  |
| 63 | Aluminium premium / domestic price difference, China | `seed/cost/commodities.yaml` → `aluminium_premium_china` | 0–200 USD/t | 100 USD/t | model-generated | low | no | ±£0.01 (0.0%) |  |
| 64 | Frosted / diffused cost per m² | `seed/cost/finish_rates.yaml` → `frosted.gbp_per_m2` | £15–£40/m² | £15/m² | model-generated | low | no | ±£0.00 (0.0%) |  |
| 65 | Tumble (barrel) polished, clear lacquered cost per m² | `seed/cost/finish_rates.yaml` → `tumble_polish.gbp_per_m2` | £20–£60/m² | £22/m² | model-generated | low | no | ±£0.00 (0.0%) |  |
| 66 | Wet paint / lacquer cost per m² | `seed/cost/finish_rates.yaml` → `wet_lacquer.gbp_per_m2` | £40–£90/m² | £35/m² | model-generated | low | no | ±£0.00 (0.0%) |  |

## Researched prices vs volume-adjusted prices

Unit cost at 500 with every price at its researched basis (no volume adjustment): £170.56; volume-adjusted: £166.68.

| Price | Researched (raw) | Basis | Basis qty | Adjustment | Used at 500 | Used at 2,000 |
|---|---|---|---|---|---|---|
| Aluminium 1050A (H14) price | £7.7–£9.2/kg | retail | 1 | trade basis (LME + premium + sheet conversion) | £3.93/kg | £3.93/kg |
| Brass (CZ121 bar / CZ108 sheet) price | £6.5–£10/kg | model estimate | — | none | £8.25/kg | £8.25/kg |
| Aluminium 6061 (T6) price | £11.5–£18.6/kg | retail | 1 | volume discount | £9.03/kg | £9.03/kg |
| Borosilicate glass price | £10–£25/kg | model estimate | — | none | £17.50/kg | £17.50/kg |
| Lantern LED: 1.5 W warm white (2700 K, CRI 90+) board on an aluminium spreader price | £1.5–£4 | model estimate | — | none | £2.75 | £2.75 |
| Tower light: 4 LED filament strips (2700 K, ~0.8 W total) on an aluminium spine price | £2–£5 | model estimate | — | none | £3.50 | £3.50 |
| Li-ion battery pack: 2 x 18650 (3,350 mAh, branded cells), protection circuit, holder and leads price | £7–£13 | model estimate | — | none | £10.00 | £10.00 |
| Control board: USB-C charging, 2-cell charger, 2-channel constant-current LED driver, dimmer input price | £5–£11 | model estimate | — | none | £8.00 | £8.00 |
| USB-C charging cable price | £1–£3 | model estimate | — | none | £2.00 | £2.00 |
| Slim rotary potentiometer with switch (9 mm class, D-shaft) and curved spacer washer price | £0.6–£1.8 | model estimate | — | none | £1.20 | £1.20 |
| Laser-cut 5 arched windows in the spun tower (5-axis laser or fixture), deburr price | £2.5–£7 | model estimate | — | none | £4.75 | £4.75 |
| Masked second-colour lacquer section (e.g. a red lower tower) price | £3–£7 | model estimate | — | none | £5.00 | £5.00 |
| Bottom plate, laser-cut 2 mm aluminium, countersunk, black lacquer price | £1.2–£3 | model estimate | — | none | £2.10 | £2.10 |
| Felt pad laminated to a 0.4 mm steel disc price | £0.5–£1.5 | model estimate | — | none | £1.00 | £1.00 |
| N52 magnet disc 6 x 2 mm price | £0.05–£0.15 | model estimate | — | none | £0.10 | £0.10 |
| M2.5 x 6 countersunk screw, hex socket, black price | £0.02–£0.08 | model estimate | — | none | £0.05 | £0.05 |
| M2.5 hex standoff, aluminium (bottom plate to weight plate) price | £0.08–£0.25 | model estimate | — | none | £0.17 | £0.17 |
| M3 stainless machine screw price | £0.02–£0.08 | model estimate | — | none | £0.05 | £0.05 |
| Silicone gasket ring price | £0.3–£1.2 | model estimate | — | none | £0.75 | £0.75 |
| Structural adhesive (tower, gallery, frame and spigot bonds), per lamp price | £0.3–£1 | model estimate | — | none | £0.65 | £0.65 |
| Retail box with moulded-pulp inserts price | £2.5–£6 | model estimate | — | none | £4.25 | £4.25 |
| Zinc-plated steel weight plate (laser cut, ~0.4 kg, battery cut-out, tapped holes) price | £2–£5 | model estimate | — | none | £3.50 | £3.50 |

## Notes

- Impact: each value moved ±25% with everything else at its midpoint, at 500 units (the Manufacturing tab's sensitivity method). Regional multipliers move all the inputs they scale together.
- 'Seed value' is the seed file's own low–high. 'Used' is the midpoint the model uses in this configuration, after the region scales machine, labour, tooling and finishing values.
- Densities are physical constants from material datasheets: they rank high because part weight drives material and spinning time, but they are low-risk and not a verification priority.
- Range widening for confidence affects the range only, not the midpoint, so it is not listed.


---

# Cost assumptions audit: Faro

Generated 2026-10-06 15:11 UTC by Product Workbench.

**Configuration:** Best with no compromise to look and feel, power option A: cordless, 2 x 18650 rechargeable over USB-C: no further design changes beyond the accepted decisions; made in China.  
**Unit cost (midpoint) at 2000 units:** £161.19.  
**Values feeding it:** 66, of which 66 are unverified.

> Every value below is a model-generated assumption unless its source says otherwise. Verify the top of the list first: it moves the unit cost most.

| # | Assumption | Seed file → entry | Seed value | Used | Source | Confidence | Verified | Impact ±25% | How to verify |
|---|---|---|---|---|---|---|---|---|---|
| 1 | China machine cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.machine` | 0.35–0.55 × | 0.45 × | model-generated | low | no | ±£10.59 (6.6%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 2 | Brass (CZ121 bar / CZ108 sheet) price | `seed/cost/material_prices.yaml` → `brass.gbp_per_kg` | £6.5–£10/kg | £8.25/kg | model-generated | low | no | ±£6.63 (4.1%) | Ask a brass stockist (CZ108 sheet / CZ121 bar) for a price per kg; check against the LME copper and zinc prices. |
| 3 | Brass (CZ121 bar / CZ108 sheet) density | `seed/rules/materials.yaml` → `brass.density_g_cm3` | 8.5 g/cm³ | 8.5 g/cm³ | model-generated | medium | no | ±£6.63 (4.1%) | Physical constant from the material datasheet; low risk. |
| 4 | CNC machining machine rate | `seed/cost/process_rates.yaml` → `cnc_machining.machine_gbp_per_hr` | £45–£80/hr | £29.88/hr | model-generated | low | no | ±£5.92 (3.7%) | Get an online CNC quote (e.g. Xometry) at 500 pcs and ask a local shop for its hourly machine rate. |
| 5 | China finishing cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.finishing` | 0.4–0.6 × | 0.5 × | model-generated | low | no | ±£5.62 (3.5%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 6 | CNC machining handling time per part | `seed/cost/process_rates.yaml` → `cnc_machining.cycle_min` | 3–8 min | 5.5 min | model-generated | low | no | ±£4.58 (2.8%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 7 | Freight and duty to the UK from China | `seed/cost/regions.yaml` → `china.freight_duty_pct` | 8–15 % | 11.5 % | model-generated | low | no | ±£4.16 (2.6%) | Ask a freight forwarder for a per-carton price to the UK and check the UK tariff for table lamps (commodity code 9405) for the duty rate. |
| 8 | Wet paint / lacquer minimum charge per part | `seed/cost/finish_rates.yaml` → `wet_lacquer.min_per_part` | £4–£8 | £3.2 | model-generated | low | no | ±£3.57 (2.2%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 9 | Li-ion battery pack: 2 x 18650 (3,350 mAh, branded cells), protection circuit, holder and leads price | `seed/cost/bought_in.yaml` → `battery_pack` | £7–£13 | £10 | model-generated | low | no | ±£2.79 (1.7%) | Get a distributor or supplier price at 500 pcs. |
| 10 | Metal spinning machine rate | `seed/cost/process_rates.yaml` → `metal_spinning.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£2.38 (1.5%) | Send the STEP files to 2–3 spinning shops and ask for a unit price at 500 pcs; ask them to split it into material, spinning time and trimming so the hourly rate can be back-calculated. |
| 11 | Control board: USB-C charging, 2-cell charger, 2-channel constant-current LED driver, dimmer input price | `seed/cost/bought_in.yaml` → `charge_control_board` | £5–£11 | £8 | model-generated | low | no | ±£2.23 (1.4%) | Get a certified driver/adapter price at 500 pcs from a distributor, with its certificates for the target markets. |
| 12 | Metal spinning handling time per part | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min` | 4–10 min | 7 min | model-generated | low | no | ±£2.21 (1.4%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 13 | Cut and finished glass tube machine rate | `seed/cost/process_rates.yaml` → `glass_tube_cut.machine_gbp_per_hr` | £35–£55/hr | £21.25/hr | model-generated | low | no | ±£1.71 (1.1%) | Ask a supplier for their hourly machine rate, or back-calculate it from a unit-price quote. |
| 14 | Cut and finished glass tube handling time per part | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min` | 5–12 min | 8.5 min | model-generated | low | no | ±£1.68 (1.0%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 15 | Tumble (barrel) polished, clear lacquered minimum charge per part | `seed/cost/finish_rates.yaml` → `tumble_polish.min_per_part` | £0.8–£2.5 | £0.91 | model-generated | low | no | ±£1.52 (0.9%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 16 | Masked second-colour lacquer section (e.g. a red lower tower) price | `seed/cost/bought_in.yaml` → `masked_stripe` | £3–£7 | £5 | model-generated | low | no | ±£1.39 (0.9%) |  |
| 17 | Laser-cut 5 arched windows in the spun tower (5-axis laser or fixture), deburr price | `seed/cost/bought_in.yaml` → `window_laser_cut` | £2.5–£7 | £4.75 | model-generated | low | no | ±£1.32 (0.8%) |  |
| 18 | CNC machining time per cm³ cut away | `seed/cost/process_rates.yaml` → `cnc_machining.min_per_cm3_removed` | 0.01–0.04 min/cm³ | 0.025 min/cm³ | model-generated | low | no | ±£1.28 (0.8%) |  |
| 19 | Retail box with moulded-pulp inserts price | `seed/cost/bought_in.yaml` → `retail_packaging` | £2.5–£6 | £4.25 | model-generated | low | no | ±£1.18 (0.7%) |  |
| 20 | Zinc-plated steel weight plate (laser cut, ~0.4 kg, battery cut-out, tapped holes) price | `seed/cost/bought_in.yaml` → `steel_weight_plate` | £2–£5 | £3.5 | model-generated | low | no | ±£0.98 (0.6%) |  |
| 21 | Tower light: 4 LED filament strips (2700 K, ~0.8 W total) on an aluminium spine price | `seed/cost/bought_in.yaml` → `tower_light` | £2–£5 | £3.5 | model-generated | low | no | ±£0.98 (0.6%) |  |
| 22 | Borosilicate glass density | `seed/rules/materials.yaml` → `borosilicate.density_g_cm3` | 2.23 g/cm³ | 2.23 g/cm³ | model-generated | medium | no | ±£0.93 (0.6%) |  |
| 23 | Borosilicate glass price | `seed/cost/material_prices.yaml` → `borosilicate.gbp_per_kg` | £10–£25/kg | £17.5/kg | model-generated | low | no | ±£0.91 (0.6%) |  |
| 24 | Cut and finished glass tube material bought per kg of part | `seed/cost/process_rates.yaml` → `glass_tube_cut.material_utilisation` | 1.1–1.3 × | 1.2 × | model-generated | low | no | ±£0.91 (0.6%) |  |
| 25 | Lantern LED: 1.5 W warm white (2700 K, CRI 90+) board on an aluminium spreader price | `seed/cost/bought_in.yaml` → `led_module_lantern` | £1.5–£4 | £2.75 | model-generated | low | no | ±£0.77 (0.5%) |  |
| 26 | Volume price as a share of small-quantity price (merchant material) | `project cost settings (edited by you)` → `volume discount: merchant_material` | 0.5–0.7 × | 0.6 × | user assumption (Oct 2026) | medium | no | ±£0.72 (0.4%) |  |
| 27 | Aluminium 6061 (T6) price | `seed/cost/material_prices.yaml` → `al_6061.gbp_per_kg` | £11.5–£18.6/kg | £15.05/kg | Single UK bars, 6082-T6 as the UK proxy for 6061: Cromwell 4in x 24in 6082 £154 ex VAT / 13.3 kg = £11.5/kg (https://cromwell.co.uk/shop/materials-maintenance-and-standard-parts/engineering-materials/4in-x-24in-aluminium-round-bar-grade-6082-1-pce/p/IND4732376K); RS PRO 4in x 24in bar £248.85 ex VAT / 13.3 kg = £18.6/kg (https://uk.rs-online.com/web/p/metal-bars-metal-rods/0495231). Cross-check: EU 6061-T6 contract $2.30-3.10/lb = £3.8-5.2/kg (https://www.mwalloys.com/es/aluminum-alloy-6061-price-per-pound-2026/). accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked). | medium | no | ±£0.72 (0.4%) |  |
| 28 | Aluminium 6061 (T6) density | `seed/rules/materials.yaml` → `al_6061.density_g_cm3` | 2.7 g/cm³ | 2.7 g/cm³ | model-generated | high | no | ±£0.72 (0.4%) |  |
| 29 | Final assembly, bonding, wiring and test time | `seed/products/faro.yaml` → `cost_items (assembly minutes)` | 24 min | 24 min | model-generated | low | no | ±£0.66 (0.4%) |  |
| 30 | Assembly labour rate | `seed/cost/general.yaml` → `labour_gbp_per_hr` | £15–£25/hr | £5.875/hr | model-generated | low | no | ±£0.66 (0.4%) |  |
| 31 | China labour cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.labour` | 0.2–0.35 × | 0.275 × | model-generated | low | no | ±£0.66 (0.4%) |  |
| 32 | Bottom plate, laser-cut 2 mm aluminium, countersunk, black lacquer price | `seed/cost/bought_in.yaml` → `bottom_plate` | £1.2–£3 | £2.1 | model-generated | low | no | ±£0.59 (0.4%) |  |
| 33 | Photo-etched brass sheet (formed after etching) handling time per part | `seed/cost/process_rates.yaml` → `photo_etching.cycle_min` | 1.5–4 min | 2.75 min | model-generated | low | no | ±£0.58 (0.4%) |  |
| 34 | Photo-etched brass sheet (formed after etching) machine rate | `seed/cost/process_rates.yaml` → `photo_etching.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£0.58 (0.4%) |  |
| 35 | Aluminium 1050A (H14) density | `seed/rules/materials.yaml` → `al_1050.density_g_cm3` | 2.71 g/cm³ | 2.71 g/cm³ | model-generated | medium | no | ±£0.58 (0.4%) |  |
| 36 | USB-C charging cable price | `seed/cost/bought_in.yaml` → `usb_c_cable` | £1–£3 | £2 | model-generated | low | no | ±£0.56 (0.3%) |  |
| 37 | Frosted / diffused minimum charge per part | `seed/cost/finish_rates.yaml` → `frosted.min_per_part` | £2–£5 | £1.9 | model-generated | low | no | ±£0.53 (0.3%) |  |
| 38 | Metal spinning material bought per kg of part | `seed/cost/process_rates.yaml` → `metal_spinning.material_utilisation` | 1.3–1.7 × | 1.5 × | model-generated | low | no | ±£0.43 (0.3%) |  |
| 39 | Silicone gasket ring price | `seed/cost/bought_in.yaml` → `silicone_gasket` | £0.3–£1.2 | £0.75 | model-generated | low | no | ±£0.42 (0.3%) |  |
| 40 | China tooling cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.tooling` | 0.3–0.5 × | 0.4 × | model-generated | low | no | ±£0.36 (0.2%) |  |
| 41 | Slim rotary potentiometer with switch (9 mm class, D-shaft) and curved spacer washer price | `seed/cost/bought_in.yaml` → `dimmer_rotary` | £0.6–£1.8 | £1.2 | model-generated | low | no | ±£0.33 (0.2%) |  |
| 42 | Exchange rate (USD per GBP) | `seed/cost/commodities.yaml` → `usd_per_gbp` | 1.3224–1.3241 USD/GBP | 1.323 USD/GBP | GBP/USD 1.32406 on 2 Oct 2026 and 1.3224 on 5 Oct 2026 (https://www.mtfxgroup.com/tools/historical-currency-exchange-rates/gbp-to-usd-rate/, https://www.fxstreet.com/news/british-pound-slides-as-france-fiscal-shock-lifts-the-us-dollar-202610051636); accessed 2026-10-05 | high | no | ±£0.28 (0.2%) |  |
| 43 | Felt pad laminated to a 0.4 mm steel disc price | `seed/cost/bought_in.yaml` → `felt_steel_disc` | £0.5–£1.5 | £1 | model-generated | low | no | ±£0.28 (0.2%) |  |
| 44 | LME aluminium cash price | `seed/cost/commodities.yaml` → `lme_aluminium_cash` | 3110–3129 USD/t | 3,120 USD/t | LME Al cash $3,119.5/t on 1 Oct 2026 and $3,110/t official cash on 2 Oct 2026 (https://www.alcircle.com/news/lme-aluminium-price-drops-2-62-as-stocks-remain-stable-at-241-375t-on-october-1-121399); $3,129/t on 5 Oct 2026 (https://tradingeconomics.com/commodity/aluminum); accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked) | high | no | ±£0.26 (0.2%) |  |
| 45 | M2.5 hex standoff, aluminium (bottom plate to weight plate) price | `seed/cost/bought_in.yaml` → `standoff_m25` | £0.08–£0.25 | £0.165 | model-generated | low | no | ±£0.18 (0.1%) |  |
| 46 | Structural adhesive (tower, gallery, frame and spigot bonds), per lamp price | `seed/cost/bought_in.yaml` → `structural_adhesive` | £0.3–£1 | £0.65 | model-generated | low | no | ±£0.18 (0.1%) |  |
| 47 | Sheet / spinning-circle conversion premium over metal (1050/3003/5052) | `seed/cost/commodities.yaml` → `aluminium_sheet_conversion` | 1–2 GBP/kg | 1.5 GBP/kg | model-generated | low | no | ±£0.16 (0.1%) |  |
| 48 | Metal spinning extra time per kg | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min_per_kg` | 3–8 min/kg | 5.5 min/kg | model-generated | low | no | ±£0.15 (0.1%) |  |
| 49 | N52 magnet disc 6 x 2 mm price | `seed/cost/bought_in.yaml` → `magnet_6x2` | £0.05–£0.15 | £0.1 | model-generated | low | no | ±£0.11 (0.1%) |  |
| 50 | CNC machining setup time per batch | `seed/cost/process_rates.yaml` → `cnc_machining.setup_hours` | 1.5–4 hours | 2.75 hours | model-generated | low | no | ±£0.07 (0.0%) |  |
| 51 | Tooling for base (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.07 (0.0%) |  |
| 52 | Tooling for gallery railing (photo-etched brass sheet (formed after etching)) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.07 (0.0%) |  |
| 53 | Tooling for cap (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.07 (0.0%) |  |
| 54 | Tooling for nameplate (photo-etched brass sheet (formed after etching)) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.07 (0.0%) |  |
| 55 | Tooling for tower (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.07 (0.0%) |  |
| 56 | Photo-etched brass sheet (formed after etching) material bought per kg of part | `seed/cost/process_rates.yaml` → `photo_etching.material_utilisation` | 2–3.5 × | 2.75 × | model-generated | low | no | ±£0.07 (0.0%) |  |
| 57 | M2.5 x 6 countersunk screw, hex socket, black price | `seed/cost/bought_in.yaml` → `screw_m25_cs` | £0.02–£0.08 | £0.05 | model-generated | low | no | ±£0.06 (0.0%) |  |
| 58 | M3 stainless machine screw price | `seed/cost/bought_in.yaml` → `screw_m3` | £0.02–£0.08 | £0.05 | model-generated | medium | no | ±£0.04 (0.0%) |  |
| 59 | Cut and finished glass tube extra time per kg | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min_per_kg` | 0–3 min/kg | 1.5 min/kg | model-generated | low | no | ±£0.02 (0.0%) |  |
| 60 | Metal spinning setup time per batch | `seed/cost/process_rates.yaml` → `metal_spinning.setup_hours` | 1–3 hours | 2 hours | model-generated | low | no | ±£0.02 (0.0%) |  |
| 61 | Aluminium premium / domestic price difference, China | `seed/cost/commodities.yaml` → `aluminium_premium_china` | 0–200 USD/t | 100 USD/t | model-generated | low | no | ±£0.01 (0.0%) |  |
| 62 | Photo-etched brass sheet (formed after etching) setup time per batch | `seed/cost/process_rates.yaml` → `photo_etching.setup_hours` | 0.5–1.5 hours | 1 hours | model-generated | low | no | ±£0.01 (0.0%) |  |
| 63 | Frosted / diffused cost per m² | `seed/cost/finish_rates.yaml` → `frosted.gbp_per_m2` | £15–£40/m² | £15/m² | model-generated | low | no | ±£0.00 (0.0%) |  |
| 64 | Tumble (barrel) polished, clear lacquered cost per m² | `seed/cost/finish_rates.yaml` → `tumble_polish.gbp_per_m2` | £20–£60/m² | £22/m² | model-generated | low | no | ±£0.00 (0.0%) |  |
| 65 | Wet paint / lacquer cost per m² | `seed/cost/finish_rates.yaml` → `wet_lacquer.gbp_per_m2` | £40–£90/m² | £35/m² | model-generated | low | no | ±£0.00 (0.0%) |  |
| 66 | Cut and finished glass tube setup time per batch | `seed/cost/process_rates.yaml` → `glass_tube_cut.setup_hours` | 0.5–1 hours | 0.75 hours | model-generated | low | no | ±£0.00 (0.0%) |  |

## Researched prices vs volume-adjusted prices

Unit cost at 2000 with every price at its researched basis (no volume adjustment): £165.08; volume-adjusted: £161.19.

| Price | Researched (raw) | Basis | Basis qty | Adjustment | Used at 500 | Used at 2,000 |
|---|---|---|---|---|---|---|
| Aluminium 1050A (H14) price | £7.7–£9.2/kg | retail | 1 | trade basis (LME + premium + sheet conversion) | £3.93/kg | £3.93/kg |
| Brass (CZ121 bar / CZ108 sheet) price | £6.5–£10/kg | model estimate | — | none | £8.25/kg | £8.25/kg |
| Aluminium 6061 (T6) price | £11.5–£18.6/kg | retail | 1 | volume discount | £9.03/kg | £9.03/kg |
| Borosilicate glass price | £10–£25/kg | model estimate | — | none | £17.50/kg | £17.50/kg |
| Lantern LED: 1.5 W warm white (2700 K, CRI 90+) board on an aluminium spreader price | £1.5–£4 | model estimate | — | none | £2.75 | £2.75 |
| Tower light: 4 LED filament strips (2700 K, ~0.8 W total) on an aluminium spine price | £2–£5 | model estimate | — | none | £3.50 | £3.50 |
| Li-ion battery pack: 2 x 18650 (3,350 mAh, branded cells), protection circuit, holder and leads price | £7–£13 | model estimate | — | none | £10.00 | £10.00 |
| Control board: USB-C charging, 2-cell charger, 2-channel constant-current LED driver, dimmer input price | £5–£11 | model estimate | — | none | £8.00 | £8.00 |
| USB-C charging cable price | £1–£3 | model estimate | — | none | £2.00 | £2.00 |
| Slim rotary potentiometer with switch (9 mm class, D-shaft) and curved spacer washer price | £0.6–£1.8 | model estimate | — | none | £1.20 | £1.20 |
| Laser-cut 5 arched windows in the spun tower (5-axis laser or fixture), deburr price | £2.5–£7 | model estimate | — | none | £4.75 | £4.75 |
| Masked second-colour lacquer section (e.g. a red lower tower) price | £3–£7 | model estimate | — | none | £5.00 | £5.00 |
| Bottom plate, laser-cut 2 mm aluminium, countersunk, black lacquer price | £1.2–£3 | model estimate | — | none | £2.10 | £2.10 |
| Felt pad laminated to a 0.4 mm steel disc price | £0.5–£1.5 | model estimate | — | none | £1.00 | £1.00 |
| N52 magnet disc 6 x 2 mm price | £0.05–£0.15 | model estimate | — | none | £0.10 | £0.10 |
| M2.5 x 6 countersunk screw, hex socket, black price | £0.02–£0.08 | model estimate | — | none | £0.05 | £0.05 |
| M2.5 hex standoff, aluminium (bottom plate to weight plate) price | £0.08–£0.25 | model estimate | — | none | £0.17 | £0.17 |
| M3 stainless machine screw price | £0.02–£0.08 | model estimate | — | none | £0.05 | £0.05 |
| Silicone gasket ring price | £0.3–£1.2 | model estimate | — | none | £0.75 | £0.75 |
| Structural adhesive (tower, gallery, frame and spigot bonds), per lamp price | £0.3–£1 | model estimate | — | none | £0.65 | £0.65 |
| Retail box with moulded-pulp inserts price | £2.5–£6 | model estimate | — | none | £4.25 | £4.25 |
| Zinc-plated steel weight plate (laser cut, ~0.4 kg, battery cut-out, tapped holes) price | £2–£5 | model estimate | — | none | £3.50 | £3.50 |

## Notes

- Impact: each value moved ±25% with everything else at its midpoint, at 2000 units (the Manufacturing tab's sensitivity method). Regional multipliers move all the inputs they scale together.
- 'Seed value' is the seed file's own low–high. 'Used' is the midpoint the model uses in this configuration, after the region scales machine, labour, tooling and finishing values.
- Densities are physical constants from material datasheets: they rank high because part weight drives material and spinning time, but they are low-risk and not a verification priority.
- Range widening for confidence affects the range only, not the midpoint, so it is not listed.
