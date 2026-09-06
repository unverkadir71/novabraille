// Nova Braille — Admin Genel Bakış
//
// F4.11 — Admin dashboard: metrikler ve sistem durumu.
// API: GET /admin/users (kullanıcı sayısı), GET /admin/plans (plan sayısı)

(function () {
  "use strict";

  const adminLoading = document.getElementById("admin-loading");
  const adminContent = document.getElementById("admin-content");
  const metricUsers = document.getElementById("metric-users");
  const metricPlans = document.getElementById("metric-plans");
  const metricPlansCard = document.getElementById("metric-plans-card");
  const metricMode = document.getElementById("metric-mode");
  const statusEl = document.getElementById("admin-status");

  async function init() {
    let user;
    try {
      user = await window.NovaAdmin.initAdminShell();
    } catch (err) {
      return;
    }

    metricMode.textContent = window.NovaUi.isAdmin(user) ? (user.role === "super_admin" ? "Hosted" : "Yönetilen") : "—";

    try {
      const users = await window.NovaApi.apiGet("/api/v1/admin/users");
      metricUsers.textContent = window.NovaUi.formatNumber(users.length);

      // Planlar yalnızca hosted modda; self-hosted'de 404
      try {
        const plans = await window.NovaApi.apiGet("/api/v1/admin/plans");
        metricPlans.textContent = window.NovaUi.formatNumber(plans.length);
        metricPlansCard.hidden = false;
      } catch (planErr) {
        // Self-hosted — planlar yok
        metricPlansCard.hidden = true;
      }

      adminLoading.hidden = true;
      adminContent.hidden = false;
    } catch (err) {
      adminLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "Veriler yüklenemedi: " + err.message, "error");
    }
  }

  init();
})();
