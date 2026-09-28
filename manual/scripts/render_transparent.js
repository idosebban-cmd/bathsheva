// Renders an SVG (with its background rect stripped) to a transparent PNG
// at a specified device pixel scale (px per mm = 96/25.4 * deviceScaleFactor).
// Usage: node render_transparent.js <svg_path> <out_png> <px_per_mm>
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [svgPath, outPng, pxPerMmStr] = process.argv.slice(2);
  const pxPerMm = parseFloat(pxPerMmStr);
  const deviceScaleFactor = pxPerMm / (96 / 25.4);

  let svg = fs.readFileSync(svgPath, 'utf8');
  svg = svg.replace(/<rect[^>]*fill="#F7F3EC"[^>]*\/>/, '');

  const tmpPath = svgPath.replace(/\.svg$/, '_transparent_tmp.svg');
  fs.writeFileSync(tmpPath, svg);

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage({ deviceScaleFactor });
  await page.goto('file://' + path.resolve(tmpPath));
  const svgEl = await page.$('svg');
  await svgEl.screenshot({ path: outPng, omitBackground: true });
  await browser.close();
  fs.unlinkSync(tmpPath);
  console.log('wrote', outPng, 'at', pxPerMm, 'px/mm');
})();
