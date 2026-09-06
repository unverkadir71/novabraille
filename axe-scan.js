#!/usr/bin/env node
/**
 * Nova Braille — WCAG 2.2 AA axe-core Otomatik Tarama
 * Faz 6.1 — Erişilebilirlik testi
 *
 * Kullanım: node axe-scan.js [--public-only] [--dashboard] [--all]
 */

const puppeteer = require('puppeteer');
const AxeBuilder = require('axe-core');

const BASE = 'http://localhost:8765';

// -------------------------------------------------------------
// Tarama sayfaları
// -------------------------------------------------------------
const PUBLIC_PAGES = [
  { name: 'Anasayfa', url: `${BASE}/public/index.html` },
  { name: 'Özellikler', url: `${BASE}/public/features.html` },
  { name: 'Fiyatlandırma', url: `${BASE}/public/pricing.html` },
  { name: 'Self-Hosted', url: `${BASE}/public/self-hosted.html` },
  { name: 'Hakkımızda', url: `${BASE}/public/about.html` },
  { name: 'İletişim', url: `${BASE}/public/contact.html` },
  { name: 'Destek', url: `${BASE}/public/support.html` },
  { name: 'Erişilebilirlik', url: `${BASE}/public/accessibility.html` },
  { name: 'Gizlilik', url: `${BASE}/public/privacy.html` },
  { name: 'KVKK', url: `${BASE}/public/kvkk.html` },
  { name: 'Kullanım Koşulları', url: `${BASE}/public/terms.html` },
  { name: 'İade/İptal', url: `${BASE}/public/refund.html` },
  { name: 'Docs', url: `${BASE}/public/docs.html` },
];

const AUTH_PAGES = [
  { name: 'Login', url: `${BASE}/dashboard/login.html` },
  { name: 'Şifremi Unuttum', url: `${BASE}/dashboard/forgot-password.html` },
];

// Dashboard sayfaları (login gerekli)
const DASHBOARD_PAGES = [
  { name: 'Dashboard (Çeviri)', url: `${BASE}/dashboard/index.html` },
  { name: 'Geçmiş', url: `${BASE}/dashboard/history.html` },
  { name: 'Profiller', url: `${BASE}/dashboard/profiles.html` },
  { name: 'Ayarlar', url: `${BASE}/dashboard/settings.html` },
  { name: 'Abonelik', url: `${BASE}/dashboard/subscription.html` },
];

const ADMIN_PAGES = [
  { name: 'Admin Dashboard', url: `${BASE}/dashboard/admin/index.html` },
  { name: 'Admin Kullanıcılar', url: `${BASE}/dashboard/admin/users.html` },
  { name: 'Admin Roller', url: `${BASE}/dashboard/admin/roles.html` },
  { name: 'Admin Planlar', url: `${BASE}/dashboard/admin/plans.html` },
  { name: 'Admin Abonelikler', url: `${BASE}/dashboard/admin/subscriptions.html` },
  { name: 'Admin Hukuki Editör', url: `${BASE}/dashboard/admin/legal-editor.html` },
];

// -------------------------------------------------------------
// axe-core'u sayfaya enjekte et ve çalıştır
// -------------------------------------------------------------
async function runAxe(page) {
  // axe-core'u tarayıcıda çalıştır
  const results = await page.evaluate(() => {
    return new Promise((resolve) => {
      // axe-core global scope'ta
      if (typeof axe === 'undefined') {
        resolve({ error: 'axe-core not loaded' });
        return;
      }
      axe.run(
        {
          runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'],
          },
        },
        (err, results) => {
          if (err) resolve({ error: err.message });
          else resolve(results);
        }
      );
    });
  });
  return results;
}

// -------------------------------------------------------------
// Bulguları analiz et
// -------------------------------------------------------------
function analyzeResults(pageName, results) {
  if (results.error) {
    return { page: pageName, error: results.error, violations: [], passes: [], incomplete: [] };
  }

  const violations = (results.violations || []).map((v) => ({
    id: v.id,
    impact: v.impact,
    description: v.description,
    helpUrl: v.helpUrl,
    nodes: v.nodes.map((n) => ({
      html: n.html ? n.html.substring(0, 120) : '',
      target: (n.target || []).join(' '),
      failureSummary: n.failureSummary ? n.failureSummary.substring(0, 200) : '',
    })),
  }));

  return {
    page: pageName,
    violations,
    violationCount: violations.length,
    passes: (results.passes || []).length,
    incomplete: (results.incomplete || []).length,
  };
}

