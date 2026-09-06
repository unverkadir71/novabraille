// Nova Braille — Ortak API İstemcisi
//
// Tüm dashboard sayfaları bu modülü kullanır.
// Sorumluluklar:
//   - fetch sarmalayıcı (credentials: same-origin)
//   - CSRF token yönetimi (X-CSRF-Token header)
//   - Hata ayrıştırma (code, message)
//   - Oturum sona erme tespiti (401 → login'e yönlendirme)
//   - JSON ve Form-encoded istek desteği

(function () {
  "use strict";

  const CSRF_COOKIE = "nova_csrf";
  const LOGIN_PATH = "login.html";

  /**
   * Çerez değerini okur.
   * @param {string} name
   * @returns {string|null}
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
   * CSRF token'ı çerezden okur.
   * @returns {string}
   */
  function getCsrfToken() {
    return getCookie(CSRF_COOKIE) || "";
  }

  /**
   * API hata nesnesi.
   */
  class ApiError extends Error {
    constructor(status, code, message) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code;
    }
  }

  /**
   * Yanıtı ayrıştırır; hata durumunda ApiError fırlatır.
   * @param {Response} res
   * @returns {Promise<object>}
   */
  async function parseResponse(res) {
    if (res.status === 204) {
      return null;
    }

    // JSON yanıt değilse metin döndür
    const contentType = res.headers.get("content-type") || "";
    let body;
    if (contentType.includes("application/json")) {
      body = await res.json();
    } else {
      body = await res.text();
    }

    if (!res.ok) {
      let code = "UNKNOWN_ERROR";
      let message = "Beklenmeyen bir hata oluştu.";

      if (typeof body === "object" && body !== null) {
        if (body.detail && typeof body.detail === "object") {
          code = body.detail.code || code;
          message = body.detail.message || message;
        } else if (body.detail && typeof body.detail === "string") {
          message = body.detail;
        }
      }

      // Oturum sona ermişse login'e yönlendir
      if (res.status === 401) {
        redirectToLogin();
      }

      throw new ApiError(res.status, code, message);
    }

    return body;
  }

  /**
   * Oturum sona erdiğinde login sayfasına yönlendirir.
   * Alt dizinlerden (admin/) doğru login yolunu hesaplar.
   */
  function redirectToLogin() {
    // Zaten login sayfasındaysak döngü yapma
    const current = window.location.pathname.split("/").pop();
    if (current === LOGIN_PATH) {
      return;
    }

    const pathDepth = window.location.pathname.split("/").filter(Boolean).length;
    const prefix = pathDepth > 1 ? "../".repeat(pathDepth - 1) : "";
    window.location.href = prefix + LOGIN_PATH + "?expired=1";
  }

  /**
   * GET isteği.
   * @param {string} path — /api/v1/... yolu
   * @returns {Promise<object>}
   */
  async function apiGet(path) {
    const res = await fetch(path, { credentials: "same-origin" });
    return parseResponse(res);
  }

  /**
   * POST isteği (JSON gövde).
   * @param {string} path
   * @param {object} body
   * @param {object} opts — { csrf: boolean } (varsayılan true)
   * @returns {Promise<object>}
   */
  async function apiPost(path, body, opts) {
    const options = {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    };

    if (!opts || opts.csrf !== false) {
      options.headers["X-CSRF-Token"] = getCsrfToken();
    }

    const res = await fetch(path, options);
    return parseResponse(res);
  }

  /**
   * POST isteği (Form-encoded gövde — login için).
   * @param {string} path
   * @param {object} fields — { key: value }
   * @returns {Promise<object>}
   */
  async function apiPostForm(path, fields) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(fields)) {
      params.append(key, value);
    }

    const res = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });
    return parseResponse(res);
  }

  /**
   * PUT isteği (JSON gövde).
   * @param {string} path
   * @param {object} body
   * @returns {Promise<object>}
   */
  async function apiPut(path, body) {
    const res = await fetch(path, {
      method: "PUT",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": getCsrfToken(),
      },
      body: JSON.stringify(body),
    });
    return parseResponse(res);
  }

  /**
   * DELETE isteği.
   * @param {string} path
   * @returns {Promise<object|null>}
   */
  async function apiDelete(path) {
    const res = await fetch(path, {
      method: "DELETE",
      credentials: "same-origin",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
    });
    return parseResponse(res);
  }

  /**
   * Multipart dosya yükleme (FormData).
   * @param {string} path
   * @param {FormData} formData
   * @returns {Promise<object>}
   */
  async function apiUpload(path, formData) {
    const res = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      body: formData,
    });
    return parseResponse(res);
  }

  // Public API
  window.NovaApi = {
    apiGet,
    apiPost,
    apiPostForm,
    apiPut,
    apiDelete,
    apiUpload,
    getCsrfToken,
    ApiError,
    redirectToLogin,
  };
})();
