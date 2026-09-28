#!/usr/bin/env python3
"""
One command rebuilds the Atelier manual: python3 manual/build.py

content.md (the copy, in a light custom markup) + specs.yaml (every
hardware fact) -> manual/out/atelier-manual.html -> manual/out/atelier-manual.pdf
+ manual/out/page-NN.png previews, via a headless-Chromium print (scripts/render_pdf.js).

Every value pulled from specs.yaml that is still TBD_FROM_ODM renders in
bright magenta on the page, and the full list of remaining TBDs is printed
at the end of the build (and written to manual/out/tbd_report.txt) so
nothing ships hidden.
"""

import re
import subprocess
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content.md"
SPECS = ROOT / "specs.yaml"
FIGURES = ROOT / "figures" / "final"
OUT = ROOT / "out"

TBD_VALUE = "TBD_FROM_ODM"
OXBLOOD = "#5A1A1F"
INK = "#181410"
PAPER = "#F7F3EC"
MAGENTA = "#FF00FF"

PAGE_W_MM, PAGE_H_MM = 105, 148


def load_specs():
    return yaml.safe_load(SPECS.read_text())


def spec_lookup(specs, dotted_path):
    node = specs
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def render_spec_token(specs, dotted_path, tbd_log, page_id):
    value, found = spec_lookup(specs, dotted_path)
    if not found:
        msg = f"content.md references unknown spec path: {dotted_path}"
        raise KeyError(msg)
    if value is None:
        value = ""
    text = str(value)
    if text == TBD_VALUE or text.strip() == "":
        tbd_log.append((page_id, dotted_path))
        return f'<span class="tbd" title="{dotted_path}">{dotted_path.split(".")[-1].replace("_", " ")}: TBD</span>'
    return text


class Page:
    def __init__(self, page_id, raw):
        self.id = page_id
        self.raw = raw
        self.subtitle = None
        self.footer_provisional = False
        self.number = None


def parse_pages(text):
    parts = re.split(r"<!--\s*page:\s*([\w-]+)\s*-->", text)
    # parts[0] is anything before the first marker (should be empty/whitespace)
    pages = []
    for i in range(1, len(parts), 2):
        page_id = parts[i].strip()
        body = parts[i + 1]
        pages.append(Page(page_id, body))
    return pages


def extract_directives(page):
    def take_subtitle(m):
        page.subtitle = m.group(1).strip()
        return ""

    def take_footer(m):
        if m.group(1).strip() == "provisional":
            page.footer_provisional = True
        return ""

    body = page.raw
    body = re.sub(r"<!--\s*subtitle\s*-->\s*\n(.+)\n", take_subtitle, body, count=1)
    body = re.sub(r"<!--\s*footer:\s*(\w+)\s*-->", take_footer, body)
    return body


def embed_figure(match, tbd_log, page):
    name_and_mods = match.group(1).strip().split()
    name = name_and_mods[0]
    mods = name_and_mods[1:]
    svg_path = FIGURES / f"{name}.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"content.md references missing figure: {name} (page {page.id})")
    svg = svg_path.read_text()
    svg = re.sub(r"^<\?xml[^>]*\?>\s*", "", svg)
    classes = "figure " + " ".join(f"figure--{m}" for m in mods)
    if "provisional" in FITTED_FIGURES.get(name, ()):
        page.footer_provisional = True
    return f'<div class="{classes}">{svg}</div>'


# figures whose geometry depends on fitted_by_eye (not-yet-confirmed) placement
FITTED_FIGURES = {
    "hero_front": ("provisional",),
    "front_callouts": ("provisional",),
    "knob_closeup": ("provisional",),
    "knob_closeup_base": ("provisional",),
}


def build_page_html(page, specs, tbd_log, page_numbers):
    body = extract_directives(page)

    def spec_sub(m):
        return render_spec_token(specs, m.group(1).strip(), tbd_log, page.id)

    def page_ref_sub(m):
        target = m.group(1).strip()
        return str(page_numbers.get(target, "?"))

    def figure_sub(m):
        return embed_figure(m, tbd_log, page)

    body = re.sub(r"\{\{spec:([^}]+)\}\}", spec_sub, body)
    body = re.sub(r"\{\{page:([^}]+)\}\}", page_ref_sub, body)
    body = re.sub(r"<!--\s*figure:\s*([^-]+?)\s*-->", figure_sub, body)

    html_body = markdown.markdown(body, extensions=["tables"])

    subtitle_html = f'<p class="subtitle">{page.subtitle}</p>' if page.subtitle else ""
    footer_html = (
        '<div class="footer-note">Provisional illustration &mdash; pending production CAD confirmation.</div>'
        if page.footer_provisional else ""
    )
    page_num_html = f'<div class="page-number">{page.number}</div>' if page.id not in ("cover",) else ""

    return f'''<section class="page" id="page-{page.id}">
  <div class="page-inner">
    {subtitle_html}
    {html_body}
  </div>
  {footer_html}
  {page_num_html}
</section>'''


