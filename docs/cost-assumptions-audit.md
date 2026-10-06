# Cost assumptions audit: Faro

Generated 2026-10-06 00:58 UTC by Product Workbench.

**Configuration:** Best with no compromise to look and feel, power option A: internal mains dimmable driver: no further design changes beyond the accepted decisions; made in China.  
**Unit cost (midpoint) at 500 units:** £79.62.  
**Values feeding it:** 49, of which 49 are unverified.

> Every value below is a model-generated assumption unless its source says otherwise. Verify the top of the list first: it moves the unit cost most.

| # | Assumption | Seed file → entry | Seed value | Used | Source | Confidence | Verified | Impact ±25% | How to verify |
|---|---|---|---|---|---|---|---|---|---|
| 1 | China machine cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.machine` | 0.35–0.55 × | 0.45 × | model-generated | low | no | ±£3.85 (4.8%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 2 | China finishing cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.finishing` | 0.4–0.6 × | 0.5 × | model-generated | low | no | ±£3.81 (4.8%) | Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier. |
| 3 | Volume price as a share of small-quantity price (electronics) | `project cost settings (edited by you)` → `volume discount: electronics` | 0.4–0.6 × | 0.5 × | user assumption (Oct 2026) | medium | no | ±£3.34 (4.2%) | Ask two suppliers for their price at 100, 500 and 2,000 pcs; the ratio of the 500-pc price to the small-quantity price is the real discount. |
| 4 | Metal spinning machine rate | `seed/cost/process_rates.yaml` → `metal_spinning.machine_gbp_per_hr` | £35–£60/hr | £22.62/hr | model-generated | low | no | ±£2.74 (3.4%) | Send the STEP files to 2–3 spinning shops and ask for a unit price at 500 pcs; ask them to split it into material, spinning time and trimming so the hourly rate can be back-calculated. |
| 5 | Wet paint / lacquer minimum charge per part | `seed/cost/finish_rates.yaml` → `wet_lacquer.min_per_part` | £4–£8 | £3.2 | model-generated | low | no | ±£2.68 (3.4%) | Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their minimum charge per part and per batch. |
| 6 | Certified dimmable constant-current LED driver (mains) [power option A] price | `seed/cost/bought_in.yaml` → `led_driver_mains` | £16.6–£17.2 | £16.9 | Mean Well certified dimmable CC drivers: PCD-25-700A (triac dim) $21.99 @50 (https://www.ledsupply.com/led-drivers/mean-well-pcd-series-with-triac-dimming); LCM-25 $22.70 @25 (https://www.digikey.com/en/products/detail/mean-well-usa-inc/LCM-25/7704704); RS UK LCM-25 £24.71 1-off (https://uk.rs-online.com/web/p/led-drivers/8234743); USD->GBP at 1.3224 (fxstreet.com GBP/USD, 5 Oct 2026); accessed 2026-10-05; prices read from search-result excerpts (direct page fetch blocked by sandbox network policy). Breaks at 25-50 pcs; 500-pc price likely lower. | medium | no | ±£2.36 (3.0%) | Get a certified driver/adapter price at 500 pcs from a distributor, with its certificates for the target markets. |
| 7 | Metal spinning handling time per part | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min` | 4–10 min | 7 min | model-generated | low | no | ±£2.21 (2.8%) | Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run. |
| 8 | Freight and duty to the UK from China | `seed/cost/regions.yaml` → `china.freight_duty_pct` | 8–15 % | 11.5 % | model-generated | low | no | ±£2.05 (2.6%) | Ask a freight forwarder for a per-carton price to the UK and check the UK tariff for table lamps (commodity code 9405) for the duty rate. |
| 9 | Aluminium 1050A (H14) density | `seed/rules/materials.yaml` → `al_1050.density_g_cm3` | 2.71 g/cm³ | 2.71 g/cm³ | model-generated | medium | no | ±£1.76 (2.2%) | Physical constant from the material datasheet; low risk. |
| 10 | Mains cable with plug and inline switch (2 m, fabric) price | `seed/cost/bought_in.yaml` → `mains_cable_plug_switch` | £3–£8 | £5.5 | model-generated | low | no | ±£1.53 (1.9%) | Ask a cable-assembly maker to quote the cable with plug, switch and fabric braid at 500 pcs. |
| 11 | Metal spinning material bought per kg of part | `seed/cost/process_rates.yaml` → `metal_spinning.material_utilisation` | 1.3–1.7 × | 1.5 × | model-generated | low | no | ±£1.31 (1.6%) | Ask the shop what blank size they cut per part (disc or strip dimensions) and how much is trimmed off. |
| 12 | Borosilicate glass density | `seed/rules/materials.yaml` → `borosilicate.density_g_cm3` | 2.23 g/cm³ | 2.23 g/cm³ | model-generated | medium | no | ±£1.31 (1.6%) | Physical constant from the material datasheet; low risk. |
| 13 | Borosilicate glass price | `seed/cost/material_prices.yaml` → `borosilicate.gbp_per_kg` | £10–£25/kg | £17.5/kg | model-generated | low | no | ±£1.28 (1.6%) | Ask a stockist for a price per kg in the form the process needs. |
| 14 | Cut and finished glass tube material bought per kg of part | `seed/cost/process_rates.yaml` → `glass_tube_cut.material_utilisation` | 1.1–1.3 × | 1.2 × | model-generated | low | no | ±£1.28 (1.6%) | Ask the shop what blank size they cut per part (disc or strip dimensions) and how much is trimmed off. |
| 15 | Retail box with moulded-pulp inserts price | `seed/cost/bought_in.yaml` → `retail_packaging` | £2.5–£6 | £4.25 | model-generated | low | no | ±£1.18 (1.5%) | Ask a packaging supplier to quote the retail box and inserts at 500 pcs. |
| 16 | Wet paint / lacquer cost per m² | `seed/cost/finish_rates.yaml` → `wet_lacquer.gbp_per_m2` | £40–£90/m² | £35/m² | model-generated | low | no | ±£1.05 (1.3%) |  |
| 17 | Cut and finished glass tube machine rate | `seed/cost/process_rates.yaml` → `glass_tube_cut.machine_gbp_per_hr` | £35–£55/hr | £21.25/hr | model-generated | low | no | ±£0.88 (1.1%) |  |
| 18 | Exchange rate (USD per GBP) | `seed/cost/commodities.yaml` → `usd_per_gbp` | 1.3224–1.3241 USD/GBP | 1.323 USD/GBP | GBP/USD 1.32406 on 2 Oct 2026 and 1.3224 on 5 Oct 2026 (https://www.mtfxgroup.com/tools/historical-currency-exchange-rates/gbp-to-usd-rate/, https://www.fxstreet.com/news/british-pound-slides-as-france-fiscal-shock-lifts-the-us-dollar-202610051636); accessed 2026-10-05 | high | no | ±£0.86 (1.1%) |  |
| 19 | China tooling cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.tooling` | 0.3–0.5 × | 0.4 × | model-generated | low | no | ±£0.86 (1.1%) |  |
| 20 | Cut and finished glass tube handling time per part | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min` | 5–12 min | 8.5 min | model-generated | low | no | ±£0.84 (1.1%) |  |
| 21 | LME aluminium cash price | `seed/cost/commodities.yaml` → `lme_aluminium_cash` | 3110–3129 USD/t | 3,120 USD/t | LME Al cash $3,119.5/t on 1 Oct 2026 and $3,110/t official cash on 2 Oct 2026 (https://www.alcircle.com/news/lme-aluminium-price-drops-2-62-as-stocks-remain-stable-at-241-375t-on-october-1-121399); $3,129/t on 5 Oct 2026 (https://tradingeconomics.com/commodity/aluminum); accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked) | high | no | ±£0.78 (1.0%) |  |
| 22 | Zinc-plated steel weight plate (~0.8 kg, laser cut) price | `seed/cost/bought_in.yaml` → `steel_weight_plate` | £1.5–£4 | £2.75 | model-generated | low | no | ±£0.77 (1.0%) |  |
| 23 | In-base rotary dimmer (potentiometer on the driver dim input, solid metal knob) price | `seed/cost/bought_in.yaml` → `dimmer_in_base` | £3.19–£4.61 | £3.9 | Potentiometer: Radiohm POTM 100k £2.34 @100 (https://uk.rs-online.com/web/p/potentiometers/4688749), Alpha 100k linear $1.56 @100 (https://www.adafruit.com/product/5277); knob: RS PRO aluminium knobs for 6 mm shaft £2.01-2.27 @1-4 (https://st1-uk.rs-online.com/web/p/potentiometer-knobs/7777322, https://st1-uk.rs-online.com/web/p/potentiometer-knobs/7777331); USD->GBP 1.3224; accessed 2026-10-05; read from search-result excerpts (direct page fetch blocked) | medium | no | ±£0.54 (0.7%) |  |
| 24 | Sheet / spinning-circle conversion premium over metal (1050/3003/5052) | `seed/cost/commodities.yaml` → `aluminium_sheet_conversion` | 1–2 GBP/kg | 1.5 GBP/kg | model-generated | low | no | ±£0.50 (0.6%) |  |
| 25 | Metal spinning extra time per kg | `seed/cost/process_rates.yaml` → `metal_spinning.cycle_min_per_kg` | 3–8 min/kg | 5.5 min/kg | model-generated | low | no | ±£0.46 (0.6%) |  |
| 26 | LED module (5–8 W, CRI 90+) price | `seed/cost/bought_in.yaml` → `led_module` | £2.53–£3.74 | £3.135 | Bridgelux Vero 10 2700K 90CRI COB: DigiKey BXRC-27G1000 $3.34 @100 (https://www.digikey.com/product-detail/en/bridgelux/BXRC-27G1000-B-23/976-1243-ND/5180215); Vero SE 10 BXRC-27G1000-D-73-SE $4.95 (https://ballastshop.com/bxrc-27g1000-d-73-se-bridgelux-gen7-vero-se-10-led-array-983-lumen-2700k/); USD->GBP at 1.3224 (fxstreet.com GBP/USD, 5 Oct 2026); accessed 2026-10-05; prices read from search-result excerpts (direct page fetch blocked by sandbox network policy). No 500-pc break published. | medium | no | ±£0.44 (0.5%) |  |
| 27 | Final assembly, wiring and test time | `seed/products/faro.yaml` → `cost_items (assembly minutes)` | 16 min | 16 min | model-generated | low | no | ±£0.44 (0.5%) |  |
| 28 | Assembly labour rate | `seed/cost/general.yaml` → `labour_gbp_per_hr` | £15–£25/hr | £5.875/hr | model-generated | low | no | ±£0.44 (0.5%) |  |
| 29 | China labour cost multiplier (vs UK) | `seed/cost/regions.yaml` → `china.labour` | 0.2–0.35 × | 0.275 × | model-generated | low | no | ±£0.44 (0.5%) |  |
| 30 | Decorative cap nut (finial) for the lamp tube, solid brass or aluminium price | `seed/cost/bought_in.yaml` → `cap_finial_nut` | £0.6–£2.5 | £1.55 | model-generated | low | no | ±£0.43 (0.5%) |  |
| 31 | Silicone gasket ring price | `seed/cost/bought_in.yaml` → `silicone_gasket` | £0.3–£1.2 | £0.75 | model-generated | low | no | ±£0.42 (0.5%) |  |
| 32 | M10x1 threaded lamp tube, cut to length price | `seed/cost/bought_in.yaml` → `lamp_tube_m10` | £0.6–£2 | £1.3 | model-generated | medium | no | ±£0.36 (0.5%) |  |
| 33 | Tooling for base (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 34 | Tooling for main body (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 35 | Tooling for top cap (metal spinning) | `seed/rules/tooling_cost.yaml` → `low band` | £100–£2000 | £515 | model-generated | low | no | ±£0.29 (0.4%) |  |
| 36 | Cut from stock aluminium tube handling time per part | `seed/cost/process_rates.yaml` → `metal_tube_cut.cycle_min` | 1.5–4 min | 2.75 min | model-generated | low | no | ±£0.23 (0.3%) |  |
| 37 | Cut from stock aluminium tube machine rate | `seed/cost/process_rates.yaml` → `metal_tube_cut.machine_gbp_per_hr` | £30–£45/hr | £17.62/hr | model-generated | low | no | ±£0.23 (0.3%) |  |
| 38 | Lamp nut and washers (M10x1, set for base and cap) price | `seed/cost/bought_in.yaml` → `lamp_nut_set` | £0.2–£0.6 | £0.4 | model-generated | medium | no | ±£0.11 (0.1%) |  |
| 39 | Metal spinning setup time per batch | `seed/cost/process_rates.yaml` → `metal_spinning.setup_hours` | 1–3 hours | 2 hours | model-generated | low | no | ±£0.08 (0.1%) |  |
| 40 | M4 rivet nut (threaded insert for thin sheet) price | `seed/cost/bought_in.yaml` → `rivet_nut_m4` | £0.04–£0.13 | £0.085 | M4 aluminium rivet nuts: Zygology £3.65/100 (https://zygology.com/rivetnuts/standard-rivetnuts/aluminium-rivetnut-small-head-m4-02al01r04011); KayFast £0.13 each (https://www.kayfast.co.uk/view-product/FLANGED-HEAD-ALUMINIUM-RIVNUTS); accessed 2026-10-05; prices read from search-result excerpts (direct page fetch blocked by sandbox network policy). | medium | no | ±£0.07 (0.1%) |  |
| 41 | Aluminium 6063 (T5/T6) price | `seed/cost/material_prices.yaml` → `al_6063.gbp_per_kg` | £4–£6.5/kg | £5.25/kg | model-generated | low | no | ±£0.07 (0.1%) |  |
| 42 | Cut from stock aluminium tube material bought per kg of part | `seed/cost/process_rates.yaml` → `metal_tube_cut.material_utilisation` | 1.05–1.15 × | 1.1 × | model-generated | low | no | ±£0.07 (0.1%) |  |
| 43 | Aluminium 6063 (T5/T6) density | `seed/rules/materials.yaml` → `al_6063.density_g_cm3` | 2.7 g/cm³ | 2.7 g/cm³ | model-generated | high | no | ±£0.07 (0.1%) |  |
| 44 | M4 stainless machine screw price | `seed/cost/bought_in.yaml` → `screw_m4` | £0.03–£0.1 | £0.065 | model-generated | medium | no | ±£0.05 (0.1%) |  |
| 45 | Aluminium premium / domestic price difference, China | `seed/cost/commodities.yaml` → `aluminium_premium_china` | 0–200 USD/t | 100 USD/t | model-generated | low | no | ±£0.03 (0.0%) |  |
| 46 | Cut and finished glass tube extra time per kg | `seed/cost/process_rates.yaml` → `glass_tube_cut.cycle_min_per_kg` | 0–3 min/kg | 1.5 min/kg | model-generated | low | no | ±£0.03 (0.0%) |  |
| 47 | Strain-relief cable grommet price | `seed/cost/bought_in.yaml` → `cable_grommet` | £0.06–£0.11 | £0.085 | Heyco strain-relief bushings, DigiKey @100: model 2126 $0.0762, 2155 $0.1436 (https://azcus.digikey.com/en/products/detail/heyco-products-corporation/2126/15906413, https://azcus.digikey.com/en/products/detail/heyco-products-corporation/2155/15906927); USD->GBP at 1.3224 (fxstreet.com GBP/USD, 5 Oct 2026); accessed 2026-10-05; prices read from search-result excerpts (direct page fetch blocked by sandbox network policy). | medium | no | ±£0.02 (0.0%) |  |
| 48 | Cut and finished glass tube setup time per batch | `seed/cost/process_rates.yaml` → `glass_tube_cut.setup_hours` | 0.5–1 hours | 0.75 hours | model-generated | low | no | ±£0.01 (0.0%) |  |
| 49 | Cut from stock aluminium tube setup time per batch | `seed/cost/process_rates.yaml` → `metal_tube_cut.setup_hours` | 0.3–1 hours | 0.65 hours | model-generated | low | no | ±£0.01 (0.0%) |  |

## Researched prices vs volume-adjusted prices

Unit cost at 500 with every price at its researched basis (no volume adjustment): £98.96; volume-adjusted: £79.62.

| Price | Researched (raw) | Basis | Basis qty | Adjustment | Used at 500 | Used at 2,000 |
|---|---|---|---|---|---|---|
| Aluminium 1050A (H14) price | £7.7–£9.2/kg | retail | 1 | trade basis (LME + premium + sheet conversion) | £3.93/kg | £3.93/kg |
| Aluminium 6063 (T5/T6) price | £4–£6.5/kg | model estimate | — | none | £5.25/kg | £5.25/kg |
| Borosilicate glass price | £10–£25/kg | model estimate | — | none | £17.50/kg | £17.50/kg |
| LED module (5–8 W, CRI 90+) price | £2.53–£3.74 | distributor, small quantity | 100 | volume discount | £1.57 | £1.57 |
| Certified dimmable constant-current LED driver (mains) [power option A] price | £16.6–£17.2 | distributor, small quantity | 25 | volume discount | £8.45 | £8.45 |
| Mains cable with plug and inline switch (2 m, fabric) price | £3–£8 | model estimate | — | none | £5.50 | £5.50 |
| In-base rotary dimmer (potentiometer on the driver dim input, solid metal knob) price | £3.19–£4.61 | distributor, small quantity | 100 | volume discount | £1.95 | £1.95 |
| M4 stainless machine screw price | £0.03–£0.1 | model estimate | — | none | £0.07 | £0.07 |
| M10x1 threaded lamp tube, cut to length price | £0.6–£2 | model estimate | — | none | £1.30 | £1.30 |
| Lamp nut and washers (M10x1, set for base and cap) price | £0.2–£0.6 | model estimate | — | none | £0.40 | £0.40 |
| Decorative cap nut (finial) for the lamp tube, solid brass or aluminium price | £0.6–£2.5 | model estimate | — | none | £1.55 | £1.55 |
| Silicone gasket ring price | £0.3–£1.2 | model estimate | — | none | £0.75 | £0.75 |
| Strain-relief cable grommet price | £0.06–£0.11 | distributor, small quantity | 100 | none | £0.08 | £0.08 |
| Retail box with moulded-pulp inserts price | £2.5–£6 | model estimate | — | none | £4.25 | £4.25 |
| Zinc-plated steel weight plate (~0.8 kg, laser cut) price | £1.5–£4 | model estimate | — | none | £2.75 | £2.75 |
| M4 rivet nut (threaded insert for thin sheet) price | £0.04–£0.13 | distributor, small quantity | 100 | none | £0.09 | £0.09 |

## Notes

- Impact: each value moved ±25% with everything else at its midpoint, at 500 units (the Manufacturing tab's sensitivity method). Regional multipliers move all the inputs they scale together.
- 'Seed value' is the seed file's own low–high. 'Used' is the midpoint the model uses in this configuration, after the region scales machine, labour, tooling and finishing values.
- Densities are physical constants from material datasheets: they rank high because part weight drives material and spinning time, but they are low-risk and not a verification priority.
- Range widening for confidence affects the range only, not the midpoint, so it is not listed.
