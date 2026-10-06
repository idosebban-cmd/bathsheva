# Open questions before sending the Faro RFQ

Internal. Suppliers will ask these; each has a proposed answer. Resolve them, then send the zip.

1. **Electronics: Battery pack configuration: 1S2P (3.6 V, 6.7 Ah) or 2S (7.2 V, 3.35 Ah)?**
   - Why: Sets the charger, the LED driver topology and which pre-certified packs fit.
   - Proposed: 1S2P: simplest 5 V USB-C charging and widest choice of certified packs; the RFQ asks suppliers to confirm or propose 2S.

2. **Electronics: Do the lantern and tower lights dim together on the one knob, or does the tower stay at a fixed ratio?**
   - Why: Defines the control board's channel behaviour.
   - Proposed: Both dim together from the knob; tower light at a fixed share of the lantern (ratio set at the factory).

3. **Electronics: How is charging and low battery shown to the user?**
   - Why: The control board and the base need an indicator (LED and light pipe, or a lantern blink).
   - Proposed: No visible indicator on the lamp: the lantern blinks twice at low battery; a small LED by the USB-C port shows charging.

4. **Drawings: Which general tolerance applies where a drawing gives none?**
   - Why: The drawings say "tolerances to be agreed"; suppliers price to the tolerance.
   - Proposed: ISO 2768-m for metal parts, ±0.5 mm on glass length and ±0.3 mm on glass OD; fits (bayonet, spigots) as dimensioned.

5. **Finish: Exact colours and gloss for the black, cream and red lacquer, and the brass finish.**
   - Why: Finishers need RAL/Pantone references and gloss levels to quote and match.
   - Proposed: Send physical colour samples or RAL references (e.g. cream ≈ RAL 9001, red ≈ RAL 3011, gloss black RAL 9005, 90+ gloss); brass polished and clear-lacquered.

6. **Nameplate: Nameplate artwork (FARO lettering, font, fill colour).**
   - Why: The etcher needs vector artwork to tool.
   - Proposed: Supply a vector file (SVG/DXF) of the lettering at 1:1 with the RFQ.

7. **Compliance: Markets for launch: UK only, or UK and EU?**
   - Why: Sets the marking (UKCA / CE), plug types for option B and the battery regulations.
   - Proposed: UK and EU (the requirement is still marked as an assumption).

8. **Commercial: Delivery terms, currency and delivery address.**
   - Why: Quotes are not comparable without the same Incoterm and currency.
   - Proposed: Quote FOB (port of loading) and DDP to a UK address, in GBP or USD.

9. **Commercial: Who does final assembly, test and packing?**
   - Why: Changes who quotes the electronics fitting, the bonding and the retail box.
   - Proposed: Ask each mechanical supplier whether they can offer final assembly; packaging quoted separately.

10. **Packaging: Retail box and shipping carton specification.**
   - Why: Not in the RFQ yet; glass parts need protective packing.
   - Proposed: Ask for the supplier's standard protective packing now; brief the retail box separately.

11. **Assembly: Which structural adhesive for the tower, gallery, frame and spigot bonds?**
   - Why: Suppliers may propose their own; it affects cure time and long-term strength.
   - Proposed: Let suppliers propose (e.g. a two-part methacrylate or epoxy) with a pull-test on samples.

12. **Quality: Inspection level (AQL) and who approves the golden sample.**
   - Why: The RFQ says "to be agreed"; suppliers price inspection into the part.
   - Proposed: AQL 1.0 major / 2.5 minor for cosmetics; golden sample approved by you before production.

13. **Commercial: Production volume is still TBD.**
   - Why: The RFQ asks for 300 / 500 / 2,000; suppliers will ask which you expect to order first.
   - Proposed: Say which quantity is the likely first order.

14. **Electronics: LED wattages, cell capacity and the runtime estimate are model-generated.**
   - Why: The runtime target (and the pack choice) depend on them.
   - Proposed: Keep them as UNVERIFIED targets in the RFQ; check against the suppliers' datasheets.
