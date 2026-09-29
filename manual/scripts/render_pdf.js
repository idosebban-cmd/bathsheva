// Renders the built manual HTML to a PDF (A6 pages) and a PNG preview per page.
// Usage: node render_pdf.js <html_path> <out_dir> <page_w_mm> <page_h_mm> <n_pages>
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');

(async () => {
  const [htmlPath, outDir, pageWmm, pageHmm, nPages] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage({ deviceScaleFactor: 3 });
  await page.goto('file://' + path.resolve(htmlPath));
  await page.emulateMedia({ media: 'print' });

  const pdfPath = path.join(outDir, 'atelier-manual.pdf');
  await page.pdf({
    path: pdfPath,
    width: pageWmm + 'mm',
    height: pageHmm + 'mm',
    printBackground: true,
    margin: { top: 0, bottom: 0, left: 0, right: 0 },
  });
  console.log('wrote', pdfPath);

  const sections = await page.$$('.page');
  const overflows = [];
  for (let i = 0; i < sections.length; i++) {
    const idAttr = await sections[i].getAttribute('id');
    const fname = String(i + 1).padStart(2, '0') + '-' + idAttr.replace('page-', '') + '.png';
    const outPath = path.join(outDir, fname);
    await sections[i].screenshot({ path: outPath });
    console.log('wrote', outPath);

    const overflow = await sections[i].evaluate((el) => {
      const inner = el.querySelector('.page-inner');
      if (!inner) return 0;
      return Math.round((inner.scrollHeight - inner.clientHeight) * 10) / 10;
    });
    if (overflow > 0.5) {
      overflows.push({ id: idAttr, overflow_mm: overflow });
    }
  }

  await browser.close();

  if (overflows.length) {
    console.error('\nWARNING: content overflows the page box and was clipped on:');
    for (const o of overflows) {
      console.error(`  ${o.id}: ${o.overflow_mm}mm too tall`);
    }
    process.exitCode = 1;
  }
})();
