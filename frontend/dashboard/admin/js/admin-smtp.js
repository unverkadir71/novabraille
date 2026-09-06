// Nova Braille — Admin SMTP Ayarları (ADR-023)
//
// SMTP ayarlarını görüntüleme, düzenleme, etkinleştirme/devre dışı bırakma,
// test e-postası gönderme.

(function () {
  "use strict";

  const form = document.getElementById("smtp-form");
  const enabledToggle = document.getElementById("smtp-enabled");
  const tlsToggle = document.getElementById("smtp-tls");
  const hostInput = document.getElementById("smtp-host");
  const portInput = document.getElementById("smtp-port");
  const usernameInput = document.getElementById("smtp-username");
  const passwordInput = document.getElementById("smtp-password");
  const fromNameInput = document.getElementById("smtp-from-name");
  const fromEmailInput = document.getElementById("smtp-from-email");
  const saveBtn = document.getElementById("save-btn");
  const testBtn = document.getElementById("test-btn");
  const statusEl = document.getElementById("smtp-status");
  const passwordStatus = document.getElementById("password-status");
  const passwordHint = document.getElementById("password-hint");

  let currentConfig = null;

  async function init() {
    try {
      await window.NovaUi.requireAuth();
    } catch {
      return;
    }

    // Load current config
    await loadConfig();
    bindEvents();
  }

  async function loadConfig() {
    try {
      const res = await fetch("/api/v1/admin/smtp", {
        headers: { "X-CSRF-Token": window.NovaApi.getCsrfToken() },
      });
      if (!res.ok) {
        showStatus("SMTP ayarları yüklenemedi. Yönetici yetkiniz olmayabilir.", "error");
        return;
      }
      currentConfig = await res.json();
      populateForm();
    } catch {
      showStatus("Bağlantı hatası.", "error");
    }
  }

  function populateForm() {
    if (!currentConfig) return;

    setToggle(enabledToggle, currentConfig.enabled);
    hostInput.value = currentConfig.host || "";
    portInput.value = currentConfig.port || 587;
    usernameInput.value = currentConfig.username || "";
    fromNameInput.value = currentConfig.from_name || "";
    fromEmailInput.value = currentConfig.from_email || "";
    setToggle(tlsToggle, currentConfig.use_tls);

    // Şifre durumu
    if (currentConfig.password_set) {
      passwordStatus.textContent = "(kayıtlı şifre mevcut)";
      passwordStatus.className = "text-ok";
    } else {
      passwordStatus.textContent = "(şifre kaydedilmemiş)";
      passwordStatus.className = "text-muted";
    }

    updateFieldStates();
  }

  function updateFieldStates() {
    const enabled = isToggleOn(enabledToggle);
    const fields = [hostInput, portInput, usernameInput, passwordInput,
                    fromNameInput, fromEmailInput, tlsToggle];
    fields.forEach(function (el) {
      el.disabled = !enabled;
    });
    saveBtn.disabled = false;
    testBtn.disabled = !enabled;
  }

  function bindEvents() {
    enabledToggle.addEventListener("click", function () {
      toggle(enabledToggle);
      updateFieldStates();
    });

    tlsToggle.addEventListener("click", function () {
      toggle(tlsToggle);
    });

    form.addEventListener("submit", handleSubmit);
    testBtn.addEventListener("click", handleTest);
  }

  // ── Toggle helpers ──

  function isToggleOn(el) {
    return el.getAttribute("aria-checked") === "true";
  }

  function setToggle(el, on) {
    el.setAttribute("aria-checked", on ? "true" : "false");
  }

  function toggle(el) {
    setToggle(el, !isToggleOn(el));
  }

  // ── Submit ──

  async function handleSubmit(e) {
    e.preventDefault();
    statusEl.textContent = "";
    statusEl.className = "status-message";

    const body = {
      enabled: isToggleOn(enabledToggle),
      host: hostInput.value.trim(),
      port: parseInt(portInput.value, 10) || 587,
      username: usernameInput.value.trim(),
      from_name: fromNameInput.value.trim(),
      from_email: fromEmailInput.value.trim(),
      use_tls: isToggleOn(tlsToggle),
    };

    // Şifre: boşsa gönderme (mevcut korunur)
    const pw = passwordInput.value;
    if (pw) {
      body.password = pw;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Kaydediliyor…";

    try {
      const res = await fetch("/api/v1/admin/smtp", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": window.NovaApi.getCsrfToken(),
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (res.ok) {
        currentConfig = data;
        passwordInput.value = "";
        populateForm();
        showStatus("SMTP ayarları kaydedildi.", "success");
      } else {
        const detail = data.detail || {};
        showStatus(detail.message || "Kaydetme başarısız.", "error");
      }
    } catch {
      showStatus("Bağlantı hatası.", "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Ayarları Kaydet";
    }
  }

  // ── Test ──

  async function handleTest() {
    statusEl.textContent = "Test e-postası gönderiliyor…";
    statusEl.className = "status-message status-info";

    testBtn.disabled = true;
    testBtn.textContent = "Gönderiliyor…";

    try {
      const res = await fetch("/api/v1/admin/smtp/test", {
        method: "POST",
        headers: { "X-CSRF-Token": window.NovaApi.getCsrfToken() },
      });

      const data = await res.json();

      if (data.success) {
        showStatus(data.message, "success");
      } else {
        showStatus(data.message || "Test e-postası gönderilemedi.", "error");
      }
    } catch {
      showStatus("Bağlantı hatası.", "error");
    } finally {
      testBtn.disabled = false;
      testBtn.textContent = "Test E-postası Gönder";
    }
  }

  function showStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = "status-message status-" + type;
  }

  init();
})();
