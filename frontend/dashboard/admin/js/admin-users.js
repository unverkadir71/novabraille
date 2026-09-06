// Nova Braille — Admin Kullanıcı Yönetimi
//
// F4.12 — Liste, arama, filtreleme, rol atama.
// API:
//   GET /admin/users               → tüm kullanıcılar
//   PUT /admin/users/{id}/role     → rol ata (super_admin)

(function () {
  "use strict";

  const searchInput = document.getElementById("user-search");
  const statusFilter = document.getElementById("status-filter");
  const usersLoading = document.getElementById("users-loading");
  const usersEmpty = document.getElementById("users-empty");
  const usersTableWrap = document.getElementById("users-table-wrap");
  const usersTbody = document.getElementById("users-tbody");
  const statusEl = document.getElementById("users-status");

  const STATUS_LABELS = {
    active: { label: "Aktif", cls: "badge-active" },
    pending: { label: "Beklemede", cls: "badge-pending" },
    suspended: { label: "Askıda", cls: "badge-suspended" },
    closed: { label: "Kapalı", cls: "badge-closed" },
  };

  const PLAN_LABELS = {
    starter: "Başlangıç",
    professional: "Profesyonel",
    enterprise: "Kurumsal",
  };

  let users = [];
  let currentUser = null;

  async function init() {
    try {
      currentUser = await window.NovaAdmin.initAdminShell();
    } catch (err) {
      return;
    }

    // Hosted-only nav gizleme (self-hosted'de plan/abonelik/ödeme/gelir yok)
    // Bu, role değil uygulama moduna bağlı; şimdilik super_admin dışında gizleme yok.
    // Rol atama yalnızca super_admin'e açık.

    searchInput.addEventListener("input", renderTable);
    statusFilter.addEventListener("change", renderTable);

    await loadUsers();
  }

  async function loadUsers() {
    usersLoading.hidden = false;
    usersEmpty.hidden = true;
    usersTableWrap.hidden = true;

    try {
      users = await window.NovaApi.apiGet("/api/v1/admin/users");
      usersLoading.hidden = true;
      renderTable();
    } catch (err) {
      usersLoading.hidden = true;
      window.NovaUi.showStatus(statusEl, "Kullanıcılar yüklenemedi: " + err.message, "error");
    }
  }

  function filteredUsers() {
    const query = searchInput.value.trim().toLowerCase();
    const status = statusFilter.value;

    return users.filter(function (user) {
      const matchesQuery =
        !query ||
        (user.email && user.email.toLowerCase().includes(query)) ||
        (user.display_name && user.display_name.toLowerCase().includes(query));
      const matchesStatus = !status || user.status === status;
      return matchesQuery && matchesStatus;
    });
  }

  function renderTable() {
    const filtered = filteredUsers();

    if (filtered.length === 0) {
      usersTableWrap.hidden = true;
      usersEmpty.hidden = false;
      return;
    }

    usersEmpty.hidden = true;
    usersTableWrap.hidden = false;
    usersTbody.innerHTML = "";

    filtered.forEach(function (user) {
      const tr = document.createElement("tr");

      tr.appendChild(td(user.email || "—"));
      tr.appendChild(td(user.display_name || "—"));

      // Rol hücresi (super_admin için dropdown)
      const roleTd = document.createElement("td");
      if (currentUser.role === "super_admin" && user.id !== currentUser.id) {
        roleTd.appendChild(roleSelect(user));
      } else {
        roleTd.textContent = window.NovaAdmin.roleLabel(user.role);
      }
      tr.appendChild(roleTd);

      tr.appendChild(statusBadge(user.status));

      tr.appendChild(td(user.plan_code ? (PLAN_LABELS[user.plan_code] || user.plan_code) : "—"));

      tr.appendChild(td(window.NovaUi.formatDate(user.created_at)));

      const actionTd = document.createElement("td");
      actionTd.textContent = user.id === currentUser.id ? "Siz" : "—";
      tr.appendChild(actionTd);

      usersTbody.appendChild(tr);
    });
  }

  function roleSelect(user) {
    const select = document.createElement("select");
    select.setAttribute("aria-label", user.email + " için rol");
    const roles = ["super_admin", "admin", "billing", "support", "user"];
    roles.forEach(function (role) {
      const opt = document.createElement("option");
      opt.value = role;
      opt.textContent = window.NovaAdmin.ROLE_LABELS[role];
      opt.selected = user.role === role;
      select.appendChild(opt);
    });

    select.addEventListener("change", async function () {
      const newRole = select.value;
      try {
        await window.NovaApi.apiPut("/api/v1/admin/users/" + user.id + "/role", {
          role: newRole,
        });
        user.role = newRole;
        window.NovaUi.showStatus(statusEl, "Rol güncellendi: " + user.email, "success");
        renderTable();
      } catch (err) {
        window.NovaUi.showStatus(statusEl, "Rol güncellenemedi: " + err.message, "error");
        await loadUsers();
      }
    });

    return select;
  }

  function statusBadge(status) {
    const td = document.createElement("td");
    const info = STATUS_LABELS[status] || { label: status, cls: "" };
    const span = document.createElement("span");
    span.className = "badge " + info.cls;
    span.textContent = info.label;
    td.appendChild(span);
    return td;
  }

  function td(text) {
    const cell = document.createElement("td");
    cell.textContent = text;
    return cell;
  }

  init();
})();
