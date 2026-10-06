# Cost seed price research (October 2026)

Public-source prices used to update the cost seed data, accessed 2026-10-05. All updated entries keep `verified: false`. Verified is reserved for your own supplier quotes.

**Method note:** in this environment the network policy blocked direct page fetches from every supplier site tried, including DigiKey, RS, Mouser, alcircle.com, Metal Supermarkets and Aluminium Warehouse. Every price below was therefore read from web-search result excerpts that quote the page, and each one is cited by its URL. Treat each figure as "as quoted by the search index on 5 Oct 2026" and spot-check it in a browser before relying on it.

Exchange rate: USD→GBP at 1.3224 (GBP/USD on 5 Oct 2026, [fxstreet](https://www.fxstreet.com/news/british-pound-slides-as-france-fiscal-shock-lifts-the-us-dollar-202610051636)).

## Values changed

| Seed entry | Old (£) | New (£) | Midpoint change | Basis |
|---|---|---|---|---|
| `material_prices` `al_1050` (sheet / spinning discs), £/kg | 4.0–6.5 | 7.7–9.2 | +61% | UK online full-sheet prices for 1050: 2000×1000×3 mm from £125.48 ex VAT, which is £7.72/kg ([aluminiumwarehouse.co.uk](https://www.aluminiumwarehouse.co.uk/aluminium/sheet)); 2000×1000×6 mm at £300 for 32.52 kg, which is £9.23/kg ([aluminiumwarehouse.co.uk](https://www.aluminiumwarehouse.co.uk/products/2000mm-x-1000mm-x-6mm-1050-aluminium-sheet-packs)) |
| `material_prices` `al_6061` (round bar), £/kg | 5.0–8.5 | 5.2–11.5 | +24% | UK: Cromwell 6082 bar, 4 in × 24 in, £154 ex VAT for about 13.3 kg, which is £11.5/kg ([cromwell.co.uk](https://cromwell.co.uk/shop/materials-maintenance-and-standard-parts/engineering-materials/4in-x-24in-aluminium-round-bar-grade-6082-1-pce/p/IND4732376K)). EU 6061-T6 contract price $2.30–3.10/lb, which is £3.8–5.2/kg ([mwalloys](https://www.mwalloys.com/es/aluminum-alloy-6061-price-per-pound-2026/)); the top of that range is the low end. 6082 is used as the UK proxy for 6061 (no 6082 rules material exists). |
| `bought_in` `led_module` | 2.5–8.0 | 2.53–3.74 | −40% | Bridgelux Vero 10 COB, 2700K, 90 CRI: $3.34 at 100 on [DigiKey](https://www.digikey.com/product-detail/en/bridgelux/BXRC-27G1000-B-23/976-1243-ND/5180215); Vero SE 10 at $4.95 ([BallastShop](https://ballastshop.com/bxrc-27g1000-d-73-se-bridgelux-gen7-vero-se-10-led-array-983-lumen-2700k/)) |
| `bought_in` `led_driver_mains` | 3.0–9.0 | 16.6–17.2 | +182% | Mean Well certified dimmable constant-current drivers: PCD-25-700A (triac dimming) at $21.99 for 50 ([LEDSupply](https://www.ledsupply.com/led-drivers/mean-well-pcd-series-with-triac-dimming)); LCM-25 at $22.70 for 25 ([DigiKey](https://www.digikey.com/en/products/detail/mean-well-usa-inc/LCM-25/7704704)); single-unit price £24.71 at [RS UK](https://uk.rs-online.com/web/p/led-drivers/8234743) |
| `bought_in` `external_adapter_12v` | 3.5–8.0 | 9.4–10.1 | +70% | Mean Well GE12I12-P1J (12 V, 12 W, interchangeable plug) at $10.82 for 500 ([DigiKey](https://www.digikey.com/en/products/detail/mean-well-usa-inc/GE12I12-P1J/7703281)), plus the UK plug clip at $1.65 (Jameco) to £1.93 ([RS UK](https://uk.rs-online.com/web/p/power-supply-accessories/1783436)) |
| `bought_in` `cable_grommet` | 0.15–0.60 | 0.06–0.11 | −77% | Heyco strain-relief bushings at 100 on DigiKey: [2126](https://azcus.digikey.com/en/products/detail/heyco-products-corporation/2126/15906413) $0.076, [2155](https://azcus.digikey.com/en/products/detail/heyco-products-corporation/2155/15906927) $0.144 |
| `bought_in` `rivet_nut_m4` | 0.08–0.25 | 0.04–0.13 | −48% | M4 aluminium rivet nuts: £3.65 per 100 from [Zygology](https://zygology.com/rivetnuts/standard-rivetnuts/aluminium-rivetnut-small-head-m4-02al01r04011); £0.13 each from [KayFast](https://www.kayfast.co.uk/view-product/FLANGED-HEAD-ALUMINIUM-RIVNUTS) |

Confidence on all of these is now `medium`. None is a published commodity price, so none is `high`.

**Caveats that matter**
- The LED driver figure is for Mean Well, the brand-name certified option with published prices. The price breaks published are at 25–50 pieces, so a 500-piece or OEM price is likely lower. The old £3–9 range is typical of unbranded OEM drivers, but no public price list was found to back it. **This is now the largest single cost driver, so get a quote first.**
- The aluminium prices are online merchant prices for full sheets and bars. Mill or trade pricing at tonnage would be lower. The metal value floor is about £2.6–2.7/kg: LME cash $3,110–3,129/t on 1–5 Oct 2026 ([alcircle](https://www.alcircle.com/news/lme-aluminium-price-drops-2-62-as-stocks-remain-stable-at-241-375t-on-october-1-121399)) plus the Rotterdam duty-paid premium of about $330–490/t through 2026 ([alcircle](https://www.alcircle.com/news/europe-s-aluminium-duty-paid-premium-falls-18-in-august-as-easing-geopolitical-risks-erase-war-premium-120701)). Material prices are not scaled by region, so a China-made part still uses UK merchant prices here.
- The 12 V adapter path (scenario g) still has no published price for a 12 V CRI 90+ module with an on-board driver. A plain COB on 12 V would also need a DC-DC driver, for example Mean Well LDH-25 at about $9.76 for 100 ([DigiKey](https://www.digikey.com/en/products/detail/mean-well-usa-inc/LDH-25-350/12759948)). That item isn't in the scenario yet.

## Still needs quotes (unchanged)

| Seed entry | What was found | Why not changed |
|---|---|---|
| `al_3003` sheet | No UK price; one Chinese ex-works figure of $1.65–1.80/kg | No credible UK/EU source |
| `al_6063` tube, `al_5052`, casting alloys, polymers, glass, brass | Not searched (out of scope) | — |
| `steel_weight_plate` (about 0.8 kg, laser cut, zinc plated) | UK S275 plate about £800–1,020/t mid-range, up to £1,200–1,350/t for cut plate ([tadweld](https://tadweld.co.uk/uk-steel-prices-set-to-surge-by-2027/)), so raw steel is about £0.65–1.10 per plate | No published price for the cut and plated part at 500. The current £1.5–4 is consistent with raw steel plus cutting. |
| `mains_cable_plug_switch` (2 m fabric) | PVC, 2.5 m, moulded plug and inline switch at £6.29 retail for one ([lampspares](https://www.lampspares.co.uk/white-3-core-with-moulded-plug-and-in-line-switch-2-5m-long/)) | Single retail unit, PVC rather than fabric. It sits inside the current £3–8. |
| Inline **dimmer** cable (not in the seed) | 3-core inline slide dimmer with push switch at £38.72 ex VAT for one ([mr-resistor](https://www.mr-resistor.co.uk/item.aspx?i=19321)) | Retail price for one. If Faro needs an inline dimmer, add it as an item and get a quote: it would be a big line. |
| `lv_cable_switch`, `led_module_12v` | Nothing credible | — |
| `lamp_tube_m10` | Mullan M10 hollow all-thread at £0.18 ex VAT, length not stated ([mullanlighting](https://www.mullanlighting.com/uk/all-thread-pipe-nipple-m10)) | Price not tied to the length needed |
| `lamp_nut_set` | Brass M10 washers £0.155 each in 100s ([bewdirect](https://bewdirect.co.uk/tools,-test-&-fixing/fixings/nuts,-bolts-&-washers/brass-washers-m10-sold-each)); brass M10 nuts £0.57 each in 100s, coarse pitch ([bolts.co.uk](https://bolts.co.uk/m10-full-nut-hexagon-din-934-brass-pack-of-100-p-FNMCBR10)) | No M10×1 lamp-nut price in GBP. The answer depends on brass vs zinc finish. |
| `retail_packaging` | Only "from" prices: US custom mailers from $1.23–1.54, die-cut inserts from $0.15 ([Box Genie](https://www.boxgenie.com/products/custom-mailer-box), [USA Box Maker](https://usaboxmaker.com/die-cut-inserts/)) | Starting prices for small boxes, not a quote at Faro's size |
| `metal_spinning` machine rate | Only operator wage data (about £12–15/hr) | A wage is not a shop rate |
| `cnc_machining` machine rate (£45–80) | UK 3-axis about £45/hr typical ([get-it-made](https://get-it-made.co.uk/resources/how-much-does-cnc-machining-cost)); mid-tier £55–85/hr ([Lewei](https://leweiprecision.com/top-cnc-machining-companies-in-the-uk-2026-profiles-strengths-and-how-to-choose/)) | Consistent with the current range, so left as is. The entry also holds the cycle and setup times, which are unsourced. |
| Wet lacquer / powder coat rates | Only US $/ft² figures and sprayer wages | No UK £/m² source |
| `regions.yaml` multipliers | Eurostat: Portugal manufacturing labour €16.50/hr in 2025 ([Eurostat](https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20260331-2)); UK not in Eurostat; no Turkey or China figures | **No credible source gives specific multipliers, so they are unchanged.** |
| Screws, gaskets, battery-path parts | Out of scope | — |

## Update (6 Oct 2026): price basis, volume discounts, dimmer and DC-DC driver

Each researched entry now records its **price basis** and the quantity it applies to (`price_basis`, `basis_quantity` in the seed). Distributor and retail prices are adjusted when costing at 500 and 2,000 by an editable volume-discount assumption (medium confidence, unverified, user-specified): bought-in electronics 40–60% of the small-quantity distributor price; material from online merchants 50–70% of the merchant price. Hardware (grommets, rivet nuts) is not discounted. The audit shows raw and adjusted prices side by side.

Outside the UK, sheet aluminium (1050/3003/5052) is priced on a **trade basis**: LME cash ($3,110–3,129/t, high confidence) + regional premium (Rotterdam duty-paid $330–490/t for Portugal, sourced; Turkey and China premiums are model estimates, low confidence) ÷ USD/GBP (1.3224–1.3241, high) + a sheet / spinning-circle conversion premium (£1.0–2.0/kg, **model estimate, needs a quote**). That gives about £3.9/kg for China, against £8.45/kg midpoint at UK merchant prices before discount.

`al_6061` bar was restated as a retail basis only (single UK bars £11.5–18.6/kg: Cromwell and RS PRO 4 in × 24 in), so the merchant discount is not applied on top of a contract price.

New researched prices (from search excerpts, accessed 5 Oct 2026):

| Entry | £ | Basis | Source |
|---|---|---|---|
| `dimmer_in_base` (potentiometer + solid aluminium knob) | 3.19–4.61 | distributor, 100 (pot) / 1–4 (knob) | Radiohm POTM 100k £2.34 @100 (RS UK); Alpha 100k $1.56 @100; RS PRO aluminium knobs £2.01–2.27 |
| `dimmer_inline_mains` | 30.00–38.72 | retail, 1 | mr-resistor inline slide dimmer £38.72 ex VAT; creative-cables £36 inc VAT |
| `dimmer_inline_lv` | 3.43 | retail, 1 | Maplin inline 12–24 V dimmer £4.12 inc VAT |
| `dc_dc_cc_driver` (Mean Well LDH-25 class) | 7.38–7.82 | distributor, 100 | TRC / DigiKey LDH-25 $9.76–10.34 @100 |
| `cap_finial_nut` | 0.6–2.5 | model estimate | — |

Still needs quotes, in addition to the list above: touch dimmer module (only uncertified modules from about €1.2 and a €13 retail unit were found), the sheet conversion premium, Turkey and China aluminium premiums, the borosilicate tube price (stock 90 mm OD tubes come in 2.5 and 3.5 mm walls; no price found).

