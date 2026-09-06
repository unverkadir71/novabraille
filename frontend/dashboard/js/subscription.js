// Nova Braille — Abonelik
//
// F4.6 — Hosted only. Mevcut plan + kullanılabilir planlar.
// API: GET /auth/me (plan_code), GET /plans (public)

(function () {
  "use strict";

  const subLoading = document.getElementById("sub-loading");
  const subContent = document.getElementById("sub-content");
  const subCurrentPlan = document.getElementById("sub-current-plan");
  const subCurrentStatus = document.getElementById("sub-current-status");
  const subPlans = document.getElementById("sub-plans");
  const statusEl = document.getElementById("sub-status");

  const PLAN_NAMES = {
    starter: "Başlangıç",
    professional: "Profesyonel",
    enterprise: "Kurumsal",
  };

  async function init() {
    let user;
    try {
      user = await window.NovaUi.requireAuth();
    } catch (err) {
      return;
    }

    document.getElementById("sidebar-user-name").textContent = user.display_name || user.email.split("@")[0];
    document.getElementById("sidebar-user-email").textContent = user.email;
    if (window.NovaUi.isAdmin(user)) {
      document.getElementById("nav-admin-section").hidden = false;
    }
    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));
    document.getElementById("logout-btn").addEventListener("click", window.NovaUi.logout);

    await loadData(user);
  }

  async function loadData(user) {
    try {
      const [plans] = await Promise.all([
        window.NovaApi.apiGet("/api/v1/plans"),
      ]);

      // Mevcut plan
      if (user.plan_code) {
        subCurrentPlan.textContent = PLAN_NAMES[user.plan_code] || user.plan_code;
        subCurrentStatus.textContent = "Plan kodu: " + user.plan_code;
      } else {
        subCurrentPlan.textContent = "Plan atanmamış";
        subCurrentStatus.textContent = "Self-hosted modda tüm özellikler sınırsızdır.";
      }

      // Kullanılabilir planlar
      renderPlans(plans);

      subLoading.hidden = true;
      subContent.hidden = false;
    } catch (err) {
      subLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "Abonelik bilgileri yüklenemedi: " + err.message, "error");
    }
  }

  function renderPlans(plans) {
    subPlans.innerHTML = "";
    if (!plans || plans.length === 0) {
      const empty = document.createElement("p");
      empty.className = "field-hint";
      empty.textContent = "Şu an görüntülenecek plan bulunmuyor.";
      subPlans.appendChild(empty);
      return;
    }

    plans.forEach(function (plan) {
      const card = document.createElement("div");
      card.className = "card";

      const name = document.createElement("h3");
      name.textContent = plan.name_tr;
      card.appendChild(name);

      const price = document.createElement("p");
      price.textContent = formatPrice(plan.price_monthly);
      price.className = "subscription-price";
      card.appendChild(price);

      if (plan.description_tr) {
        const desc = document.createElement("p");
        desc.className = "field-hint";
        desc.textContent = plan.description_tr;
        card.appendChild(desc);
      }

      subPlans.appendChild(card);
    });
  }

  function formatPrice(kurus) {
    if (!kurus) {
      return "Ücretsiz";
    }
    const lira = kurus / 100;
    return "₺" + lira.toLocaleString("tr-TR", { minimumFractionDigits: 2 }) + "/ay";
  }

  init();
})();
