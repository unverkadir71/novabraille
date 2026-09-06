// Nova Braille — Ortak Dashboard UI Yardımcıları
//
// Tüm dashboard sayfalarının kullandığı ortak işlevler:
//   - Oturum kontrolü (auth guard)
//   - Çıkış (logout)
//   - Durum mesajı gösterimi (aria-live)
//   - Tarih/biçim yardımcıları
//   - Mobil sidebar açma/kapama

(function () {
  "use strict";

  /**
   * Çerez okur.
   */
  function getCookie(name) {
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const [key, value] = cookie.trim().split("=");
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return null;
  }

  /**
   * Geçerli kullanıcıyı çeker. Oturum yoksa login'e yönlendirir.
   * @returns {Promise<object>} — kullanıcı bilgisi (UserRead)
   */
  async function requireAuth() {
    try {
      const user = await window.NovaApi.apiGet("/api/v1/auth/me");
      return user;
    } catch (err) {
      if (err && err.status === 401) {
        window.NovaApi.redirectToLogin();
      }
      throw err;
    }
  }

  /**
   * Kullanıcının admin olup olmadığını döndürür.
   * @param {object} user
   * @returns {boolean}
   */
  function isAdmin(user) {
    if (!user || !user.role) {
      return false;
    }
    return user.role !== "user";
  }

  /**
   * Admin erişimi gerektirir; admin değilse dashboard'a yönlendirir.
   * @returns {Promise<object>} — kullanıcı bilgisi
   */
  async function requireAdmin() {
    const user = await requireAuth();
    if (!isAdmin(user)) {
      const pathDepth = window.location.pathname.split("/").filter(Boolean).length;
      const prefix = pathDepth > 1 ? "../".repeat(pathDepth - 1) : "";
      window.location.href = prefix + "index.html";
      throw new Error("Admin yetkisi gerekli.");
    }
    return user;
  }

  /**
   * Çıkış yapar ve login'e yönlendirir.
   */
  async function logout() {
    try {
      await window.NovaApi.apiPost("/api/v1/auth/logout", {});
    } catch (err) {
      // Çıkış başarısız olsa bile yerel olarak login'e git
    }
    window.location.href = "../login.html";
  }

  /**
   * Durum mesajını gösterir (aria-live bölgesinde).
   * @param {HTMLElement} element
   * @param {string} message
   * @param {string} type — "success" | "error" | "info"
   */
  function showStatus(element, message, type) {
    if (!element) {
      return;
    }
    element.textContent = message;
    element.className = "status-message";
    if (type) {
      element.classList.add("status-" + type);
    }
    // aria-live için role ekle
    element.setAttribute("role", "status");
    element.setAttribute("aria-live", "polite");
  }

  /**
   * Loading durumunu gösterir/gizler.
   * @param {HTMLElement} element
   * @param {boolean} loading
   */
  function setLoading(element, loading) {
    if (!element) {
      return;
    }
    element.hidden = !loading;
  }

  /**
   * Tarihi yerel formatta döndürür.
   * @param {string} isoDate
   * @returns {string}
   */
  function formatDate(isoDate) {
    if (!isoDate) {
      return "—";
    }
    try {
      const d = new Date(isoDate);
      return d.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return isoDate;
    }
  }

  /**
   * Sayıyı binlik ayraçlarla biçimlendirir.
   * @param {number} n
   * @returns {string}
   */
  function formatNumber(n) {
    if (n === null || n === undefined) {
      return "0";
    }
    return Number(n).toLocaleString("tr-TR");
  }

  /**
   * Mobil sidebar menüsünü kurar.
   * @param {string} toggleSelector — hamburger buton seçici
   */
  function initSidebarToggle(toggleSelector) {
    const toggle = document.querySelector(toggleSelector);
    const sidebar = document.querySelector(".sidebar");
    if (!toggle || !sidebar) {
      return;
    }

    toggle.addEventListener("click", function () {
      const expanded = this.getAttribute("aria-expanded") === "true";
      this.setAttribute("aria-expanded", String(!expanded));
      sidebar.classList.toggle("open");
    });

    // Escape ile kapat
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        toggle.setAttribute("aria-expanded", "false");
        sidebar.classList.remove("open");
      }
    });
  }

  /**
   * Çevrimdışı durum bildirimi kurar.
   * @param {HTMLElement} offlineBanner
   */
  function initOfflineBanner(offlineBanner) {
    if (!offlineBanner) {
      return;
    }

    function updateOfflineState() {
      if (!navigator.onLine) {
        offlineBanner.hidden = false;
      } else {
        offlineBanner.hidden = true;
      }
    }

    window.addEventListener("online", updateOfflineState);
    window.addEventListener("offline", updateOfflineState);
    updateOfflineState();
  }

  // Public API
  window.NovaUi = {
    requireAuth,
    requireAdmin,
    isAdmin,
    logout,
    showStatus,
    setLoading,
    formatDate,
    formatNumber,
    initSidebarToggle,
    initOfflineBanner,
    getCookie,
  };
})();
