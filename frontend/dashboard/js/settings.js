// Nova Braille — Ayarlar + Hesap Düzenleme
//
// F4.7 + F6.9 — Hesap bilgisi görüntüleme ve düzenleme (ADR-021).
// Tema ve dil tercihleri header'da (shared/js/preferences.js) yönetilir.

(function () {
  "use strict";

  const form = document.getElementById("account-form");
  const displayNameInput = document.getElementById("display-name");
  const emailInput = document.getElementById("email");
  const newPasswordInput = document.getElementById("new-password");
  const newPasswordConfirmInput = document.getElementById("new-password-confirm");
  const currentPasswordInput = document.getElementById("current-password");
  const saveBtn = document.getElementById("save-btn");
  const resetBtn = document.getElementById("reset-btn");
  const statusEl = document.getElementById("settings-status");
  const encryptionWarning = document.getElementById("encryption-warning");
  const accountInfo = document.getElementById("account-info");

  const STATUS_LABELS = {
    active: "Aktif",
    pending: "Beklemede",
    suspended: "Askıya alınmış",
    closed: "Kapatılmış",
  };

  const PLAN_LABELS = {
    starter: "Başlangıç",
    professional: "Profesyonel",
    enterprise: "Kurumsal",
  };

  let currentUser = null;

  async function init() {
    try {
      currentUser = await window.NovaUi.requireAuth();
    } catch (err) {
      return;
    }

    // Sidebar
    document.getElementById("sidebar-user-name").textContent =
      currentUser.display_name || currentUser.email.split("@")[0];
    document.getElementById("sidebar-user-email").textContent = currentUser.email;
    if (window.NovaUi.isAdmin(currentUser)) {
      document.getElementById("nav-admin-section").hidden = false;
    }
    if (currentUser.plan_code) {
      document.getElementById("nav-subscription").hidden = false;
    }
    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));
    document.getElementById("logout-btn").addEventListener("click", window.NovaUi.logout);

    populateForm();
    renderAccountInfo();
    bindEvents();
  }

  function populateForm() {
    displayNameInput.value = currentUser.display_name || "";
    emailInput.value = currentUser.email || "";
    // Parola alanları boş başlar
  }

  function renderAccountInfo() {
    accountInfo.innerHTML = "";
    addInfoRow("Durum", STATUS_LABELS[currentUser.status] || currentUser.status);
    addInfoRow("Plan", currentUser.plan_code ? (PLAN_LABELS[currentUser.plan_code] || currentUser.plan_code) : "—");
    addInfoRow("Kayıt Tarihi", window.NovaUi.formatDate(currentUser.created_at));
  }

  function addInfoRow(label, value) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    accountInfo.appendChild(dt);
    accountInfo.appendChild(dd);
  }

  function bindEvents() {
    form.addEventListener("submit", handleSubmit);
    resetBtn.addEventListener("click", function () {
      populateForm();
      statusEl.textContent = "";
      statusEl.className = "status-message";
      encryptionWarning.hidden = true;
    });

    // Parola alanlarına yazıldığında şifreleme uyarısı göster
    newPasswordInput.addEventListener("input", function () {
      encryptionWarning.hidden = this.value.length === 0;
    });
    newPasswordConfirmInput.addEventListener("input", function () {
      encryptionWarning.hidden = newPasswordInput.value.length === 0 && this.value.length === 0;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    statusEl.textContent = "";
    statusEl.className = "status-message";

    // Validasyon
    const currentPassword = currentPasswordInput.value.trim();
    if (!currentPassword) {
      showStatus("Mevcut parolanızı girin.", "error");
      currentPasswordInput.focus();
      return;
    }

    // Hangi alanlar değişti?
    const body = { current_password: currentPassword };
    let hasChanges = false;

    const newDisplayName = displayNameInput.value.trim();
    if (newDisplayName !== (currentUser.display_name || "")) {
      body.display_name = newDisplayName || null;
      hasChanges = true;
    }

    const newEmail = emailInput.value.trim();
    if (newEmail && newEmail !== currentUser.email) {
      body.email = newEmail;
      hasChanges = true;
    }

    const newPassword = newPasswordInput.value;
    if (newPassword) {
      if (newPassword.length < 8) {
        showStatus("Yeni parola en az 8 karakter olmalıdır.", "error");
        newPasswordInput.focus();
        return;
      }
      const confirmPassword = newPasswordConfirmInput.value;
      if (newPassword !== confirmPassword) {
        showStatus("Yeni parolalar eşleşmiyor.", "error");
        newPasswordConfirmInput.focus();
        return;
      }
      body.new_password = newPassword;
      hasChanges = true;
    }

    if (!hasChanges) {
      showStatus("Değişiklik yapmadınız.", "info");
      return;
    }

    // Gönder
    saveBtn.disabled = true;
    saveBtn.textContent = "Kaydediliyor…";

    try {
      const res = await fetch("/api/v1/account", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": window.NovaApi.getCsrfToken(),
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (res.ok) {
        showStatus("Hesap bilgileriniz güncellendi.", "success");

        // Form ve sidebar'ı güncelle
        if (data.user) {
          if (data.user.display_name) {
            currentUser.display_name = data.user.display_name;
            document.getElementById("sidebar-user-name").textContent =
              data.user.display_name;
          }
          if (data.user.email) {
            currentUser.email = data.user.email;
            document.getElementById("sidebar-user-email").textContent =
              data.user.email;
          }
          populateForm();
          renderAccountInfo();
        }

        // Parola alanlarını temizle
        newPasswordInput.value = "";
        newPasswordConfirmInput.value = "";
        currentPasswordInput.value = "";
        encryptionWarning.hidden = true;
      } else {
        const detail = data.detail || {};
        const msg = detail.message || "Bir hata oluştu.";
        showStatus(msg, "error");
        if (detail.code === "WRONG_PASSWORD") {
          currentPasswordInput.focus();
        }
      }
    } catch (err) {
      showStatus("Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin.", "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Değişiklikleri Kaydet";
    }
  }

  function showStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = "status-message status-" + type;
  }

  init();
})();
