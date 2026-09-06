// Nova Braille — Admin Paneli Ortak Yardımcıları
//
// F4.10+F7.7 — Admin layout. Admin guard + sidebar yönetimi + self-hosted sadeleştirme.
// Tüm admin sayfaları bu modülü kullanır.

(function () {
  "use strict";

  const ROLE_LABELS = {
    super_admin: "Süper Admin",
    admin: "Admin",
    billing: "Faturalama",
    support: "Destek",
    user: "Kullanıcı",
  };

  // Hosted-only nav item IDs — self-hosted'de gizlenir (ADR-012)
  const HOSTED_ONLY_NAV_IDS = [
    "nav-roles",
    "nav-plans",
    "nav-subscriptions",
    "nav-payments",
    "nav-revenue",
  ];

  // Hosted-only quick link IDs — admin index sayfasında
  const HOSTED_ONLY_QUICK_IDS = [
    "quick-plans",
    "quick-roles",
  ];

  /**
   * Admin guard + sidebar hazırlığı. Ortak başlatma.
   * @returns {Promise<object>} — kullanıcı bilgisi
   */
  async function initAdminShell() {
    let user;
    try {
      user = await window.NovaUi.requireAdmin();
    } catch (err) {
      throw err;
    }

    document.getElementById("sidebar-user-name").textContent =
      user.display_name || user.email.split("@")[0];
    document.getElementById("sidebar-user-email").textContent = user.email;

    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));

    // Self-hosted sadeleştirme — hosted-only nav öğelerini gizle
    await applySelfHostedSimplification();

    document.getElementById("logout-btn").addEventListener("click", async function () {
      try {
        await window.NovaApi.apiPost("/api/v1/auth/logout", {});
      } catch (err) {
        // ignore
      }
      window.location.href = "../login.html";
    });

    return user;
  }

  /**
   * Self-hosted modda hosted-only nav ve quick link öğelerini gizler.
   */
  async function applySelfHostedSimplification() {
    try {
      const res = await fetch("/api/v1/admin/mode", {
        headers: { "X-CSRF-Token": window.NovaApi.getCsrfToken() },
      });

      if (!res.ok) return;

      const data = await res.json();

      if (data.is_self_hosted) {
        // Sidebar nav öğelerini gizle
        HOSTED_ONLY_NAV_IDS.forEach(function (id) {
          const el = document.getElementById(id);
          if (el) el.hidden = true;
        });

        // Dashboard quick link'leri gizle
        HOSTED_ONLY_QUICK_IDS.forEach(function (id) {
          const el = document.getElementById(id);
          if (el) el.hidden = true;
        });

        // Metric plan kartını gizle
        const planCard = document.getElementById("metric-plans-card");
        if (planCard) planCard.hidden = true;
      }
    } catch (err) {
      // API erişilemezse sessizce devam et
    }
  }

  /**
   * Rol adını okunur etikete çevirir.
   */
  function roleLabel(role) {
    return ROLE_LABELS[role] || role;
  }

  window.NovaAdmin = {
    initAdminShell,
    roleLabel,
    ROLE_LABELS,
  };
})();
