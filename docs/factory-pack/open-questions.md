# Open questions before sending the Faro RFQ

Internal. Do not send. Answers marked resolved are already written into the RFQs.

## Fill in before sending

These placeholders are in both RFQs (mechanical/rfq and electronics/rfq_electronics):

- [ ] `[COMPANY NAME]`
- [ ] `[CONTACT NAME, ROLE]`
- [ ] `[EMAIL]`
- [ ] `[PHONE]`
- [ ] `[COMPANY ADDRESS]`
- [ ] `[QUOTE DEADLINE]`
- [ ] `[DELIVERY ADDRESS, to be filled in]`

## Still open

None.

## Resolved (in the RFQs)

| # | Topic | Question | Answer |
|---|---|---|---|
| 1 | Electronics | Battery pack configuration: 1S2P (3.6 V, 6.7 Ah) or 2S (7.2 V, 3.35 Ah)? | 1S2P (3.6 V nominal); suppliers may propose 2S with reasons. |
| 2 | Electronics | Do the lantern and tower lights dim together on the one knob, or does the tower stay at a fixed ratio? | Both dim together from the knob; the tower light is a fixed share of the lantern, set at the factory. |
| 3 | Electronics | How is charging and low battery shown to the user? | The lantern blinks twice at low battery; a small LED by the USB-C port shows charging. No other indicator. |
| 4 | Drawings | Which general tolerance applies where a drawing gives none? | ISO 2768-m for metal parts; glass ±0.5 mm on length and ±0.3 mm on OD; fits (bayonet, spigots) as dimensioned. |
| 5 | Finish | Exact colours and gloss for the black, cream and red lacquer, and the brass finish. | Hex values from the prototype (black, cream) and Atelier (oxblood red), each with the nearest RAL marked approximate; physical colour samples will be supplied. Brass polished and clear-lacquered. |
| 6 | Nameplate | Nameplate artwork (FARO lettering, font, fill colour). | Prototype lettering exported 1:1 as SVG and DXF (mechanical/artwork/); etched, filled black. |
| 7 | Compliance | Markets for launch: UK only, or UK and EU? | UK only at launch: quote UKCA marking; CE for the EU may follow. |
| 8 | Commercial | Delivery terms, currency and delivery address. | FOB (port of loading) and DDP to a UK address, in GBP or USD. The delivery address is a placeholder for you to fill in. |
| 9 | Commercial | Who does final assembly, test and packing? | Each mechanical supplier is asked whether they can offer final assembly, test and packing; the retail box is quoted separately. |
| 10 | Packaging | Retail box and shipping carton specification. | Suppliers quote their standard protective packing now; the retail box is briefed separately. |
| 11 | Assembly | Which structural adhesive for the tower, gallery, frame and spigot bonds? | Suppliers propose the adhesive (e.g. two-part methacrylate or epoxy), proven by a pull-test on samples. |
| 12 | Quality | Inspection level (AQL) and who approves the golden sample. | AQL 1.0 major / 2.5 minor for cosmetics; golden sample approved by Bathsheva London before production. |
| 13 | Commercial | Likely first order. | 300 to 500 lamps, depending on pre-orders; all three tiers (300, 500, 2,000) quoted. |
| 14 | Electronics | LED wattages, cell capacity and the runtime estimate are model-generated. | Kept as UNVERIFIED targets in the RFQ; checked against the suppliers' datasheets. |

## Colour references used

| Finish | Hex | Nearest RAL (approximate) | Source |
|---|---|---|---|
| Gloss black lacquer | #121212 | RAL 9005 Jet black | prototype faro/params.py BASE_HEX |
| Cream lacquer | #F9F2E1 | RAL 9001 Cream | prototype faro/params.py CREAM_HEX |
| Oxblood red lacquer | #8A1C15 | RAL 3002 Carmine red | Atelier params.py RED_HEX (warm deep oxblood lacquer); prototype faro/params.py uses the same value |
| Polished brass, clear lacquer | #C4A15A | n/a (natural brass) | prototype faro/params.py BRASS_HEX (render reference only) |