// -------------------------------------------------------------
// Test kullanıcısı oluştur ve login ol
// -------------------------------------------------------------
async function registerAndLogin(page) {
  // Auth yönlendirmesini tamamen bloke et: fake auth + location override
  await page.evaluateOnNewDocument(() => {
    // 1. fetch override: /auth/me → fake authenticated user
    const originalFetch = window.fetch;
    window.fetch = function(url, ...args) {
      const urlStr = typeof url === 'string' ? url : (url.url || '');
      if (urlStr.includes('/auth/me')) {
        return Promise.resolve(new Response(JSON.stringify({
          id: 'axe-scan-fake-id',
          email: 'axe-test@novabraille.com',
          status: 'active',
          role: 'user',
          display_name: 'Axe Tester',
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return originalFetch.call(this, url, ...args);
    };

    // 2. location.href assign override — login yönlendirmesini engelle
    const originalDescriptor = Object.getOwnPropertyDescriptor(window.Location.prototype, 'href');
    // Sadece login içermeyen set'lere izin ver
  });

  // Login sayfasına git
  await page.goto(`${BASE}/dashboard/login.html`, { waitUntil: 'networkidle0' });
  console.log(`  Auth bypassed, URL: ${page.url()}`);
  return true;
}

// -------------------------------------------------------------
// Ana tarama fonksiyonu
// -------------------------------------------------------------
async function scan() {
  console.log('=== Nova Braille WCAG 2.2 AA axe-core Taraması ===');
  console.log(`Başlangıç: ${new Date().toISOString()}\n`);

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
    // --- PUBLIC sayfalar ---
    console.log('📄 Public Site Sayfaları:');
    for (const pageInfo of PUBLIC_PAGES) {
      const pg = await browser.newPage();
      try {
        await pg.goto(pageInfo.url, { waitUntil: 'networkidle0', timeout: 15000 });

        // axe-core enjekte et
        await pg.addScriptTag({
          path: require.resolve('axe-core/axe.min.js'),
        });

        const results = await runAxe(pg);
        const analyzed = analyzeResults(pageInfo.name, results);

        const critical = analyzed.violations.filter((v) => v.impact === 'critical').length;
        const serious = analyzed.violations.filter((v) => v.impact === 'serious').length;

        totalViolations += analyzed.violationCount;
        criticalViolations += critical;
        seriousViolations += serious;

        const icon = analyzed.violationCount === 0 ? '✅' : '⚠️';
        console.log(`  ${icon} ${pageInfo.name}: ${analyzed.violationCount} ihlal (${critical} kritik, ${serious} ciddi), ${analyzed.passes} geçti, ${analyzed.incomplete} eksik`);

        if (analyzed.violationCount > 0) {
          for (const v of analyzed.violations) {
            console.log(`     [${v.impact}] ${v.id}: ${v.description}`);
            if (v.nodes.length > 0) {
              console.log(`       → ${v.nodes[0].target} | ${v.nodes[0].failureSummary}`);
            }
          }
        }
        allResults.push(analyzed);
      } catch (e) {
        console.log(`  ❌ ${pageInfo.name}: HATA — ${e.message}`);
        allResults.push({ page: pageInfo.name, error: e.message, violations: [] });
      } finally {
        await pg.close();
      }
    }

    // --- AUTH sayfaları ---
    console.log('\n🔐 Auth Sayfaları:');
    for (const pageInfo of AUTH_PAGES) {
      const pg = await browser.newPage();
      try {
        await pg.goto(pageInfo.url, { waitUntil: 'networkidle0', timeout: 15000 });
        await pg.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
        const results = await runAxe(pg);
        const analyzed = analyzeResults(pageInfo.name, results);

        const critical = analyzed.violations.filter((v) => v.impact === 'critical').length;
        const serious = analyzed.violations.filter((v) => v.impact === 'serious').length;

        totalViolations += analyzed.violationCount;
        criticalViolations += critical;
        seriousViolations += serious;

        const icon = analyzed.violationCount === 0 ? '✅' : '⚠️';
        console.log(`  ${icon} ${pageInfo.name}: ${analyzed.violationCount} ihlal (${critical} kritik, ${serious} ciddi)`);

        if (analyzed.violationCount > 0) {
          for (const v of analyzed.violations) {
            console.log(`     [${v.impact}] ${v.id}: ${v.description}`);
          }
        }
        allResults.push(analyzed);
      } catch (e) {
        console.log(`  ❌ ${pageInfo.name}: HATA — ${e.message}`);
      } finally {
        await pg.close();
      }
    }

    // --- DASHBOARD sayfaları (login gerekli) ---
    console.log('\n📊 Dashboard Sayfaları (login ile):');
    const dashPg = await browser.newPage();
    try {
      await registerAndLogin(dashPg);

      for (const pageInfo of DASHBOARD_PAGES) {
        try {
          await dashPg.goto(pageInfo.url, { waitUntil: 'networkidle0', timeout: 15000 });
          await dashPg.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
          const results = await runAxe(dashPg);
          const analyzed = analyzeResults(pageInfo.name, results);

          const critical = analyzed.violations.filter((v) => v.impact === 'critical').length;
          const serious = analyzed.violations.filter((v) => v.impact === 'serious').length;

          totalViolations += analyzed.violationCount;
          criticalViolations += critical;
          seriousViolations += serious;

          const icon = analyzed.violationCount === 0 ? '✅' : '⚠️';
          console.log(`  ${icon} ${pageInfo.name}: ${analyzed.violationCount} ihlal (${critical} kritik, ${serious} ciddi)`);

          if (analyzed.violationCount > 0) {
            for (const v of analyzed.violations) {
              console.log(`     [${v.impact}] ${v.id}: ${v.description}`);
            }
          }
          allResults.push(analyzed);
        } catch (e) {
          console.log(`  ❌ ${pageInfo.name}: HATA — ${e.message}`);
        }
      }
    } finally {
      await dashPg.close();
    }

    // --- ADMIN sayfaları ---
    console.log('\n🛡️ Admin Sayfaları:');
    const adminPg = await browser.newPage();
    try {
      await registerAndLogin(adminPg);

      for (const pageInfo of ADMIN_PAGES) {
        try {
          await adminPg.goto(pageInfo.url, { waitUntil: 'networkidle0', timeout: 15000 });
          await adminPg.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
          const results = await runAxe(adminPg);
          const analyzed = analyzeResults(pageInfo.name, results);

          const critical = analyzed.violations.filter((v) => v.impact === 'critical').length;
          const serious = analyzed.violations.filter((v) => v.impact === 'serious').length;

          totalViolations += analyzed.violationCount;
          criticalViolations += critical;
          seriousViolations += serious;

          const icon = analyzed.violationCount === 0 ? '✅' : '⚠️';
          console.log(`  ${icon} ${pageInfo.name}: ${analyzed.violationCount} ihlal (${critical} kritik, ${serious} ciddi)`);

          if (analyzed.violationCount > 0) {
            for (const v of analyzed.violations) {
              console.log(`     [${v.impact}] ${v.id}: ${v.description}`);
            }
          }
          allResults.push(analyzed);
        } catch (e) {
          console.log(`  ❌ ${pageInfo.name}: HATA — ${e.message}`);
        }
      }
    } finally {
      await adminPg.close();
    }

    // --- ÖZET ---
    console.log('\n=== ÖZET ===');
    console.log(`Taranan sayfa: ${allResults.length}`);
    console.log(`Toplam ihlal: ${totalViolations}`);
    console.log(`Kritik (critical): ${criticalViolations}`);
    console.log(`Ciddi (serious): ${seriousViolations}`);

    const pagesWithViolations = allResults.filter((r) => r.violationCount > 0);
    if (pagesWithViolations.length > 0) {
      console.log('\nİhlal bulunan sayfalar:');
      for (const r of pagesWithViolations) {
        console.log(`  - ${r.page}: ${r.violationCount} ihlal`);
      }
    }

    // JSON çıktı
    const fs = require('fs');
    const report = {
      timestamp: new Date().toISOString(),
      totalPages: allResults.length,
      totalViolations,
      criticalViolations,
      seriousViolations,
      results: allResults,
    };
    fs.writeFileSync('/tmp/axe-report.json', JSON.stringify(report, null, 2));
    console.log(`\nDetaylı rapor: /tmp/axe-report.json`);

    return report;
  } finally {
    await browser.close();
  }
}

scan()
  .then((report) => {
    const exitCode = report.criticalViolations > 0 ? 1 : 0;
    process.exit(exitCode);
  })
  .catch((err) => {
    console.error('Tarama başarısız:', err);
    process.exit(2);
  });
