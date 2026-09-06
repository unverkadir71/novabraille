// Nova Braille — Profil Yönetimi v3
//
// F5.3 — Profil listeleme, oluşturma, güncelleme, silme.
// v3: Translate sayfasıyla uyumlu yapı. Optgroup ile tablo gruplama.
//     Dosya formatı seçimi eklendi. Progressive disclosure eklendi.

(function () {
  "use strict";

  // DOM referansları
  const profileCards = document.getElementById("profile-cards");
  const noProfilesMsg = document.getElementById("no-profiles-message");
  const profileForm = document.getElementById("profile-form");
  const profileFormCard = document.getElementById("profile-form-card");
  const newProfileBtn = document.getElementById("new-profile-btn");
  const formCancelBtn = document.getElementById("form-cancel-btn");
  const formSubmitBtn = document.getElementById("form-submit-btn");
  const formTitle = document.getElementById("form-title");
  const deleteDialog = document.getElementById("delete-dialog");
  const deleteConfirmBtn = document.getElementById("delete-confirm-btn");
  const deleteCancelBtn = document.getElementById("delete-cancel-btn");
  const deleteDialogMsg = document.getElementById("delete-dialog-message");
  const statusEl = document.getElementById("profiles-status");
  const pageSettingsGroup = document.getElementById("page-settings-group");
  const contractionGroup = document.getElementById("contraction-categories-group");
  const formatGroup = document.getElementById("format-group");

  // Form alanları
  const profileIdEl = document.getElementById("profile-id");
  const profileNameEl = document.getElementById("profile-name");
  const profileLocaleEl = document.getElementById("profile-locale");
  const profileTableEl = document.getElementById("profile-table");
  const profileModeEl = document.getElementById("profile-mode");
  const profileIsDefaultEl = document.getElementById("profile-is-default");
  const contractionChecks = document.getElementById("contraction-categories");
  const profileFormatEl = document.getElementById("profile-format");
  const profilePaperSize = document.getElementById("profile-paper-size");
  const profileCharsPerLine = document.getElementById("profile-chars-per-line");
  const profileLinesPerPage = document.getElementById("profile-lines-per-page");
  const profileTopMargin = document.getElementById("profile-top-margin");
  const profileBindingMargin = document.getElementById("profile-binding-margin");
  const profileInterpoint = document.getElementById("profile-interpoint");

  let profiles = [];
  let tablesByLang = {};
  let currentDeleteId = null;
  let modeFormats = {}; // mode → [{id, label_tr, ...}]

  // 8 öncelikli dil
  const PRIORITY_LANGUAGES = ["tr", "en", "de", "fr", "es", "ar", "ru", "pt"];
  const LANG_NAMES = { tr: "Türkçe", en: "English", de: "Deutsch", fr: "Français", es: "Español", ar: "العربية", ru: "Русский", pt: "Português" };

  const PAPER_DEFAULTS = {
    a4: { chars: 30, lines: 28 },
    letter: { chars: 30, lines: 25 },
    "11.5x11": { chars: 40, lines: 25 }
  };

  const MODE_LABELS = { display: "Braille Ekran", embosser: "Embosser (Yazıcı)", notetaker: "Nota Alıcı Cihaz" };

  // ── Mod → sayfa düzeni görünürlüğü ──────────────────────
  profileModeEl.addEventListener("change", function () {
    const needsPageSettings = this.value === "embosser" || this.value === "notetaker";
    pageSettingsGroup.hidden = !needsPageSettings;
    // Dosya formatlarını yükle
    renderProfileFormatOptions(this.value);
  });

  // Kağıt boyutu → otomatik değer doldur
  if (profilePaperSize) {
    profilePaperSize.addEventListener("change", function () {
      const def = PAPER_DEFAULTS[this.value];
      if (def) {
        if (profileCharsPerLine) profileCharsPerLine.value = def.chars;
        if (profileLinesPerPage) profileLinesPerPage.value = def.lines;
      }
    });
  }

  // Tablo → kısaltma kategorileri
  profileTableEl.addEventListener("change", function () {
    const opt = this.selectedOptions[0];
    if (opt && opt.value) {
      const contraction = opt.getAttribute("data-contraction") || "";
      const locale = profileLocaleEl.value;
      const hasContraction = contraction && contraction !== "false" && contraction !== "none" && contraction !== "no" && contraction !== "";

      if (hasContraction && locale) {
        showContractionCategories(locale);
      } else {
        contractionGroup.hidden = true;
      }
    } else {
      contractionGroup.hidden = true;
    }
  });

  // ── Başlangıç ─────────────────────────────────────────

  async function init() {
    let user;
    try {
      user = await window.NovaUi.requireAuth();
    } catch (err) {
      return;
    }

    document.getElementById("sidebar-user-name").textContent =
      user.display_name || user.email.split("@")[0];
    document.getElementById("sidebar-user-email").textContent = user.email;
    if (window.NovaUi.isAdmin(user)) {
      document.getElementById("nav-admin-section").hidden = false;
    }
    if (user.plan_code) {
      document.getElementById("nav-subscription").hidden = false;
    }
    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));
    document.getElementById("logout-btn").addEventListener("click", window.NovaUi.logout);

    // Event listeners
    newProfileBtn.addEventListener("click", openNewProfileForm);
    formCancelBtn.addEventListener("click", closeForm);
    profileForm.addEventListener("submit", handleFormSubmit);
    deleteCancelBtn.addEventListener("click", closeDeleteDialog);
    deleteConfirmBtn.addEventListener("click", confirmDelete);
    profileLocaleEl.addEventListener("change", onLocaleChange);

    loadLanguages();
    await loadModes();
    await loadProfiles();
  }

  // ── Dil ve tablo verileri ─────────────────────────────

  function loadLanguages() {
    profileLocaleEl.innerHTML = '<option value="">— Seçin —</option>';
    for (const code of PRIORITY_LANGUAGES) {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = LANG_NAMES[code] || code;
      profileLocaleEl.appendChild(opt);
    }
  }

  async function onLocaleChange() {
    const locale = profileLocaleEl.value;
    profileTableEl.innerHTML = '<option value="">— Yükleniyor… —</option>';

    if (!locale) {
      profileTableEl.innerHTML = '<option value="">Tablo seçin…</option>';
      contractionChecks.innerHTML = "";
      contractionGroup.hidden = true;
      return;
    }

    try {
      const data = await window.NovaApi.apiGet(
        "/api/v1/tables?language=" + encodeURIComponent(locale) + "&priority_only=true"
      );
      tablesByLang[locale] = data;
      renderTableOptions(data);
    } catch (err) {
      profileTableEl.innerHTML = '<option value="">— Yüklenemedi —</option>';
    }
  }

  function renderTableOptions(tables) {
    // Tabloları kısaltmasız/kısaltmalı olarak optgroup ile grupla
    profileTableEl.innerHTML = '<option value="">Tablo seçin…</option>';

    const uncontracted = [];
    const contracted = [];
    for (const t of tables) {
      const hasContraction = t.contraction && t.contraction !== "false" && t.contraction !== "none" && t.contraction !== "no" && t.contraction !== "";
      if (hasContraction) {
        contracted.push(t);
      } else {
        uncontracted.push(t);
      }
    }

    if (uncontracted.length > 0) {
      const og = document.createElement("optgroup");
      og.label = "Kısaltmasız Tablolar";
      for (const t of uncontracted) {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.name_tr || t.name || t.id;
        opt.setAttribute("data-contraction", "");
        og.appendChild(opt);
      }
      profileTableEl.appendChild(og);
    }

    if (contracted.length > 0) {
      const og = document.createElement("optgroup");
      og.label = "Kısaltmalı Tablolar";
      for (const t of contracted) {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.name_tr || t.name || t.id;
        opt.setAttribute("data-contraction", t.contraction || "");
        og.appendChild(opt);
      }
      profileTableEl.appendChild(og);
    }
  }

  // ── Çıktı modları ve formatları ───────────────────────

  async function loadModes() {
    try {
      const modes = await window.NovaApi.apiGet("/api/v1/output/modes");
      modeFormats = {};
      for (const m of modes) {
        if (m.file_formats && m.file_formats.length > 0) {
          modeFormats[m.id] = m.file_formats;
        }
      }
    } catch (err) { /* sessiz */ }
  }

  function renderProfileFormatOptions(modeId) {
    if (!profileFormatEl || !formatGroup) return;

    const formats = modeFormats[modeId];
    if (!formats || formats.length === 0) {
      formatGroup.hidden = true;
      return;
    }

    profileFormatEl.innerHTML = '<option value="">— Seçin —</option>';
    for (const fmt of formats) {
      const opt = document.createElement("option");
      opt.value = fmt.id;
      let label = fmt.label_tr;
      if (fmt.recommended) label += " (Önerilen)";
      opt.textContent = label;
      profileFormatEl.appendChild(opt);
    }

    formatGroup.hidden = false;
  }

  // ── Kısaltma kategorileri ─────────────────────────────

  async function loadContractionCategories(locale) {
    contractionChecks.innerHTML = "";
    try {
      const data = await window.NovaApi.apiGet(
        "/api/v1/contractions/" + encodeURIComponent(locale) + "/categories"
      );
      if (data && data.length > 0) {
        for (const cat of data) {
          const label = document.createElement("label");
          label.className = "checkbox-label";
          const input = document.createElement("input");
          input.type = "checkbox";
          input.value = cat.id;
          input.name = "contraction-cat";
          const span = document.createElement("span");
          span.textContent = cat.label_tr || cat.label || cat.id;
          label.appendChild(input);
          label.appendChild(span);
          contractionChecks.appendChild(label);
        }
        return true;
      }
    } catch (err) {
      // Kısaltma kategorileri yüklenemezse boş bırak
    }
    return false;
  }

  async function showContractionCategories(locale) {
    if (contractionChecks.children.length === 0) {
      const ok = await loadContractionCategories(locale);
      contractionGroup.hidden = !ok;
    } else {
      contractionGroup.hidden = false;
    }
  }

  // ── Profil yükleme ve görüntüleme ─────────────────────

  async function loadProfiles() {
    try {
      profiles = await window.NovaApi.apiGet("/api/v1/profiles");
      renderProfileList();
    } catch (err) {
      window.NovaUi.showStatus(statusEl, "Profiller yüklenirken hata oluştu.", "error");
      profiles = [];
      renderProfileList();
    }
  }

  function renderProfileList() {
    profileCards.innerHTML = "";
    if (profiles.length === 0) {
      noProfilesMsg.hidden = false;
      document.getElementById("profile-list-section").querySelector(".section-title").hidden = true;
      return;
    }
    noProfilesMsg.hidden = true;
    document.getElementById("profile-list-section").querySelector(".section-title").hidden = false;

    for (const p of profiles) {
      const card = createProfileCard(p);
      profileCards.appendChild(card);
    }
  }

  function createProfileCard(p) {
    const card = document.createElement("div");
    card.className = "card profile-card";
    card.setAttribute("role", "listitem");

    const defaultBadge = p.is_default
      ? '<span class="badge badge-default">Varsayılan</span>'
      : "";

    let contractionsText = "—";
    if (p.contraction_categories) {
      try {
        const cats = typeof p.contraction_categories === "string"
          ? JSON.parse(p.contraction_categories)
          : p.contraction_categories;
        contractionsText = Array.isArray(cats) ? cats.join(", ") : "—";
      } catch (e) {
        contractionsText = "—";
      }
    }

    // Format etiketini bul
    let formatLabel = "—";
    if (p.output_format && modeFormats[p.mode]) {
      const fmt = modeFormats[p.mode].find(function (f) { return f.id === p.output_format; });
      if (fmt) formatLabel = fmt.label_tr;
      else formatLabel = p.output_format;
    }

    card.innerHTML =
      '<div class="profile-card-header">' +
        '<h3>' + escapeHtml(p.name) + '</h3>' +
        defaultBadge +
      '</div>' +
      '<dl class="info-list profile-details">' +
        '<dt>Dil</dt><dd>' + escapeHtml(p.locale) + '</dd>' +
        '<dt>Tablo</dt><dd>' + escapeHtml(p.table_id) + '</dd>' +
        '<dt>Mod</dt><dd>' + (MODE_LABELS[p.mode] || p.mode) + '</dd>' +
        '<dt>Format</dt><dd>' + formatLabel + '</dd>' +
        '<dt>Kategoriler</dt><dd>' + contractionsText + '</dd>' +
        '<dt>Oluşturma</dt><dd>' + window.NovaUi.formatDate(p.created_at) + '</dd>' +
      '</dl>' +
      '<div class="profile-card-actions">' +
        '<button type="button" class="btn btn-sm btn-ghost" data-action="edit" data-id="' + p.id + '" aria-label="' + escapeHtml(p.name) + ' profilini düzenle">Düzenle</button>' +
        '<button type="button" class="btn btn-sm btn-ghost" data-action="delete" data-id="' + p.id + '" aria-label="' + escapeHtml(p.name) + ' profilini sil">Sil</button>' +
        (!p.is_default
          ? '<button type="button" class="btn btn-sm btn-ghost" data-action="default" data-id="' + p.id + '" aria-label="' + escapeHtml(p.name) + ' varsayılan yap">Varsayılan Yap</button>'
          : "") +
      '</div>';

    card.querySelector('[data-action="edit"]').addEventListener("click", function () {
      editProfile(this.dataset.id);
    });
    card.querySelector('[data-action="delete"]').addEventListener("click", function () {
      openDeleteDialog(this.dataset.id);
    });
    const defaultBtn2 = card.querySelector('[data-action="default"]');
    if (defaultBtn2) {
      defaultBtn2.addEventListener("click", function () {
        setDefaultProfile(this.dataset.id);
      });
    }

    return card;
  }

  // ── Form işlemleri ────────────────────────────────────

  async function openNewProfileForm() {
    resetForm();
    formTitle.textContent = "Yeni Profil";
    formSubmitBtn.textContent = "Kaydet";
    profileFormCard.hidden = false;
    profileFormCard.scrollIntoView({ behavior: "smooth" });
    profileNameEl.focus();
    newProfileBtn.setAttribute("aria-expanded", "true");
  }

  function editProfile(id) {
    const p = profiles.find(function (pr) { return pr.id === id; });
    if (!p) return;

    resetForm();
    profileIdEl.value = p.id;
    profileNameEl.value = p.name;
    setSelectValue(profileLocaleEl, p.locale);

    // Tabloları yükle, sonra tablo değerini set et
    onLocaleChange().then(function () {
      setSelectValue(profileTableEl, p.table_id);

      // Kısaltma checkbox'larını işaretle
      if (p.contraction_categories) {
        setTimeout(function () {
          const cats = typeof p.contraction_categories === "string"
            ? JSON.parse(p.contraction_categories)
            : p.contraction_categories;
          const checks = contractionChecks.querySelectorAll('input[type="checkbox"]');
          for (const check of checks) {
            check.checked = Array.isArray(cats) && cats.indexOf(check.value) !== -1;
          }
        }, 300);
      }
    });

    setSelectValue(profileModeEl, p.mode);
    // Mod change event formatları yükler

    // Çıktı formatı
    if (p.output_format && profileFormatEl) {
      setTimeout(function () {
        for (let i = 0; i < profileFormatEl.options.length; i++) {
          if (profileFormatEl.options[i].value === p.output_format) {
            profileFormatEl.selectedIndex = i;
            break;
          }
        }
      }, 100);
    }

    profileIsDefaultEl.checked = p.is_default;

    // Sayfa düzeni
    if (p.page_settings) {
      const ps = typeof p.page_settings === "string"
        ? JSON.parse(p.page_settings) : p.page_settings;
      if (ps.paper_size && profilePaperSize) profilePaperSize.value = ps.paper_size;
      if (ps.chars_per_line && profileCharsPerLine) profileCharsPerLine.value = ps.chars_per_line;
      if (ps.lines_per_page && profileLinesPerPage) profileLinesPerPage.value = ps.lines_per_page;
      if (ps.top_margin !== undefined && profileTopMargin) profileTopMargin.value = ps.top_margin;
      if (ps.binding_margin !== undefined && profileBindingMargin) profileBindingMargin.value = ps.binding_margin;
      if (profileInterpoint) profileInterpoint.checked = !!ps.interpoint;
      if (p.mode === "embosser" || p.mode === "notetaker") {
        pageSettingsGroup.hidden = false;
      }
    }

    formTitle.textContent = "Profili Düzenle";
    formSubmitBtn.textContent = "Güncelle";
    profileFormCard.hidden = false;
    profileFormCard.scrollIntoView({ behavior: "smooth" });
    profileNameEl.focus();
    newProfileBtn.setAttribute("aria-expanded", "true");
  }

  function closeForm() {
    profileFormCard.hidden = true;
    resetForm();
    newProfileBtn.setAttribute("aria-expanded", "false");
    window.NovaUi.showStatus(statusEl, "", "");
  }

  function resetForm() {
    profileForm.reset();
    profileIdEl.value = "";
    profileIsDefaultEl.checked = false;
    pageSettingsGroup.hidden = true;
    contractionGroup.hidden = true;
    if (formatGroup) formatGroup.hidden = true;
    profileTableEl.innerHTML = '<option value="">Tablo seçin…</option>';
    contractionChecks.innerHTML = "";
    if (profileFormatEl) { profileFormatEl.innerHTML = '<option value="">— Seçin —</option>'; }
    if (profilePaperSize) profilePaperSize.value = "";
    if (profileCharsPerLine) profileCharsPerLine.value = "";
    if (profileLinesPerPage) profileLinesPerPage.value = "";
    if (profileTopMargin) profileTopMargin.value = "";
    if (profileBindingMargin) profileBindingMargin.value = "";
    if (profileInterpoint) profileInterpoint.checked = false;
  }

  async function handleFormSubmit(e) {
    e.preventDefault();

    const profileId = profileIdEl.value;
    const name = profileNameEl.value.trim();
    const locale = profileLocaleEl.value;
    const tableId = profileTableEl.value;
    const mode = profileModeEl.value;
    const outputFormat = profileFormatEl ? profileFormatEl.value : "";
    const isDefault = profileIsDefaultEl.checked;

    // Kısaltma kategorileri
    const checks = contractionChecks.querySelectorAll('input[type="checkbox"]:checked');
    const categories = Array.from(checks).map(function (c) { return c.value; });

    // Sayfa düzeni (sadece kağıt boyutu seçilmişse kaydet)
    let pageSettings = null;
    if ((mode === "embosser" || mode === "notetaker") && profilePaperSize.value) {
      pageSettings = {
        paper_size: profilePaperSize.value,
        chars_per_line: parseInt(profileCharsPerLine.value, 10) || 30,
        lines_per_page: parseInt(profileLinesPerPage.value, 10) || 28,
        top_margin: parseInt(profileTopMargin.value, 10) || 0,
        binding_margin: parseInt(profileBindingMargin.value, 10) || 0,
        interpoint: profileInterpoint.checked || false
      };
    }

    const payload = {
      name: name,
      locale: locale,
      table_id: tableId,
      mode: mode,
      grade: "grade2",
      is_default: isDefault,
    };
    if (categories.length > 0) {
      payload.contraction_categories = categories;
    }
    if (outputFormat) {
      payload.output_format = outputFormat;
    }
    if (pageSettings) {
      payload.page_settings = pageSettings;
    }

    try {
      if (profileId) {
        await window.NovaApi.apiPut("/api/v1/profiles/" + profileId, payload);
      } else {
        await window.NovaApi.apiPost("/api/v1/profiles", payload);
      }

      window.NovaUi.showStatus(
        statusEl,
        profileId ? "Profil güncellendi." : "Profil oluşturuldu.",
        "success"
      );
      closeForm();
      await loadProfiles();
    } catch (err) {
      let msg = err.message || "Bir hata oluştu.";
      if (err.code === "PROFILE_LIMIT_REACHED") {
        msg = err.message;
      }
      window.NovaUi.showStatus(statusEl, msg, "error");
    }
  }

  // ── Silme ─────────────────────────────────────────────

  function openDeleteDialog(id) {
    const p = profiles.find(function (pr) { return pr.id === id; });
    if (!p) return;
    currentDeleteId = id;
    deleteDialogMsg.textContent = '"' + p.name + '" profili silinecek. Bu işlem geri alınamaz.';
    deleteDialog.hidden = false;
    deleteConfirmBtn.focus();
  }

  function closeDeleteDialog() {
    deleteDialog.hidden = true;
    currentDeleteId = null;
  }

  async function confirmDelete() {
    if (!currentDeleteId) return;
    try {
      await window.NovaApi.apiDelete("/api/v1/profiles/" + currentDeleteId);
      window.NovaUi.showStatus(statusEl, "Profil silindi.", "success");
      closeDeleteDialog();
      await loadProfiles();
    } catch (err) {
      let msg = err.message || "Silme sırasında hata oluştu.";
      if (err.code === "LAST_PROFILE") {
        msg = err.message;
      }
      window.NovaUi.showStatus(statusEl, msg, "error");
      closeDeleteDialog();
    }
  }

  // ── Varsayılan yap ────────────────────────────────────

  async function setDefaultProfile(id) {
    try {
      await window.NovaApi.apiPut("/api/v1/profiles/" + id, { is_default: true });
      window.NovaUi.showStatus(statusEl, "Varsayılan profil güncellendi.", "success");
      await loadProfiles();
    } catch (err) {
      window.NovaUi.showStatus(statusEl, err.message || "Hata oluştu.", "error");
    }
  }

  // ── Yardımcılar ──────────────────────────────────────

  function setSelectValue(selectEl, value) {
    if (!value) return;
    for (let i = 0; i < selectEl.options.length; i++) {
      if (selectEl.options[i].value === value) {
        selectEl.selectedIndex = i;
        selectEl.dispatchEvent(new Event("change"));
        return;
      }
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  init();
})();