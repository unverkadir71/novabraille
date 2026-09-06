#!/usr/bin/env node
/**
 * Nova Braille — Dashboard WCAG 2.2 AA axe-core Taraması (statik HTML)
 * JS auth yönlendirmesini atlamak için sayfaları statik olarak serve eder.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const PORT = 9876;
const PUBLIC_DIR = path.resolve(__dirname, 'frontend/public');
const DASHBOARD_DIR = path.resolve(__dirname, 'frontend/dashboard');
const SHARED_DIR = path.resolve(__dirname, 'frontend/shared');

// MIME tipleri
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function serveFile(res, filePath) {
  try {
    const ext = path.extname(filePath);
    const content = fs.readFileSync(filePath);
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

// Statik dosya sunucusu — JS çalıştırmaz, sadece ham HTML döner
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  let filePath;

  // Public sayfalar
  if (url.pathname.startsWith('/public/')) {
    filePath = path.join(PUBLIC_DIR, url.pathname.replace('/public/', ''));
  }
  // Dashboard sayfaları
  else if (url.pathname.startsWith('/dashboard/')) {
    filePath = path.join(DASHBOARD_DIR, url.pathname.replace('/dashboard/', ''));
  }
  // Shared assets
  else if (url.pathname.startsWith('/shared/')) {
    filePath = path.join(SHARED_DIR, url.pathname.replace('/shared/', ''));
  }
  // Root
  else if (url.pathname === '/') {
    res.writeHead(302, { Location: '/public/index.html' });
    res.end();
    return;
  }
  else {
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  serveFile(res, filePath);
});

// Tarama yapılacak dashboard sayfaları
const DASH_PAGES = [
  { name: 'Dashboard (Çeviri)', path: '/dashboard/index.html' },
  { name: 'Geçmiş', path: '/dashboard/history.html' },
  { name: 'Profiller', path: '/dashboard/profiles.html' },
  { name: 'Ayarlar', path: '/dashboard/settings.html' },
  { name: 'Abonelik', path: '/dashboard/subscription.html' },
  { name: 'Login', path: '/dashboard/login.html' },
  { name: 'Şifremi Unuttum', path: '/dashboard/forgot-password.html' },
  { name: 'Admin Dashboard', path: '/dashboard/admin/index.html' },
  { name: 'Admin Kullanıcılar', path: '/dashboard/admin/users.html' },
  { name: 'Admin Roller', path: '/dashboard/admin/roles.html' },
  { name: 'Admin Planlar', path: '/dashboard/admin/plans.html' },
  { name: 'Admin Abonelikler', path: '/dashboard/admin/subscriptions.html' },
  { name: 'Admin Hukuki Editör', path: '/dashboard/admin/legal-editor.html' },
];

async function scanPage(page, pageInfo) {
  try {
    await page.goto(`http://localhost:${PORT}${pageInfo.path}`, {
      waitUntil: 'networkidle0',
      timeout: 15000,
    });

    // axe-core enjekte et
    await page.addScriptTag({
      path: require.resolve('axe-core/axe.min.js'),
    });

    // JS çalışmasını bekle (auth redirect gibi)
    await new Promise(r => setTimeout(r, 2000));

    const results = await page.evaluate(() => {
      return new Promise((resolve) => {
        if (typeof axe === 'undefined') {
          resolve({ error: 'axe-core not loaded' });
          return;
        }
        axe.run(
          { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } },
          (err, results) => { if (err) resolve({ error: err.message }); else resolve(results); }
        );
      });
    });

    if (results.error) {
      console.log(`  ❌ ${pageInfo.name}: ${results.error}`);
      return { page: pageInfo.name, error: results.error, violations: [] };
    }

    const violations = results.violations || [];
    const critical = violations.filter(v => v.impact === 'critical').length;
    const serious = violations.filter(v => v.impact === 'serious').length;

    const icon = violations.length === 0 ? '✅' : '⚠️';
    console.log(`  ${icon} ${pageInfo.name}: ${violations.length} ihlal (${critical} kritik, ${serious} ciddi)`);

    for (const v of violations) {
      console.log(`     [${v.impact}] ${v.id}: ${v.description}`);
      if (v.nodes.length > 0) {
        console.log(`       → ${(v.nodes[0].target || []).join(' ')} | ${(v.nodes[0].failureSummary || '').substring(0, 200)}`);
      }
    }

    return {
      page: pageInfo.name,
      violations: violations.map(v => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.map(n => ({
          html: (n.html || '').substring(0, 120),
          target: (n.target || []).join(' '),
          failureSummary: (n.failureSummary || '').substring(0, 200),
        })),
      })),
      violationCount: violations.length,
      passes: (results.passes || []).length,
    };
  } catch (e) {
    console.log(`  ❌ ${pageInfo.name}: HATA — ${e.message}`);
    return { page: pageInfo.name, error: e.message, violations: [] };
  }
}

async function main() {
  // Sunucuyu başlat
  await new Promise(resolve => server.listen(PORT, resolve));
  console.log(`Statik sunucu: http://localhost:${PORT}`);

  console.log('=== Nova Braille Dashboard axe-core Taraması (statik) ===');

  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const allResults = [];
  let totalViolations = 0;
  let criticalViolations = 0;
  let seriousViolations = 0;

  try {
    const pg = await browser.newPage();

    for (const pageInfo of DASH_PAGES) {
      const result = await scanPage(pg, pageInfo);
      totalViolations += result.violationCount;
      criticalViolations += result.violations.filter(v => v.impact === 'critical').length;
      seriousViolations += result.violations.filter(v => v.impact === 'serious').length;
      allResults.push(result);
    }

    await pg.close();
  } finally {
    await browser.close();
    server.close();
  }

  // Özet
  console.log('\n=== ÖZET ===');
  console.log(`Taranan sayfa: ${allResults.length}`);
  console.log(`Toplam ihlal: ${totalViolations}`);
  console.log(`Kritik: ${criticalViolations}`);
  console.log(`Ciddi: ${seriousViolations}`);

  const pagesWithViolations = allResults.filter(r => r.violationCount > 0);
  if (pagesWithViolations.length > 0) {
    console.log('\nİhlal bulunan sayfalar:');
    for (const r of pagesWithViolations) {
      console.log(`  - ${r.page}: ${r.violationCount} ihlal`);
    }
  } else {
    console.log('\n✅ Tüm sayfalar temiz!');
  }

  // Rapor
  const report = {
    timestamp: new Date().toISOString(),
    mode: 'static-html',
    totalPages: allResults.length,
    totalViolations,
    criticalViolations,
    seriousViolations,
    results: allResults,
  };
  fs.writeFileSync('/tmp/axe-dashboard-report.json', JSON.stringify(report, null, 2));
  console.log(`\nDetaylı rapor: /tmp/axe-dashboard-report.json`);
}

main().catch(err => { console.error(err); process.exit(1); });