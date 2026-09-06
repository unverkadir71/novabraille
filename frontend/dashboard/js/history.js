// Nova Braille — Çeviri Geçmişi
//
// F4.5 — Client-side şifrelemeli çeviri geçmişi (ADR-004).
//
// API:
//   GET  /api/v1/history              → metadata listesi (şifresiz)
//   GET  /api/v1/history/{id}         → ciphertext dahil tam kayıt
//   DELETE /api/v1/history/{id}       → sil
//
// Şifre çözme: NovaBrailleEncryption.decrypt(password, ciphertext, iv, salt)

(function () {
  "use strict";

  const passwordInput = document.getElementById("decrypt-password");
  const historyLoading = document.getElementById("history-loading");
  const historyEmpty = document.getElementById("history-empty");
  const historyList = document.getElementById("history-list");
  const historyDetail = document.getElementById("history-detail");
  const historyDetailContent = document.getElementById("history-detail-content");
  const historyClose = document.getElementById("history-close");
  const statusEl = document.getElementById("history-status");

  let entries = [];

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
    if (user.plan_code) {
      document.getElementById("nav-subscription").hidden = false;
    }
    window.NovaUi.initSidebarToggle(".hamburger");
    window.NovaUi.initOfflineBanner(document.getElementById("offline-banner"));
    document.getElementById("logout-btn").addEventListener("click", window.NovaUi.logout);
    historyClose.addEventListener("click", function () {
      historyDetail.hidden = true;
    });

    await loadHistory();
  }

  async function loadHistory() {
    historyLoading.hidden = false;
    historyEmpty.hidden = true;
    historyList.innerHTML = "";

    try {
      entries = await window.NovaApi.apiGet("/api/v1/history?limit=50");
      historyLoading.hidden = true;

      if (entries.length === 0) {
        historyEmpty.hidden = false;
        return;
      }

      renderList();
    } catch (err) {
      historyLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "Geçmiş yüklenemedi: " + err.message, "error");
    }
  }

  function renderList() {
    historyList.innerHTML = "";
    entries.forEach(function (entry) {
      const item = document.createElement("div");
      item.className = "card history-item";
      item.setAttribute("role", "listitem");

      const meta = document.createElement("div");
      meta.className = "history-meta";

      const langSpan = document.createElement("span");
      langSpan.textContent = "Dil: " + (entry.source_locale || "—");
      meta.appendChild(langSpan);

      const dirSpan = document.createElement("span");
      dirSpan.textContent = "Yön: " + directionLabel(entry.direction);
      meta.appendChild(dirSpan);

      const charSpan = document.createElement("span");
      charSpan.textContent = window.NovaUi.formatNumber(entry.char_count) + " karakter";
      meta.appendChild(charSpan);

      const dateSpan = document.createElement("span");
      dateSpan.textContent = window.NovaUi.formatDate(entry.created_at);
      meta.appendChild(dateSpan);

      const actions = document.createElement("div");
      actions.className = "btn-group";

      const viewBtn = document.createElement("button");
      viewBtn.type = "button";
      viewBtn.className = "btn btn-secondary";
      viewBtn.textContent = "Görüntüle";
      viewBtn.addEventListener("click", function () { viewEntry(entry.id); });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "btn btn-danger";
      deleteBtn.textContent = "Sil";
      deleteBtn.addEventListener("click", function () { deleteEntry(entry.id); });

      actions.appendChild(viewBtn);
      actions.appendChild(deleteBtn);

      item.appendChild(meta);
      item.appendChild(actions);
      historyList.appendChild(item);
    });
  }

  async function viewEntry(entryId) {
    const password = passwordInput.value;
    if (!password) {
      window.NovaUi.showStatus(statusEl, "İçeriği görüntülemek için şifre çözme parolası girin.", "error");
      passwordInput.focus();
      return;
    }

    window.NovaUi.showStatus(statusEl, "", null);

    try {
      const record = await window.NovaApi.apiGet("/api/v1/history/" + entryId);

      let decrypted;
      try {
        decrypted = await window.NovaBrailleEncryption.decrypt(
          password,
          record.ciphertext,
          record.iv,
          record.salt
        );
      } catch (e) {
        window.NovaUi.showStatus(statusEl, "Şifre çözme başarısız. Parola yanlış olabilir.", "error");
        return;
      }

      renderDetail(decrypted, record);
      historyDetail.hidden = false;
      historyDetail.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      window.NovaUi.showStatus(statusEl, "Kayıt yüklenemedi: " + err.message, "error");
    }
  }

  function renderDetail(data, record) {
    historyDetailContent.innerHTML = "";

    const heading = document.createElement("h3");
    heading.textContent = "Kaynak Metin";
    historyDetailContent.appendChild(heading);

    const sourcePre = document.createElement("pre");
    sourcePre.className = "result-output";
    sourcePre.textContent = data.source || "";
    sourcePre.tabIndex = 0;
    historyDetailContent.appendChild(sourcePre);

    const brailleHeading = document.createElement("h3");
    brailleHeading.textContent = "Braille Sonucu";
    historyDetailContent.appendChild(brailleHeading);

    const braillePre = document.createElement("pre");
    braillePre.className = "result-output";
    braillePre.textContent = data.braille || "";
    braillePre.tabIndex = 0;
    historyDetailContent.appendChild(braillePre);

    const meta = document.createElement("p");
    meta.className = "field-hint";
    meta.textContent = "Tablo: " + record.table_id + " · " +
      window.NovaUi.formatDate(record.created_at);
    historyDetailContent.appendChild(meta);
  }

  async function deleteEntry(entryId) {
    const confirmed = window.confirm("Bu çeviri kaydını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.");
    if (!confirmed) {
      return;
    }

    try {
      await window.NovaApi.apiDelete("/api/v1/history/" + entryId);
      window.NovaUi.showStatus(statusEl, "Kayıt silindi.", "success");
      await loadHistory();
    } catch (err) {
      window.NovaUi.showStatus(statusEl, "Silme başarısız: " + err.message, "error");
    }
  }

  function directionLabel(direction) {
    return direction === "text_to_braille" ? "Metin → Braille" : "Braille → Metin";
  }

  init();
})();
