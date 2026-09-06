// Nova Braille — Admin Plan Yönetimi
//
// F4.14 — Hosted only. Plan CRUD.
// API:
//   GET    /admin/plans          → listele (entitlement'larla)
//   POST   /admin/plans          → oluştur
//   PUT    /admin/plans/{code}   → güncelle
//   DELETE /admin/plans/{code}   → arşivle

(function () {
  "use strict";

  const plansLoading = document.getElementById("plans-loading");
  const plansList = document.getElementById("plans-list");
  const form = document.getElementById("plan-form");
  const formTitle = document.getElementById("plan-form-title");
  const codeInput = document.getElementById("plan-code");
  const sortInput = document.getElementById("plan-sort");
  const nameTrInput = document.getElementById("plan-name-tr");
  const nameEnInput = document.getElementById("plan-name-en");
  const priceMonthlyInput = document.getElementById("plan-price-monthly");
  const priceAnnualInput = document.getElementById("plan-price-annual");
  const descTrInput = document.getElementById("plan-desc-tr");
  const descEnInput = document.getElementById("plan-desc-en");
  const maxCharsInput = document.getElementById("ent-max-chars");
  const maxProfilesInput = document.getElementById("ent-max-profiles");
  const saveBtn = document.getElementById("plan-save-btn");
  const cancelBtn = document.getElementById("plan-cancel-btn");
  const statusEl = document.getElementById("plans-status");

  let plans = [];
  let editingCode = null;

  async function init() {
    try {
      await window.NovaAdmin.initAdminShell();
    } catch (err) {
      return;
    }

    form.addEventListener("submit", savePlan);
    cancelBtn.addEventListener("click", resetForm);

    await loadPlans();
  }

  async function loadPlans() {
    plansLoading.hidden = false;
    plansList.innerHTML = "";
    try {
      plans = await window.NovaApi.apiGet("/api/v1/admin/plans");
      plansLoading.hidden = true;
      renderPlans();
    } catch (err) {
      plansLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "Planlar yüklenemedi: " + err.message, "error");
    }
  }

  function renderPlans() {
    plansList.innerHTML = "";
    if (plans.length === 0) {
      const empty = document.createElement("div");
      empty.className = "state-box";
      empty.textContent = "Henüz plan yok.";
      plansList.appendChild(empty);
      return;
    }

    plans.forEach(function (plan) {
      const card = document.createElement("div");
      card.className = "card plan-card";

      const name = document.createElement("h3");
      name.textContent = plan.name_tr;
      card.appendChild(name);

      const code = document.createElement("p");
      code.className = "field-hint";
      code.textContent = plan.plan_code;
      card.appendChild(code);

      const price = document.createElement("p");
      price.className = "subscription-price";
      price.textContent = formatPrice(plan.price_monthly);
      card.appendChild(price);

      const status = document.createElement("p");
      const badge = document.createElement("span");
      badge.className = "badge " + (plan.is_active ? "badge-active" : "badge-closed");
      badge.textContent = plan.is_active ? "Aktif" : "Arşivlenmiş";
      status.appendChild(badge);
      card.appendChild(status);

      const actions = document.createElement("div");
      actions.className = "btn-group";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn btn-secondary";
      editBtn.textContent = "Düzenle";
      editBtn.addEventListener("click", function () { editPlan(plan); });
      actions.appendChild(editBtn);

      const archiveBtn = document.createElement("button");
      archiveBtn.type = "button";
      archiveBtn.className = "btn btn-danger";
      archiveBtn.textContent = "Arşivle";
      archiveBtn.addEventListener("click", function () { archivePlan(plan.plan_code); });
      actions.appendChild(archiveBtn);

      card.appendChild(actions);
      plansList.appendChild(card);
    });
  }

  function editPlan(plan) {
    editingCode = plan.plan_code;
    formTitle.textContent = "Planı Düzenle: " + plan.plan_code;
    codeInput.value = plan.plan_code;
    codeInput.disabled = true;
    sortInput.value = plan.sort_order || 0;
    nameTrInput.value = plan.name_tr;
    nameEnInput.value = plan.name_en;
    priceMonthlyInput.value = plan.price_monthly;
    priceAnnualInput.value = plan.price_annual;
    descTrInput.value = plan.description_tr || "";
    descEnInput.value = plan.description_en || "";
    maxCharsInput.value = plan.entitlements.max_chars !== undefined ? plan.entitlements.max_chars : 50000;
    maxProfilesInput.value = plan.entitlements.max_profiles !== undefined ? plan.entitlements.max_profiles : 3;
    saveBtn.textContent = "Güncelle";
    cancelBtn.hidden = false;
  }

  function resetForm() {
    editingCode = null;
    formTitle.textContent = "Yeni Plan";
    form.reset();
    codeInput.disabled = false;
    sortInput.value = 0;
    saveBtn.textContent = "Kaydet";
    cancelBtn.hidden = true;
  }

  async function savePlan(event) {
    event.preventDefault();

    const planCode = codeInput.value.trim();
    if (!planCode || !/^[a-z0-9_]+$/.test(planCode)) {
      window.NovaUi.showStatus(statusEl, "Geçerli bir plan kodu girin (küçük harf, rakam, alt çizgi).", "error");
      codeInput.focus();
      return;
    }

    const entitlements = {
      max_chars: parseInt(maxCharsInput.value, 10) || 0,
      max_profiles: parseInt(maxProfilesInput.value, 10) || 0,
    };

    const payload = {
      plan_code: planCode,
      name_tr: nameTrInput.value.trim(),
      name_en: nameEnInput.value.trim(),
      description_tr: descTrInput.value.trim() || null,
      description_en: descEnInput.value.trim() || null,
      price_monthly: parseInt(priceMonthlyInput.value, 10) || 0,
      price_annual: parseInt(priceAnnualInput.value, 10) || 0,
      sort_order: parseInt(sortInput.value, 10) || 0,
      entitlements: entitlements,
    };

    saveBtn.disabled = true;
    window.NovaUi.showStatus(statusEl, "", null);

    try {
      if (editingCode) {
        await window.NovaApi.apiPut("/api/v1/admin/plans/" + editingCode, payload);
        window.NovaUi.showStatus(statusEl, "Plan güncellendi.", "success");
      } else {
        await window.NovaApi.apiPost("/api/v1/admin/plans", payload);
        window.NovaUi.showStatus(statusEl, "Plan oluşturuldu.", "success");
      }
      resetForm();
      await loadPlans();
    } catch (err) {
      window.NovaUi.showStatus(statusEl, "Kayıt başarısız: " + err.message, "error");
    } finally {
      saveBtn.disabled = false;
    }
  }

  async function archivePlan(planCode) {
    const confirmed = window.confirm("Bu planı arşivlemek istediğinize emin misiniz?");
    if (!confirmed) {
      return;
    }
    try {
      await window.NovaApi.apiDelete("/api/v1/admin/plans/" + planCode);
      window.NovaUi.showStatus(statusEl, "Plan arşivlendi.", "success");
      await loadPlans();
    } catch (err) {
      window.NovaUi.showStatus(statusEl, "Arşivleme başarısız: " + err.message, "error");
    }
  }

  function formatPrice(kurus) {
    return "₺" + (kurus / 100).toLocaleString("tr-TR", { minimumFractionDigits: 2 }) + "/ay";
  }

  init();
})();
