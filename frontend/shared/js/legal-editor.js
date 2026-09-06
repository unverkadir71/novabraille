// Nova Braille — Hukuki Belge Editörü
//
// F3.11 — Admin panelinde hukuki belgelerin yönetimi.
// Backend endpoint'leri (F3.10):
//   GET  /api/v1/admin/legal           → tüm belgeler (draft dahil)
//   GET  /api/v1/admin/legal/{slug}    → tek belge
//   PUT  /api/v1/admin/legal/{slug}    → oluştur/güncelle
//   DELETE /api/v1/admin/legal/{slug}  → sil (şimdilik UI'da yok)
//
// CSRF: nova_csrf cookie'sini X-CSRF-Token header olarak gönderir.
// Erişilebilirlik: aria-live durum mesajları, focus yönetimi, klavye erişimi.

(function () {
  "use strict";

  const API_BASE = "/api/v1";

  const docList = document.getElementById("legal-doc-list");
  const form = document.getElementById("legal-form");
  const slugInput = document.getElementById("legal-slug");
  const titleTrInput = document.getElementById("legal-title-tr");
  const titleEnInput = document.getElementById("legal-title-en");
  const statusSelect = document.getElementById("legal-status");
  const contentInput = document.getElementById("legal-content");
  const statusMessage = document.getElementById("legal-status-message");
  const newBtn = document.getElementById("legal-new");

  let currentDocs = [];
  let currentSlug = null;

  // CSRF token'ı cookie'den okur
  function getCsrfToken() {
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split("=");
      if (name === "nova_csrf") {
        return decodeURIComponent(value);
      }
    }
    return null;
  }

  // Durum mesajını gösterir (aria-live)
  function showStatus(message, isError) {
    statusMessage.textContent = message;
    statusMessage.className = "status-message " + (isError ? "status-error" : "status-success");
  }

  // Tüm belgeleri listeler
  async function loadDocs() {
    try {
      const res = await fetch(`${API_BASE}/admin/legal`, {
        credentials: "same-origin",
      });
      if (res.status === 401) {
        showStatus("Oturumunuz sona ermiş. Lütfen yeniden giriş yapın.", true);
        return;
      }
      if (!res.ok) {
        throw new Error("Belgeler yüklenemedi: " + res.status);
      }
      const docs = await res.json();
      currentDocs = docs;
      renderDocList(docs);
    } catch (err) {
      showStatus("Belgeler yüklenemedi: " + err.message, true);
    }
  }

  // Belge listesini render eder
  function renderDocList(docs) {
    docList.innerHTML = "";
    if (docs.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "Henüz belge yok. Yeni belge oluşturun.";
      docList.appendChild(li);
      return;
    }
    docs.forEach(function (doc) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "legal-doc-item" + (doc.slug === currentSlug ? " active" : "");
      btn.setAttribute("aria-current", doc.slug === currentSlug ? "page" : null);
      btn.textContent = doc.title_tr;
      const meta = document.createElement("span");
      meta.className = "doc-meta";
      meta.textContent = doc.status === "published" ? "Yayında" : "Taslak";
      btn.appendChild(meta);
      btn.addEventListener("click", function () {
        loadDoc(doc.slug);
      });
      li.appendChild(btn);
      docList.appendChild(li);
    });
  }

  // Tek bir belgeyi yükler
  async function loadDoc(slug) {
    try {
      const res = await fetch(`${API_BASE}/admin/legal/${slug}`, {
        credentials: "same-origin",
      });
      if (!res.ok) {
        throw new Error("Belge yüklenemedi: " + res.status);
      }
      const doc = await res.json();
      currentSlug = doc.slug;
      slugInput.value = doc.slug;
      titleTrInput.value = doc.title_tr;
      titleEnInput.value = doc.title_en;
      statusSelect.value = doc.status;
      contentInput.value = doc.content_markdown;
      renderDocList(currentDocs);
      titleTrInput.focus();
      showStatus("", false);
    } catch (err) {
      showStatus("Belge yüklenemedi: " + err.message, true);
    }
  }

  // Formu temizler (yeni belge)
  function newDoc() {
    currentSlug = null;
    slugInput.value = "";
    slugInput.removeAttribute("readonly");
    titleTrInput.value = "";
    titleEnInput.value = "";
    statusSelect.value = "draft";
    contentInput.value = "";
    renderDocList(currentDocs);
    slugInput.focus();
    showStatus("Yeni belge için tanımlayıcı (slug) girin.", false);
  }

  // Kaydetme (oluştur veya güncelle)
  async function saveDoc(event) {
    event.preventDefault();

    const slug = slugInput.value.trim();
    if (!slug) {
      showStatus("Tanımlayıcı (slug) zorunludur.", true);
      slugInput.focus();
      return;
    }
    if (!/^[a-z0-9-]+$/.test(slug)) {
      showStatus("Tanımlayıcı yalnızca küçük harf, rakam ve tire içerebilir.", true);
      slugInput.focus();
      return;
    }

    const payload = {
      title_tr: titleTrInput.value.trim(),
      title_en: titleEnInput.value.trim(),
      content_markdown: contentInput.value,
      status: statusSelect.value,
    };

    if (!payload.title_tr || !payload.title_en || !payload.content_markdown) {
      showStatus("Tüm alanlar zorunludur.", true);
      return;
    }

    const csrfToken = getCsrfToken();

    try {
      const res = await fetch(`${API_BASE}/admin/legal/${encodeURIComponent(slug)}`, {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken || "",
        },
        body: JSON.stringify(payload),
      });

      if (res.status === 403) {
        showStatus("Bu işlem için yetkiniz yok veya CSRF doğrulaması başarısız.", true);
        return;
      }
      if (!res.ok) {
        const detail = await res.json().catch(function () { return {}; });
        throw new Error(detail.detail?.message || "Kayıt başarısız: " + res.status);
      }

      const saved = await res.json();
      currentSlug = saved.slug;
      slugInput.value = saved.slug;
      slugInput.setAttribute("readonly", "true");
      showStatus("Belge başarıyla kaydedildi.", false);
      await loadDocs();
      renderDocList(currentDocs);
    } catch (err) {
      showStatus("Kayıt başarısız: " + err.message, true);
    }
  }

  // Olay dinleyicileri
  form.addEventListener("submit", saveDoc);
  newBtn.addEventListener("click", newDoc);

  // Başlangıç
  async function init() {
    // Admin guard + sidebar
    if (window.NovaAdmin && window.NovaAdmin.initAdminShell) {
      try {
        const user = await window.NovaAdmin.initAdminShell();
        document.getElementById("sidebar-user-name").textContent =
          user.display_name || user.email.split("@")[0];
        document.getElementById("sidebar-user-email").textContent = user.email;
      } catch (err) {
        return; // admin değil → yönlendirildi
      }
    }
    loadDocs();
  }

  init();
})();
