// Nova Braille — Çeviri Arayüzü (Sekmeli + Çeviri Yöntemi Seçici)
//
// İki sekme:
//   Sekme "Metin Oluştur" — textarea + çeviri yöntemi seçici
//   Sekme "Dosya Yükle"  — upload zone → metin + çeviri yöntemi seçici
//
// Çeviri yöntemi:
//   "Profil Kullan" → kayıtlı profil dropdown → çeviri
//   "Manuel Çeviri Seçenekleri" → progressive disclosure: Dil→Tablo→Mod→Düzen

(function () {
  "use strict";

  var activeTab = "text";

  function el(id) { return document.getElementById(id); }
  function elId(suffix) { return document.getElementById(activeTab + "-" + suffix); }

  var panelText = el("panel-text");
  var panelFile = el("panel-file");
  var sourceText = el("source-text");
  var fileInput = el("file-input");
  var fileHint = el("file-hint");
  var fileResult = el("file-result");
  var sourceTextFile = el("source-text-file");
  var optionsText = el("options-text");
  var optionsFile = el("options-file");

  var tables = [];
  var currentResult = null;
  var savedProfiles = [];
  var modeFormats = {};  // mode_id → [{id, label_tr, extension, description_tr, recommended}]

  // Kağıt boyutu → varsayılan değerler (Duxbury referans)
  var PAPER_DEFAULTS = {
    a4: { chars: 30, lines: 28 },
    letter: { chars: 30, lines: 25 },
    "11.5x11": { chars: 40, lines: 25 }
  };

  // ── Seçenek HTML şablonu ────────────────────────────────────

  function optionsHTML(prefix) {
    return (
      // Çeviri yöntemi seçici
      '<section class="card" aria-label="Çeviri yöntemi">' +
        '<h2>Çeviri Yöntemi</h2>' +
        '<div class="form-field">' +
          '<label for="' + prefix + '-method-select">Yöntem</label>' +
          '<select id="' + prefix + '-method-select" required>' +
            '<option value="">— Seçin —</option>' +
            '<option value="profile">Profil Kullan</option>' +
            '<option value="manual">Manuel Çeviri Seçenekleri</option>' +
          '</select>' +
        '</div>' +
      '</section>' +

      // Profil seçici (yöntem "profile" seçilince görünür)
      '<div id="' + prefix + '-profile-section" class="card" hidden>' +
        '<h2>Profil Seçimi</h2>' +
        '<div class="form-field">' +
          '<label for="' + prefix + '-profile-select">Kayıtlı Profil</label>' +
          '<select id="' + prefix + '-profile-select">' +
            '<option value="">— Seçin —</option>' +
          '</select>' +
        '</div>' +
      '</div>' +

      // Manuel çeviri seçenekleri (yöntem "manual" seçilince görünür)
      '<div id="' + prefix + '-manual-section" hidden>' +
        '<section class="card" aria-label="Çeviri seçenekleri">' +
          '<h2>Çeviri Seçenekleri</h2>' +
          '<div class="grid grid-2">' +
            '<div class="form-field">' +
              '<label for="' + prefix + '-lang-select">1. Dil</label>' +
              '<select id="' + prefix + '-lang-select" required>' +
                '<option value="">Dil seçin…</option>' +
              '</select>' +
            '</div>' +
            '<div class="form-field">' +
              '<label for="' + prefix + '-table-select">2. Braille Tablosu</label>' +
              '<select id="' + prefix + '-table-select" required>' +
                '<option value="">Tablo seçin…</option>' +
              '</select>' +
            '</div>' +
            '<div class="form-field">' +
              '<label for="' + prefix + '-mode-select">3. Çıktı Modu</label>' +
              '<select id="' + prefix + '-mode-select" required>' +
                '<option value="">Mod seçin…</option>' +
              '</select>' +
            '</div>' +
          '</div>' +
        '</section>' +
        '<div id="' + prefix + '-contraction-categories" class="card contraction-card" hidden>' +
          '<h2>Kısaltma Çeşitleri</h2>' +
          '<div class="contraction-checks" id="' + prefix + '-contraction-checks" role="group" aria-label="Kısaltma çeşitleri"></div>' +
        '</div>' +
      '</div>' +

      // Sayfa Düzeni kartı (mode embosser/notetaker seçilince görünür)
      '<div id="' + prefix + '-page-settings-card" class="card" hidden>' +
        '<h2>Sayfa Düzeni</h2>' +
        '<div class="grid grid-2">' +
          '<div class="form-field">' +
            '<label for="' + prefix + '-paper-size">Kağıt Boyutu</label>' +
            '<select id="' + prefix + '-paper-size">' +
              '<option value="">— Seçin —</option>' +
              '<option value="a4">A4</option>' +
              '<option value="letter">Letter (8.5×11")</option>' +
              '<option value="11.5x11">11×11.5" (Braille Standardı)</option>' +
            '</select>' +
          '</div>' +
          '<div class="form-field">' +
            '<label for="' + prefix + '-chars-per-line">Satır Başına Karakter</label>' +
            '<input type="number" id="' + prefix + '-chars-per-line" min="20" max="50" placeholder="30">' +
          '</div>' +
          '<div class="form-field">' +
            '<label for="' + prefix + '-lines-per-page">Sayfa Başına Satır</label>' +
            '<input type="number" id="' + prefix + '-lines-per-page" min="10" max="35" placeholder="28">' +
          '</div>' +
          '<div class="form-field">' +
            '<label for="' + prefix + '-top-margin">Üst Kenar Boşluğu (satır)</label>' +
            '<input type="number" id="' + prefix + '-top-margin" min="0" max="10" placeholder="0">' +
          '</div>' +
          '<div class="form-field">' +
            '<label for="' + prefix + '-binding-margin">Cilt Payı (karakter)</label>' +
            '<input type="number" id="' + prefix + '-binding-margin" min="0" max="10" placeholder="0">' +
          '</div>' + +
          '<div class="form-field">' +
            '<label class="checkbox-label">' +
              '<input type="checkbox" id="' + prefix + '-interpoint">' +
              '<span>Çift Taraflı (Interpoint)</span>' +
            '</label>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Dosya Formatı kartı (mod seçilince görünür — Sonuç bölümünden önce)
      '<div id="' + prefix + '-format-card" class="card" hidden>' +
        '<h2>Dosya Formatı</h2>' +
        '<p class="field-hint" id="' + prefix + '-format-hint">Seçtiğiniz çıktı modu için kullanılabilir dosya formatları:</p>' +
        '<div class="radio-group format-radio-group" id="' + prefix + '-format-options" role="radiogroup" aria-label="Dosya formatı seçenekleri">' +
          '<!-- Dinamik olarak doldurulur -->' +
        '</div>' +
      '</div>' +

      // Çevir / Temizle butonları + durum
      '<div class="btn-group btn-group-translate">' +
        '<button type="button" class="btn btn-primary" id="' + prefix + '-translate-btn" disabled>Çevir</button>' +
        '<button type="button" class="btn btn-secondary" id="' + prefix + '-clear-btn">Temizle</button>' +
      '</div>' +
      '<p id="' + prefix + '-ready-hint" class="ready-hint" role="alert" aria-live="polite">' +
        'Çeviri yapabilmek için: metin girin ve bir çeviri yöntemi seçin.</p>' +
      '<p id="' + prefix + '-translate-status" class="status-message" role="status" aria-live="polite"></p>' +
      '<section class="card" aria-label="Çeviri sonucu">' +
        '<h2>Sonuç</h2>' +
        '<div id="' + prefix + '-result-loading" class="loading-indicator" hidden>' +
          '<span class="spinner" aria-hidden="true"></span><span>Çevriliyor…</span>' +
        '</div>' +
        '<div id="' + prefix + '-result-empty" class="state-box">' +
          '<h3>Henüz çeviri yapılmadı</h3><p>Çeviri yöntemini belirleyin, ardından "Çevir" düğmesine basın.</p>' +
        '</div>' +
        '<div id="' + prefix + '-result-content" hidden>' +
          '<pre class="result-output" id="' + prefix + '-result-output" tabindex="0" aria-label="Braille çeviri sonucu"></pre>' +
          '<div class="result-meta">' +
            '<span id="' + prefix + '-result-charcount"></span>' +
            '<span id="' + prefix + '-result-table"></span>' +
          '</div>' +
          '<div class="btn-group" style="margin-top:var(--space-md)">' +
            '<button type="button" class="btn btn-secondary" id="' + prefix + '-copy-btn">Kopyala</button>' +
            '<button type="button" class="btn btn-primary" id="' + prefix + '-download-btn" hidden>Dosya İndir</button>' +
          '</div>' +
        '</div>' +
      '</section>'
    );
  }

  // ── Başlangıç ──────────────────────────────────────────────

  async function init() {
    var user;
    try { user = await window.NovaUi.requireAuth(); } catch (err) { return; }

    populateSidebarUser(user);
    initAdminNav(user);
    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));
    el("logout-btn").addEventListener("click", window.NovaUi.logout);

    optionsText.innerHTML = optionsHTML("text");
    optionsFile.innerHTML = optionsHTML("file");

    initTabs();
    initFormatSelector();
    bindControlEvents("text");
    bindControlEvents("file");

    await Promise.all([loadLanguages(), loadModes(), loadProfiles(), loadFormats()]);
  }

  // ── Sekme yönetimi ─────────────────────────────────────────

  function initTabs() {
    el("tab-text").addEventListener("click", function () { switchTab("text"); });
    el("tab-file").addEventListener("click", function () { switchTab("file"); });
  }

  function switchTab(tab) {
    activeTab = tab;
    el("tab-text").setAttribute("aria-selected", String(tab === "text"));
    el("tab-file").setAttribute("aria-selected", String(tab === "file"));
    panelText.hidden = tab !== "text";
    panelFile.hidden = tab !== "file";
  }

  function getActiveSource() {
    return activeTab === "file" ? sourceTextFile : sourceText;
  }

  // ── Profil yönetimi ────────────────────────────────────────

  async function loadProfiles() {
    try {
      savedProfiles = await window.NovaApi.apiGet("/api/v1/profiles");
      populateProfileSelectors();
    } catch (err) { savedProfiles = []; }
  }

  function populateProfileSelectors() {
    ["text", "file"].forEach(function (p) {
      var sel = el(p + "-profile-select");
      if (!sel) return;
      sel.innerHTML = '<option value="">— Seçin —</option>';
      if (!savedProfiles || savedProfiles.length === 0) return;
      savedProfiles.forEach(function (prof) {
        var opt = document.createElement("option");
        opt.value = prof.id;
        opt.textContent = prof.name + (prof.is_default ? " ★" : "");
        sel.appendChild(opt);
      });
    });
  }

  // ── Format listesi (populate select dropdown) ─────────

  async function loadFormats() {
    try {
      var formats = await window.NovaApi.apiGet("/api/v1/files/formats");
      populateFormatSelect(formats);
    } catch (err) {
      // Fallback: 4 temel format
      populateFormatSelect([
        { format: "txt", label_tr: "Düz Metin (.txt)", extensions: [".txt"] },
        { format: "docx", label_tr: "Microsoft Word (.docx)", extensions: [".docx"] },
        { format: "rtf", label_tr: "Zengin Metin (.rtf)", extensions: [".rtf"] },
        { format: "pdf", label_tr: "PDF Belgesi (.pdf)", extensions: [".pdf"] },
      ]);
    }
  }

  function populateFormatSelect(formats) {
    var fmtSel = el("upload-format-select");
    if (!fmtSel) return;
    fmtSel.innerHTML = '<option value="">— Seçin —</option>';
    if (!formats || !formats.length) return;

    formats.forEach(function (f) {
      var opt = document.createElement("option");
      opt.value = f.format;
      opt.textContent = f.label_tr;
      // Store extensions for accept attribute
      if (f.extensions) opt.setAttribute("data-extensions", f.extensions.join(","));
      fmtSel.appendChild(opt);
    });
  }

  async function applyProfile(prefix, profile) {
    // 1. Dil → tablo yükle → tablo seç
    var langSel = el(prefix + "-lang-select");
    if (!langSel) return;
    langSel.value = profile.locale;
    langSel.dispatchEvent(new Event("change"));

    var tblSel = el(prefix + "-table-select");
    await waitFor(function () { return tblSel && tblSel.options.length > 1; }, 5000);
    tblSel.value = profile.table_id;
    tblSel.dispatchEvent(new Event("change"));

    // 2. Mod
    var modeSel = el(prefix + "-mode-select");
    await waitFor(function () { return modeSel && modeSel.options.length > 1; }, 3000);
    modeSel.value = profile.mode;
    modeSel.dispatchEvent(new Event("change"));

    // 3. Dosya formatı (profilden mode'a göre otomatik)
    // Profilde kayıtlı format varsa onu seç, yoksa önerilen formatı bırak
    if (profile.output_format && modeFormats[profile.mode]) {
      var fmtRadio = document.querySelector("input[name='" + prefix + "-output-format'][value='" + profile.output_format + "']");
      if (fmtRadio) fmtRadio.checked = true;
    }

    // 4. Kısaltma checkbox'ları
    var checksContainer = el(prefix + "-contraction-checks");
    if (profile.contraction_categories && checksContainer) {
      await waitFor(function () { return checksContainer.children.length > 0; }, 5000);
      var catIds = typeof profile.contraction_categories === "string"
        ? JSON.parse(profile.contraction_categories) : profile.contraction_categories;
      if (Array.isArray(catIds)) {
        var cbs = checksContainer.querySelectorAll("input[type=checkbox]");
        for (var i = 0; i < cbs.length; i++) cbs[i].checked = catIds.indexOf(cbs[i].value) !== -1;
      }
      var card = el(prefix + "-contraction-categories");
      if (card) card.hidden = false;
    }

    // 5. Sayfa düzeni (varsa)
    if (profile.page_settings) {
      var ps = typeof profile.page_settings === "string"
        ? JSON.parse(profile.page_settings) : profile.page_settings;
      applyPageSettings(prefix, ps);
    }

    updateReadyState();
  }

  // ── Sayfa düzeni ───────────────────────────────────────────

  function applyPageSettings(prefix, ps) {
    if (!ps) return;
    if (ps.paper_size) setValue(prefix + "-paper-size", ps.paper_size);
    if (ps.chars_per_line) setValue(prefix + "-chars-per-line", ps.chars_per_line);
    if (ps.lines_per_page) setValue(prefix + "-lines-per-page", ps.lines_per_page);
    if (ps.top_margin !== undefined) setValue(prefix + "-top-margin", ps.top_margin);
    if (ps.binding_margin !== undefined) setValue(prefix + "-binding-margin", ps.binding_margin);
    var ip = el(prefix + "-interpoint");
    if (ip) ip.checked = !!ps.interpoint;
  }

  function getPageSettings(prefix) {
    var ps = {
      paper_size: (el(prefix + "-paper-size") || {}).value || "",
      chars_per_line: parseInt((el(prefix + "-chars-per-line") || {}).value, 10) || 30,
      lines_per_page: parseInt((el(prefix + "-lines-per-page") || {}).value, 10) || 28,
      top_margin: parseInt((el(prefix + "-top-margin") || {}).value, 10) || 0,
      binding_margin: parseInt((el(prefix + "-binding-margin") || {}).value, 10) || 0,
      interpoint: (el(prefix + "-interpoint") || {}).checked || false
    };
    return ps;
  }

  function setValue(id, val) {
    var e = el(id);
    if (e) e.value = val;
  }

  function waitFor(fn, ms) {
    return new Promise(function (ok) {
      var start = Date.now();
      function tick() { if (fn() || Date.now() - start > ms) return ok(); setTimeout(tick, 100); }
      tick();
    });
  }

  // ── Dosya formatı seçici ──────────────────────────────

  function initFormatSelector() {
    var fmtSel = el("upload-format-select");
    var selBtn = el("file-select-btn");
    var infoEl = el("upload-format-info");

    if (fmtSel) {
      fmtSel.addEventListener("change", function () {
        var opt = fmtSel.selectedOptions[0];
        if (opt && opt.value) {
          var exts = opt.getAttribute("data-extensions") || "." + opt.value;
          fileInput.setAttribute("accept", exts);
          if (selBtn) selBtn.disabled = false;
          if (infoEl) infoEl.textContent = opt.textContent + " formatı seçildi. Dosya seç butonuna basarak yükleyin.";
        } else {
          fileInput.setAttribute("accept", "");
          if (selBtn) selBtn.disabled = true;
          if (infoEl) infoEl.textContent = "Yüklemek istediğiniz dosya türünü seçin.";
        }
      });
    }

    if (selBtn) {
      selBtn.addEventListener("click", function () {
        if (fmtSel && fmtSel.value) {
          fileInput.click();
        }
      });
    }

    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });
  }

  async function handleFileUpload(file) {
    fileHint.textContent = "Dosya yükleniyor…";
    fileHint.classList.remove("status-success");
    var formData = new FormData();
    formData.append("file", file);
    try {
      var result = await window.NovaApi.apiUpload("/api/v1/files/upload", formData);
      sourceTextFile.value = result.text;
      fileHint.textContent = "✓ " + result.original_filename + " (" + result.input_format.toUpperCase() + ", " + window.NovaUi.formatNumber(result.char_count) + " karakter)";
      fileHint.classList.add("status-success");
      fileResult.hidden = false;
      fileResult.scrollIntoView({ behavior: "smooth", block: "start" });
      clearResultFor("file");
      if (activeTab === "file") updateReadyState();
    } catch (err) {
      fileHint.textContent = "";
      var s = el("file-translate-status");
      if (s) window.NovaUi.showStatus(s, "Dosya yüklenemedi: " + err.message, "error");
    } finally { fileInput.value = ""; }
  }

  // ── Veri yükleme ───────────────────────────────────────────

  async function loadLanguages() {
    try {
      var langs = await window.NovaApi.apiGet("/api/v1/tables/languages?priority_only=true");
      ["text", "file"].forEach(function (p) {
        var sel = el(p + "-lang-select");
        if (!sel) return;
        sel.innerHTML = '<option value="">Dil seçin…</option>';
        langs.forEach(function (l) {
          var opt = document.createElement("option");
          opt.value = l.code;
          opt.textContent = l.name;
          sel.appendChild(opt);
        });
      });
    } catch (err) { showAllStatus("Diller yüklenemedi: " + err.message, "error"); }
  }

  async function loadModes() {
    try {
      var modes = await window.NovaApi.apiGet("/api/v1/output/modes");
      modeFormats = {};
      ["text", "file"].forEach(function (p) {
        var sel = el(p + "-mode-select");
        if (!sel) return;
        sel.innerHTML = '<option value="">Mod seçin…</option>';
        modes.forEach(function (m) {
          var opt = document.createElement("option");
          opt.value = m.id;
          // Sadece mod adı — açıklama/datalist yok
          opt.textContent = m.label_tr;
          sel.appendChild(opt);
          // Dosya formatlarını sakla
          if (m.file_formats && m.file_formats.length > 0) {
            modeFormats[m.id] = m.file_formats;
          }
        });
      });
    } catch (err) { showAllStatus("Çıktı modları yüklenemedi: " + err.message, "error"); }
  }

  async function loadTables(language) {
    ["text", "file"].forEach(function (p) {
      var sel = el(p + "-table-select");
      if (!sel) return;
      sel.innerHTML = '<option value="">Yükleniyor…</option>';
    });
    tables = [];
    try {
      tables = await window.NovaApi.apiGet("/api/v1/tables?language=" + encodeURIComponent(language) + "&priority_only=true");
      ["text", "file"].forEach(function (p) {
        var sel = el(p + "-table-select");
        if (!sel) return;
        sel.innerHTML = '<option value="">Tablo seçin…</option>';

        // Tabloları kısaltmasız/kısaltmalı olarak optgroup ile grupla
        var uncontracted = [];
        var contracted = [];
        tables.forEach(function (t) {
          var has = t.contraction && t.contraction !== "false" && t.contraction !== "none" && t.contraction !== "no" && t.contraction !== "";
          if (has) contracted.push(t);
          else uncontracted.push(t);
        });

        if (uncontracted.length > 0) {
          var og = document.createElement("optgroup");
          og.label = "Kısaltmasız Tablolar";
          uncontracted.forEach(function (t) {
            var opt = document.createElement("option");
            opt.value = t.id; opt.textContent = t.name_tr || t.name_en || t.id;
            opt.setAttribute("data-contraction", "");
            opt.setAttribute("data-language", t.language || "");
            og.appendChild(opt);
          });
          sel.appendChild(og);
        }

        if (contracted.length > 0) {
          var og2 = document.createElement("optgroup");
          og2.label = "Kısaltmalı Tablolar";
          contracted.forEach(function (t) {
            var opt = document.createElement("option");
            opt.value = t.id; opt.textContent = t.name_tr || t.name_en || t.id;
            opt.setAttribute("data-contraction", t.contraction || "");
            opt.setAttribute("data-language", t.language || "");
            og2.appendChild(opt);
          });
          sel.appendChild(og2);
        }
      });
    } catch (err) {
      ["text", "file"].forEach(function (p) {
        var sel = el(p + "-table-select");
        if (sel) sel.innerHTML = '<option value="">Yüklenemedi</option>';
      });
      showAllStatus("Tablolar yüklenemedi: " + err.message, "error");
    }
    loadContractionCategories(language);
  }

  // ── Kısaltma kategorileri ────────────────────────────────────

  var contractionCategories = {};

  async function loadContractionCategories(language) {
    try {
      var cats = await window.NovaApi.apiGet("/api/v1/contractions/" + language + "/categories");
      if (cats && cats.length > 0) contractionCategories[language] = cats;
    } catch (err) { /* sessiz */ }
  }

  function renderContractionChecks(prefix, language, contraction) {
    var card = el(prefix + "-contraction-categories");
    var checksContainer = el(prefix + "-contraction-checks");
    if (!card || !checksContainer) return;

    var has = contraction && contraction !== "false" && contraction !== "none" && contraction !== "no" && contraction !== "";
    if (!has) { card.hidden = true; return; }

    var cats = contractionCategories[language];
    if (!cats || cats.length === 0) { card.hidden = true; return; }

    checksContainer.innerHTML = "";
    cats.forEach(function (cat) {
      var label = document.createElement("label");
      label.className = "contraction-check";
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.id = prefix + "-cat-" + cat.id; cb.name = "contraction-category";
      cb.value = cat.id; cb.checked = true; cb.setAttribute("data-category", cat.id);
      var span = document.createElement("span");
      span.className = "contraction-check-label";
      var strong = document.createElement("strong"); strong.textContent = cat.label_tr;
      var desc = document.createElement("span"); desc.className = "contraction-check-desc"; desc.textContent = cat.description_tr;
      span.appendChild(strong); span.appendChild(document.createTextNode(" ")); span.appendChild(desc);
      label.appendChild(cb); label.appendChild(span);
      checksContainer.appendChild(label);
    });
    card.hidden = false;
  }

  function getSelectedCategories(prefix) {
    var checks = document.querySelectorAll("#" + prefix + "-contraction-checks input[type=checkbox]");
    var sel = [];
    checks.forEach(function (cb) { if (cb.checked) sel.push(cb.value); });
    return sel;
  }

  // ── Dosya formatı seçimi ────────────────────────────────────

  function renderFormatOptions(prefix, modeId) {
    var card = el(prefix + "-format-card");
    var radioGroup = el(prefix + "-format-options");
    if (!card || !radioGroup) return;

    var formats = modeFormats[modeId];
    if (!formats || formats.length === 0) {
      card.hidden = true;
      return;
    }

    radioGroup.innerHTML = "";
    formats.forEach(function (fmt, idx) {
      var label = document.createElement("label");
      label.className = "radio-label format-radio-label";
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = prefix + "-output-format";
      radio.value = fmt.id;
      radio.setAttribute("data-extension", fmt.extension);
      if (fmt.recommended) radio.checked = true;
      var span = document.createElement("span");
      span.className = "format-radio-text";
      var strong = document.createElement("strong");
      strong.textContent = fmt.label_tr;
      if (fmt.recommended) {
        var rec = document.createElement("span");
        rec.className = "badge badge-recommended";
        rec.textContent = "Önerilen";
        strong.appendChild(document.createTextNode(" "));
        strong.appendChild(rec);
      }
      var desc = document.createElement("span");
      desc.className = "format-radio-desc";
      desc.textContent = fmt.description_tr;
      span.appendChild(strong);
      span.appendChild(document.createTextNode(" "));
      span.appendChild(desc);
      label.appendChild(radio);
      label.appendChild(span);
      radioGroup.appendChild(label);

      // Radyo buton değişince ready state güncelle
      radio.addEventListener("change", function () { updateReadyState(); });
    });

    card.hidden = false;
  }

  function getSelectedFormat(prefix) {
    var radio = document.querySelector("input[name='" + prefix + "-output-format']:checked");
    if (!radio) return null;
    return {
      id: radio.value,
      extension: radio.getAttribute("data-extension") || ""
    };
  }

  // ── Olay bağlama ────────────────────────────────────────────

  function bindControlEvents(p) {
    var methodSel = el(p + "-method-select");
    var profSel = el(p + "-profile-select");
    var langSel = el(p + "-lang-select");
    var modeSel = el(p + "-mode-select");
    var xlateBtn = el(p + "-translate-btn");
    var clrBtn = el(p + "-clear-btn");
    var cpBtn = el(p + "-copy-btn");
    var dlBtn = el(p + "-download-btn");

    // Çeviri yöntemi seçici
    if (methodSel) {
      methodSel.addEventListener("change", function () {
        var method = methodSel.value;
        var profSection = el(p + "-profile-section");
        var manSection = el(p + "-manual-section");

        if (method === "profile") {
          if (profSection) profSection.hidden = false;
          if (manSection) manSection.hidden = true;
        } else if (method === "manual") {
          if (profSection) profSection.hidden = true;
          if (manSection) manSection.hidden = false;
        } else {
          if (profSection) profSection.hidden = true;
          if (manSection) manSection.hidden = true;
        }
        updateReadyState();
      });
    }

    // Profil seçici
    if (profSel) {
      profSel.addEventListener("change", function () {
        var pid = profSel.value;
        if (!pid) return;
        var profile = savedProfiles.find(function (pr) { return pr.id === pid; });
        if (profile) applyProfile(p, profile);
      });
    }

    // Dil → Tablo listesi doldur
    if (langSel) {
      langSel.addEventListener("change", function () {
        if (langSel.value) {
          loadTables(langSel.value);
        }
        updateReadyState();
      });
    }

    // Tablo → kısaltma checkbox'ları
    var tblSel = el(p + "-table-select");
    if (tblSel) {
      tblSel.addEventListener("change", function () {
        var opt = tblSel.selectedOptions[0];
        if (opt && opt.value) {
          var contraction = opt.getAttribute("data-contraction") || "";
          var language = opt.getAttribute("data-language") || "";
          renderContractionChecks(p, language, contraction);
        } else {
          var ccard = el(p + "-contraction-categories");
          if (ccard) ccard.hidden = true;
        }
        updateReadyState();
      });
    }

    // Mod → Sayfa Düzeni görünürlüğü + Dosya formatı seçici
    if (modeSel) {
      modeSel.addEventListener("change", function () {
        var v = modeSel.value;
        var isPrint = v === "embosser" || v === "notetaker";
        var card = el(p + "-page-settings-card");
        if (card) card.hidden = !isPrint;

        // Dosya formatı seçici
        var formatCard = el(p + "-format-card");
        if (v) {
          renderFormatOptions(p, v);
        } else if (formatCard) {
          formatCard.hidden = true;
        }

        // BRF indir butonunu göster (tüm modlarda indirilebilir format var)
        var dl = el(p + "-download-btn");
        // İndir butonu artık her zaman sonuç varken görünür
        updateReadyState();
      });
    }

    // Kağıt boyutu → otomatik değer doldur
    var paperSel = el(p + "-paper-size");
    if (paperSel) {
      paperSel.addEventListener("change", function () {
        var def = PAPER_DEFAULTS[this.value];
        if (def) {
          var cpl = el(p + "-chars-per-line"); if (cpl) cpl.value = def.chars;
          var lpp = el(p + "-lines-per-page"); if (lpp) lpp.value = def.lines;
        }
        updateReadyState();
      });
    }

    // Metin değişince
    var srcEl = (p === "file") ? sourceTextFile : sourceText;
    if (srcEl) srcEl.addEventListener("input", function () { updateReadyState(); });

    if (xlateBtn) xlateBtn.addEventListener("click", doTranslate);
    if (clrBtn) clrBtn.addEventListener("click", doClear);
    if (cpBtn) cpBtn.addEventListener("click", doCopy);
    if (dlBtn) dlBtn.addEventListener("click", doDownload);

    updateReadyState();
  }

  // ── Hazırlık durumu ────────────────────────────────────────

  function updateReadyState() {
    var p = activeTab;
    var btn = el(p + "-translate-btn");
    var hint = el(p + "-ready-hint");
    var methodSel = el(p + "-method-select");
    var method = methodSel ? methodSel.value : "";

    var textOk = (activeTab === "file") ? sourceTextFile.value.trim() !== "" : sourceText.value.trim() !== "";
    var missing = [];

    if (!textOk) missing.push(activeTab === "file" ? "bir dosya yükleyin" : "metin girin");
    if (!method) missing.push("bir çeviri yöntemi seçin");

    var allOk = textOk && method !== "";

    if (method === "profile") {
      // Profil seçilmiş olmalı
      var profSel = el(p + "-profile-select");
      var profOk = profSel && profSel.value !== "";
      if (!profOk) { allOk = false; missing.push("bir profil seçin"); }
    }

    if (method === "manual") {
      // Manuel seçeneklerin hepsi dolu olmalı
      var langSel = el(p + "-lang-select");
      var tblSel = el(p + "-table-select");
      var modeSel = el(p + "-mode-select");
      var langOk = langSel && langSel.value !== "";
      var tblOk = tblSel && tblSel.value !== "";
      var modeOk = modeSel && modeSel.value !== "";
      if (!langOk) { allOk = false; missing.push("bir dil seçin"); }
      if (!tblOk) { allOk = false; missing.push("bir Braille tablosu seçin"); }
      if (!modeOk) { allOk = false; missing.push("bir çıktı modu seçin"); }
    }

    // Sayfa Düzeni kartı görünüyorsa (Embosser/Notetaker modu) kağıt boyutu zorunlu
    var pageCard = el(p + "-page-settings-card");
    if (pageCard && !pageCard.hidden) {
      var paperSel = el(p + "-paper-size");
      var paperOk = paperSel && paperSel.value !== "";
      if (!paperOk) { allOk = false; missing.push("bir kağıt boyutu seçin"); }
    }

    if (btn) btn.disabled = !allOk;
    if (hint) {
      if (missing.length === 0) {
        hint.textContent = "✓ Tüm gereklilikler karşılandı. Çeviri yapabilirsiniz.";
        hint.className = "ready-hint ready-hint-ok";
      } else {
        hint.textContent = "Çeviri yapabilmek için: " + missing.join(", ") + ".";
        hint.className = "ready-hint ready-hint-neutral";
      }
    }
  }

  // ── Çeviri ──────────────────────────────────────────────────

  function getTranslationParams() {
    var p = activeTab;
    var methodSel = el(p + "-method-select");
    var method = methodSel ? methodSel.value : "";

    var text = getActiveSource().value;
    var tableId, mode;

    if (method === "profile") {
      var profSel = el(p + "-profile-select");
      if (!profSel || !profSel.value) return null;
      var profile = savedProfiles.find(function (pr) { return pr.id === profSel.value; });
      if (!profile) return null;
      tableId = profile.table_id;
      mode = profile.mode;
    } else if (method === "manual") {
      var tblSel = el(p + "-table-select");
      var modeSel2 = el(p + "-mode-select");
      if (!tblSel || !modeSel2 || !tblSel.value || !modeSel2.value) return null;
      tableId = tblSel.value;
      mode = modeSel2.value;
    } else {
      return null;
    }

    return { text: text, tableId: tableId, mode: mode };
  }

  function doClear() {
    getActiveSource().value = "";
    if (activeTab === "file") {
      fileHint.textContent = ""; fileHint.classList.remove("status-success"); fileResult.hidden = true;
    }
    clearResultFor(activeTab);
    var s = elId("translate-status"); if (s) window.NovaUi.showStatus(s, "", null);

    // Yöntem seçiciyi sıfırla
    var methodSel = elId("method-select");
    if (methodSel) { methodSel.value = ""; methodSel.dispatchEvent(new Event("change")); }
    var profSel = elId("profile-select");
    if (profSel) profSel.value = "";

    // Manuel seçenekleri sıfırla
    ["text", "file"].forEach(function (pp) {
      var ms = el(pp + "-mode-select");
      if (ms) { ms.value = ""; }
      var ts = el(pp + "-table-select");
      if (ts) { ts.value = ""; }
      var lang = el(pp + "-lang-select");
      if (lang) { lang.value = ""; }
      var ccard = el(pp + "-contraction-categories");
      if (ccard) ccard.hidden = true;
    });

    // Sayfa düzenini sıfırla
    var card = elId("page-settings-card");
    if (card) card.hidden = true;
    var paper = elId("paper-size"); if (paper) paper.value = "";
    var cpl = elId("chars-per-line"); if (cpl) cpl.value = "";
    var lpp = elId("lines-per-page"); if (lpp) lpp.value = "";
    var tm = elId("top-margin"); if (tm) tm.value = "";
    var bm = elId("binding-margin"); if (bm) bm.value = "";
    var ip = elId("interpoint"); if (ip) ip.checked = false;

    // Format kartını sıfırla
    var fmtCard = elId("format-card");
    if (fmtCard) fmtCard.hidden = true;

    // Dosya format seçiciyi sıfırla (sadece file sekmesinde)
    if (activeTab === "file") {
      var fmtSel = el("upload-format-select");
      var selBtn = el("file-select-btn");
      var infoEl = el("upload-format-info");
      if (fmtSel) fmtSel.value = "";
      if (selBtn) selBtn.disabled = true;
      if (infoEl) infoEl.textContent = "Yüklemek istediğiniz dosya türünü seçin.";
      fileInput.setAttribute("accept", "");
    }

    updateReadyState();
  }

  function clearResultFor(p) {
    var c = el(p + "-result-content"); if (c) c.hidden = true;
    var e = el(p + "-result-empty"); if (e) e.hidden = false;
    currentResult = null;
  }

  function showAllStatus(msg, kind) {
    ["text", "file"].forEach(function (p) {
      var s = el(p + "-translate-status"); if (s) window.NovaUi.showStatus(s, msg, kind);
    });
  }

  async function doCopy() {
    if (!currentResult) return;
    try {
      await navigator.clipboard.writeText(currentResult.braille);
      var s = elId("translate-status"); if (s) window.NovaUi.showStatus(s, "Sonuç panoya kopyalandı.", "success");
    } catch (err) {
      var out = elId("result-output"); if (out) out.focus();
      var s = elId("translate-status"); if (s) window.NovaUi.showStatus(s, "Kopyalamak için sonucu seçip kopyalayın.", "info");
    }
  }

  async function doDownload() {
    if (!currentResult) return;
    var p = activeTab;
    var params = getTranslationParams();
    if (!params) return;

    // Seçili dosya formatını al
    var selFmt = getSelectedFormat(p);
    var outputFormat = selFmt ? selFmt.id : (params.mode === "notetaker" ? "brl" : "brf");
    var filename;
    var mimeType;

    if (outputFormat === "brl") {
      filename = "nova-braille.brl";
      mimeType = "text/plain; charset=utf-8";
    } else if (outputFormat === "txt") {
      filename = "nova-braille.txt";
      mimeType = "text/plain; charset=utf-8";
    } else {
      filename = "nova-braille.brf";
      mimeType = "application/octet-stream";
    }

    var dlBtn = elId("download-btn"); if (dlBtn) dlBtn.disabled = true;
    var s = elId("translate-status"); if (s) window.NovaUi.showStatus(s, "Dosya hazırlanıyor…", "info");

    try {
      var ps = getPageSettings(p);

      var res = await window.NovaApi.apiPost("/api/v1/output/download", {
        text: params.text, table_id: params.tableId,
        output_format: outputFormat,
        chars_per_line: ps.chars_per_line,
        lines_per_page: ps.lines_per_page,
      });
      triggerDownload(res.content_base64, res.filename || filename, res.mime_type || mimeType);
      if (s) window.NovaUi.showStatus(s, "Dosya indirildi: " + (res.filename || filename), "success");
    } catch (err) {
      if (s) window.NovaUi.showStatus(s, "İndirme başarısız: " + err.message, "error");
    } finally { if (dlBtn) dlBtn.disabled = false; }
  }

  async function doTranslate() {
    var params = getTranslationParams();
    if (!params) {
      var s = elId("translate-status");
      if (s) window.NovaUi.showStatus(s, "Lütfen çeviri yöntemi ve seçeneklerini belirleyin.", "error");
      return;
    }

    ["text", "file"].forEach(function (p) { var btn = el(p + "-translate-btn"); if (btn) btn.disabled = true; });

    var loading = elId("result-loading"); if (loading) loading.hidden = false;
    var content = elId("result-content"); if (content) content.hidden = true;
    var empty = elId("result-empty"); if (empty) empty.hidden = true;
    var stat = elId("translate-status"); if (stat) window.NovaUi.showStatus(stat, "", null);

    try {
      var res = await window.NovaApi.apiPost("/api/v1/output/translate", {
        text: params.text, table_id: params.tableId, mode: params.mode,
        contraction_categories: getSelectedCategories(activeTab),
      });
      currentResult = res;

      var out = elId("result-output"); if (out) out.textContent = res.braille;
      var cc = elId("result-charcount"); if (cc) cc.textContent = window.NovaUi.formatNumber(res.char_count) + " karakter";
      var rt = elId("result-table"); if (rt) rt.textContent = res.table_id;

      if (loading) loading.hidden = true;
      if (content) content.hidden = false;
      // İndir butonu her zaman göster (tüm modların dosya formatı var)
      var dl = elId("download-btn"); if (dl) dl.hidden = false;
      if (stat) window.NovaUi.showStatus(stat, "Çeviri tamamlandı.", "success");
    } catch (err) {
      if (loading) loading.hidden = true; if (empty) empty.hidden = false;
      if (stat) window.NovaUi.showStatus(stat, "Çeviri başarısız: " + err.message, "error");
    } finally {
      ["text", "file"].forEach(function (p) { var btn = el(p + "-translate-btn"); if (btn) btn.disabled = false; });
    }
  }

  // ── Yardımcılar ────────────────────────────────────────────

  function populateSidebarUser(user) {
    var nameEl = el("sidebar-user-name"); if (nameEl) nameEl.textContent = user.display_name || user.email.split("@")[0];
    var emailEl = el("sidebar-user-email"); if (emailEl) emailEl.textContent = user.email;
  }

  function initAdminNav(user) {
    if (window.NovaUi.isAdmin(user)) el("nav-admin-section").hidden = false;
    if (user.plan_code || user.status === "active") el("nav-subscription").hidden = false;
  }

  function triggerDownload(base64, filename, mimeType) {
    var byteChars = atob(base64);
    var bytes = new Uint8Array(byteChars.length);
    for (var i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
    var blob = new Blob([bytes], { type: mimeType || "application/octet-stream" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  init();
})();