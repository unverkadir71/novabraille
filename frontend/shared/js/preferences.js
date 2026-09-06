// Nova Braille — Shared Preferences (Theme + Language)
//
// Theme and language preferences are stored in cookies and remembered across visits.
// No "auto" option. On first visit (no cookie):
//   Theme : system preference (prefers-color-scheme) detected → written to cookie
//   Language : browser language (navigator.language) detected → written to cookie
// Subsequent visits use the stored cookie value.
//
// Controls:
//   Theme  : <button role="switch" aria-checked data-pref-theme>
//   Language : <button aria-haspopup="menu" aria-expanded data-pref-locale-btn>
//            + <ul role="menu"> with <button role="menuitem" data-locale>
//
// Loaded synchronously in <head> to prevent FOUC.

(function () {
  "use strict";

  var THEME_COOKIE = "nova_theme";   // light | dark
  var LOCALE_COOKIE = "nova_locale"; // ISO 639-1 codes
  var COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

  // 8 supported UI languages (same as translation languages)
  var LOCALE_LABELS = {
    tr: "Türkçe",
    en: "English",
    de: "Deutsch",
    fr: "Français",
    es: "Español",
    ar: "العربية",
    ru: "Русский",
    pt: "Português",
  };

  // All valid locale codes
  var VALID_LOCALES = Object.keys(LOCALE_LABELS);

  // ── Cookie helpers ─────────────────────────────────────────

  function getCookie(name) {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var parts = cookies[i].trim().split("=");
      if (parts[0] === name) {
        return decodeURIComponent(parts.slice(1).join("="));
      }
    }
    return null;
  }

  function setCookie(name, value) {
    var isHttps = window.location.protocol === "https:";
    var cookie = name + "=" + encodeURIComponent(value) +
      "; path=/; max-age=" + COOKIE_MAX_AGE + "; SameSite=Lax";
    if (isHttps) {
      cookie += "; Secure";
    }
    document.cookie = cookie;
  }

  // ── System / browser detection ─────────────────────────────

  function systemPrefersDark() {
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function browserLocale() {
    var raw = (navigator.language || navigator.userLanguage || "tr").toLowerCase();
    var lang = raw.slice(0, 2);

    // Direct match against our 8 supported locales
    if (LOCALE_LABELS[lang]) {
      return lang;
    }

    // Portuguese: accept pt-BR, pt-PT → pt
    if (raw.slice(0, 3) === "pt-") {
      return "pt";
    }

    // Arabic: accept ar-XX variants
    if (lang === "ar") {
      return "ar";
    }

    // Default to Turkish
    return "tr";
  }

  // ── Theme ───────────────────────────────────────────────────

  function getTheme() {
    var theme = getCookie(THEME_COOKIE);
    if (theme === "light" || theme === "dark") {
      return theme;
    }
    // No cookie → detect system preference and persist
    theme = systemPrefersDark() ? "dark" : "light";
    setCookie(THEME_COOKIE, theme);
    return theme;
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  function setTheme(theme) {
    if (theme !== "light" && theme !== "dark") {
      theme = "light";
    }
    setCookie(THEME_COOKIE, theme);
    applyTheme(theme);
    syncThemeButton(theme);
  }

  function toggleTheme() {
    setTheme(getTheme() === "dark" ? "light" : "dark");
  }

  var SUN_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  var MOON_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  function syncThemeButton(theme) {
    var btn = document.querySelector('[data-pref-theme]');
    if (!btn) return;
    var isDark = theme === "dark";
    btn.setAttribute("aria-checked", isDark ? "true" : "false");
    var label = btn.querySelector(".pref-btn-label");
    if (label) {
      label.textContent = isDark ? "Dark theme" : "Light theme";
    }
    var icon = btn.querySelector(".pref-btn-icon");
    if (icon) {
      icon.innerHTML = isDark ? MOON_SVG : SUN_SVG;
    }
    btn.setAttribute("aria-label", isDark ? "Dark theme" : "Light theme");
  }

  // ── Language ────────────────────────────────────────────────

  function getLocale() {
    var locale = getCookie(LOCALE_COOKIE);
    if (VALID_LOCALES.indexOf(locale) !== -1) {
      return locale;
    }
    // No cookie → detect browser language and persist
    locale = browserLocale();
    setCookie(LOCALE_COOKIE, locale);
    return locale;
  }

  function setLocale(locale) {
    if (VALID_LOCALES.indexOf(locale) === -1) {
      locale = "tr";
    }
    setCookie(LOCALE_COOKIE, locale);
    document.documentElement.lang = locale;
    syncLocaleButton(locale);
    closeLocaleMenu();
  }

  function syncLocaleButton(locale) {
    var btn = document.querySelector('[data-pref-locale-btn]');
    if (btn) {
      var label = btn.querySelector(".pref-btn-label");
      if (label) {
        label.textContent = LOCALE_LABELS[locale] || locale;
      }
      btn.setAttribute("aria-label", "Language: " + (LOCALE_LABELS[locale] || locale));
    }
    // Mark the active menu item
    var items = document.querySelectorAll('[data-locale]');
    items.forEach(function (item) {
      if (item.getAttribute("data-locale") === locale) {
        item.setAttribute("aria-current", "true");
      } else {
        item.removeAttribute("aria-current");
      }
    });
  }

  // ── Language menu (flyout) ──────────────────────────────────

  function toggleLocaleMenu() {
    var btn = document.querySelector('[data-pref-locale-btn]');
    var menu = document.querySelector('.pref-menu-list');
    if (!btn || !menu) return;
    var expanded = btn.getAttribute("aria-expanded") === "true";
    setLocaleMenuState(!expanded);
  }

  function setLocaleMenuState(open) {
    var btn = document.querySelector('[data-pref-locale-btn]');
    var menu = document.querySelector('.pref-menu-list');
    if (!btn || !menu) return;
    var wasOpen = !menu.hidden;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    menu.hidden = !open;
    if (open) {
      // Focus first menu item
      var first = menu.querySelector('[data-locale]');
      if (first) first.focus();
    } else if (wasOpen) {
      // Only return focus to button if menu was actually open
      btn.focus();
    }
  }

  function closeLocaleMenu() {
    setLocaleMenuState(false);
  }

  // ── Control binding ─────────────────────────────────────────

  function initControls() {
    var themeBtn = document.querySelector('[data-pref-theme]');
    var localeBtn = document.querySelector('[data-pref-locale-btn]');
    var localeItems = document.querySelectorAll('[data-locale]');

    if (themeBtn) {
      themeBtn.addEventListener("click", toggleTheme);
      syncThemeButton(getTheme());
    }

    if (localeBtn) {
      localeBtn.addEventListener("click", toggleLocaleMenu);
    }

    localeItems.forEach(function (item) {
      item.addEventListener("click", function () {
        setLocale(item.getAttribute("data-locale"));
      });
    });

    // Close menu on outside click
    document.addEventListener("click", function (e) {
      var menu = document.querySelector('.pref-menu');
      if (menu && !menu.contains(e.target)) {
        closeLocaleMenu();
      }
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeLocaleMenu();
      }
    });

    syncLocaleButton(getLocale());
  }

  // ── Startup ─────────────────────────────────────────────────

  // Apply theme before page render (FOUC prevention)
  applyTheme(getTheme());
  document.documentElement.lang = getLocale();

  // Bind controls when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initControls);
  } else {
    initControls();
  }

  // Public API
  window.NovaPrefs = {
    getTheme: getTheme,
    setTheme: setTheme,
    toggleTheme: toggleTheme,
    applyTheme: applyTheme,
    getLocale: getLocale,
    setLocale: setLocale,
    THEME_COOKIE: THEME_COOKIE,
    LOCALE_COOKIE: LOCALE_COOKIE,
  };
})();