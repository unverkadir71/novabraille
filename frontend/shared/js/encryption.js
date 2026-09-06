// Nova Braille — Client-Side Encryption
//
// Web Crypto API tabanlı PBKDF2 + AES-256-GCM şifreleme.
// Plan v9 referansı: Bölüm 1.11.1, ADR-004.
//
// Sunucu şifreleme anahtarına HİÇBİR ZAMAN erişmez.
// Sadece ciphertext, iv ve salt depolar.
// Parola kaybı = veri kurtarılamaz.

(function () {
  "use strict";

  const ALGORITHM = "AES-GCM";
  const KEY_LENGTH = 256;
  const IV_LENGTH = 12;
  const SALT_LENGTH = 16;
  const PBKDF2_ITERATIONS = 600_000;
  const PBKDF2_HASH = "SHA-256";

  /**
   * Kullanıcı parolasından AES anahtarı türetir.
   * @param {string} password
   * @param {Uint8Array} salt
   * @returns {Promise<CryptoKey>}
   */
  async function deriveKey(password, salt) {
    const encoder = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      "raw",
      encoder.encode(password),
      "PBKDF2",
      false,
      ["deriveKey"]
    );
    return crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: salt,
        iterations: PBKDF2_ITERATIONS,
        hash: PBKDF2_HASH,
      },
      keyMaterial,
      { name: ALGORITHM, length: KEY_LENGTH },
      false,
      ["encrypt", "decrypt"]
    );
  }

  /**
   * Çeviri verisini şifreler.
   *
   * @param {string} password — kullanıcının Nova Braille parolası
   * @param {object} data — çeviri verisi ({source, braille, metadata})
   * @returns {Promise<{ciphertext: string, iv: string, salt: string}>}
   */
  async function encrypt(password, data) {
    const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
    const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
    const key = await deriveKey(password, salt);

    const encoder = new TextEncoder();
    const plaintext = encoder.encode(JSON.stringify(data));

    const encrypted = await crypto.subtle.encrypt(
      { name: ALGORITHM, iv: iv },
      key,
      plaintext
    );

    return {
      ciphertext: _arrayBufferToBase64(encrypted),
      iv: _arrayBufferToBase64(iv),
      salt: _arrayBufferToBase64(salt),
    };
  }

  /**
   * Şifreli veriyi çözer.
   *
   * @param {string} password
   * @param {string} ciphertextBase64
   * @param {string} ivBase64
   * @param {string} saltBase64
   * @returns {Promise<object>} — orijinal çeviri verisi
   */
  async function decrypt(password, ciphertextBase64, ivBase64, saltBase64) {
    const iv = _base64ToArrayBuffer(ivBase64);
    const salt = _base64ToArrayBuffer(saltBase64);
    const ciphertext = _base64ToArrayBuffer(ciphertextBase64);

    const key = await deriveKey(password, salt);

    const decrypted = await crypto.subtle.decrypt(
      { name: ALGORITHM, iv: iv },
      key,
      ciphertext
    );

    const decoder = new TextDecoder();
    return JSON.parse(decoder.decode(decrypted));
  }

  // ---------- Yardımcılar ----------

  function _arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  function _base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  // ---------- Public API ----------

  window.NovaBrailleEncryption = {
    encrypt,
    decrypt,
    ALGORITHM,
    PBKDF2_ITERATIONS,
    PBKDF2_HASH,
  };
})();