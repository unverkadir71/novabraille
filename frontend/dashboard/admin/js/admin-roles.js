// Nova Braille — Admin Rol Yönetimi
//
// F4.13 — Hosted only. Rol-izin matrisi (salt okunur).
// API: GET /admin/roles/permissions

(function () {
  "use strict";

  const rolesLoading = document.getElementById("roles-loading");
  const rolesContent = document.getElementById("roles-content");
  const rolesList = document.getElementById("roles-list");
  const statusEl = document.getElementById("roles-status");

  async function init() {
    try {
      await window.NovaAdmin.initAdminShell();
    } catch (err) {
      return;
    }

    try {
      const matrix = await window.NovaApi.apiGet("/api/v1/admin/roles/permissions");
      renderMatrix(matrix);
      rolesLoading.hidden = true;
      rolesContent.hidden = false;
    } catch (err) {
      rolesLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "İzin matrisi yüklenemedi: " + err.message, "error");
    }
  }

  function renderMatrix(matrix) {
    rolesList.innerHTML = "";
    for (const [role, permissions] of Object.entries(matrix)) {
      const card = document.createElement("div");
      card.className = "card";

      const heading = document.createElement("h3");
      heading.textContent = window.NovaAdmin.roleLabel(role);
      card.appendChild(heading);

      if (!permissions || permissions.length === 0) {
        const empty = document.createElement("p");
        empty.className = "field-hint";
        empty.textContent = "İzin yok";
        card.appendChild(empty);
      } else {
        const ul = document.createElement("ul");
        ul.className = "permission-list";
        permissions.forEach(function (perm) {
          const li = document.createElement("li");
          li.textContent = perm;
          ul.appendChild(li);
        });
        card.appendChild(ul);
      }

      rolesList.appendChild(card);
    }
  }

  init();
})();
