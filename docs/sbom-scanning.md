# Nova Braille — SBOM ve Image Scan Konfigürasyonu
#
# Güvenlik taraması için kullanılan araçlar ve komutlar.
# CI/CD pipeline'ına entegre edilebilir (F7.10 atlandı).

## SBOM (Software Bill of Materials) — Syft

```bash
# Docker image'dan SBOM oluştur
syft novabraille:latest -o spdx-json > sbom.spdx.json
syft novabraille:latest -o cyclonedx-json > sbom.cyclonedx.json

# Çoklu mimari için
syft novabraille:latest --platform linux/amd64 -o spdx-json > sbom-amd64.spdx.json
syft novabraille:latest --platform linux/arm64 -o spdx-json > sbom-arm64.spdx.json
```

## Image Vulnerability Scan — Trivy

```bash
# Kritik ve yüksek şiddetli güvenlik açıklarını tara
trivy image --severity CRITICAL,HIGH novabraille:latest

# JSON raporu
trivy image -f json -o trivy-report.json novabraille:latest

# Ignore file ile bilinen false positive'lar
trivy image --ignorefile .trivyignore novabraille:latest
```

## Release İmzası — Cosign

```bash
# Keyless signing (GitHub Actions OIDC)
cosign sign ghcr.io/novabraille/novabraille:latest

# Doğrulama
cosign verify ghcr.io/novabraille/novabraille:latest

# Manuel imza (CI yoksa)
cosign generate-key-pair
cosign sign --key cosign.key ghcr.io/novabraille/novabraille:latest
```

## Multi-Arch Build

```bash
# Buildx builder oluştur
docker buildx create --name novabraille-builder --use

# Çoklu mimari build + push
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ghcr.io/novabraille/novabraille:latest \
    --tag ghcr.io/novabraille/novabraille:$(git describe --tags --always) \
    --push \
    .

# Sadece build (push yok)
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag novabraille:latest \
    --load \
    .
```

## Trivy Ignore File (.trivyignore)

```
# Python base image kaynaklı, uygulama kodunu etkilemez
CVE-2024-xxxx

# Debian base image, patch yok
CVE-2024-yyyy
```

## Ön Koşullar

```bash
# Araç kurulumları
brew install syft cosign trivy          # macOS
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh  # Linux
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh  # Linux
```
