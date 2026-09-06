# Nova Braille — Security Policy

## Supported Versions

| Version | Support |
|---|---|
| v1.0.0-beta (latest) | ✅ Active security updates |

## Reporting a Vulnerability

If you discover a security vulnerability in Nova Braille, please report it
**privately via GitHub**:

1. Go to [Security Advisories](https://github.com/unverkadir71/novabraille/security/advisories/new)
2. Click "Report a vulnerability"
3. Describe the vulnerability in detail (affected version, steps to reproduce, potential impact)

**Do not report vulnerabilities as public issues.** We follow a coordinated
disclosure process.

## Response Process

1. Your report will be acknowledged within 48 hours
2. The vulnerability will be verified and its severity assessed
3. A fix will be developed
4. A new release will be published
5. The vulnerability will be publicly disclosed after the fix is released

## Security Measures

Nova Braille's security architecture:

- **Password hashing:** Argon2id (OWASP 2026 compliant)
- **Session management:** HttpOnly, Secure, SameSite=Lax cookie
- **CSRF protection:** Double Submit Cookie pattern
- **Database:** SQLAlchemy ORM (SQL injection protection)
- **File uploads:** Format validation, size limits, temporary file cleanup
- **Dependencies:** Regular security scanning

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities.
With your permission, we will credit you in the security advisory.
