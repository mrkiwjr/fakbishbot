import { chromium } from 'playwright';
import { createServer } from 'vite';

const vite = await createServer({ server: { port: 5174 } });
await vite.listen();

const pages = [
  { name: 'home', path: '/' },
  { name: 'tariffs', path: '/tariffs' },
  { name: 'promos', path: '/promos' },
  { name: 'booking', path: '/booking' },
];

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
});

for (const p of pages) {
  const page = await context.newPage();
  await page.goto(`http://localhost:5174${p.path}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `screenshots/${p.name}.png`, fullPage: true });
  await page.close();
}

await browser.close();
await vite.close();
console.log('Done');