CSS = f'''
@page {{ size: {PAGE_W_MM}mm {PAGE_H_MM}mm; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #ccc; }}
body {{ font-family: Georgia, "Times New Roman", serif; color: {INK}; }}

.page {{
  width: {PAGE_W_MM}mm;
  height: {PAGE_H_MM}mm;
  background: {PAPER};
  position: relative;
  page-break-after: always;
  overflow: hidden;
}}
.page-inner {{
  position: absolute;
  inset: 0;
  padding: 10mm 9mm 13mm 9mm;
  display: flex;
  flex-direction: column;
}}

h1 {{
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
  font-size: 17pt;
  color: {OXBLOOD};
  margin: 0 0 3mm 0;
  letter-spacing: 0.02em;
}}
h2 {{
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
  font-size: 10.5pt;
  color: {OXBLOOD};
  margin: 2.5mm 0 1.5mm 0;
  border-top: 0.4pt solid {OXBLOOD};
  padding-top: 1.5mm;
}}
p.subtitle {{
  font-family: Helvetica, Arial, sans-serif;
  font-size: 8.5pt;
  color: #6b6b6b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: -1.5mm 0 3mm 0;
}}
p, li {{
  font-family: Helvetica, Arial, sans-serif;
  font-size: 8.5pt;
  line-height: 1.45;
  margin: 0 0 2.2mm 0;
}}
ol, ul {{ margin: 0 0 2.2mm 0; padding-left: 4.5mm; }}
strong {{ color: {OXBLOOD}; }}

table {{
  width: 100%;
  border-collapse: collapse;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 7.6pt;
  margin: 1mm 0 2mm 0;
}}
th, td {{
  text-align: left;
  padding: 0.9mm 1.5mm;
  border-bottom: 0.35pt solid #d8d0c2;
  vertical-align: top;
}}
th {{
  color: {OXBLOOD};
  font-weight: 700;
  border-bottom: 0.6pt solid {OXBLOOD};
}}

.tbd {{
  color: {MAGENTA};
  font-weight: 700;
  font-family: Helvetica, Arial, sans-serif;
}}

.figure {{
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 1mm 0;
}}
.figure svg {{ width: 100%; height: auto; max-height: 78mm; }}
.figure--small svg {{ max-height: 42mm; }}
.figure--centered {{ justify-content: center; }}

#page-cover .page-inner {{
  align-items: center;
  justify-content: space-between;
  text-align: center;
  padding-top: 16mm;
  padding-bottom: 16mm;
}}
#page-cover h1 {{
  font-size: 26pt;
  letter-spacing: 0.12em;
  margin-top: 4mm;
}}
#page-cover p.subtitle {{
  font-size: 9pt;
  margin-top: -2mm;
}}
#page-cover .figure {{ flex: 1; width: 100%; }}
#page-cover .figure svg {{ max-height: 100mm; }}

#page-regulatory .subtitle:last-of-type {{
  margin-top: auto;
  text-align: center;
  border-top: none;
}}

.footer-note {{
  position: absolute;
  left: 9mm;
  right: 9mm;
  bottom: 5.5mm;
  font-family: Helvetica, Arial, sans-serif;
  font-style: italic;
  font-size: 6.2pt;
  color: #8a8378;
}}
.page-number {{
  position: absolute;
  right: 9mm;
  bottom: 5.5mm;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 7pt;
  color: #8a8378;
}}
'''


def main():
    specs = load_specs()
    text = CONTENT.read_text()
    pages = parse_pages(text)

    # assign printed page numbers (cover is unnumbered)
    page_numbers = {}
    n = 1
    for p in pages:
        if p.id == "cover":
            continue
        page_numbers[p.id] = n
        n += 1
    for p in pages:
        p.number = page_numbers.get(p.id)

    if len(pages) % 4 != 0:
        print(f"WARNING: page count {len(pages)} is not a multiple of 4 (saddle stitch)", file=sys.stderr)

    tbd_log = []
    page_html = []
    for p in pages:
        page_html.append(build_page_html(p, specs, tbd_log, page_numbers))

    html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Atelier manual</title>
<style>{CSS}</style>
</head>
<body>
{"".join(page_html)}
</body>
</html>'''

    OUT.mkdir(parents=True, exist_ok=True)
    html_path = OUT / "atelier-manual.html"
    html_path.write_text(html)
    print(f"wrote {html_path} ({len(pages)} pages)")

    # render PDF + per-page PNGs
    result = subprocess.run(
        ["node", str(ROOT / "scripts" / "render_pdf.js"), str(html_path), str(OUT), str(PAGE_W_MM), str(PAGE_H_MM), str(len(pages))],
    )
    if result.returncode != 0:
        print("\nBUILD FAILED: one or more pages overflowed their A6 box (see warnings above).", file=sys.stderr)
        sys.exit(1)

    # TBD report
    report_lines = [f"Remaining TBD_FROM_ODM values: {len(tbd_log)}", ""]
    for page_id, path in tbd_log:
        report_lines.append(f"  page '{page_id}': {path}")
    report = "\n".join(report_lines)
    (OUT / "tbd_report.txt").write_text(report + "\n")
    print()
    print(report)


if __name__ == "__main__":
    main()
