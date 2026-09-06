# Nova Braille — Contributing Guide

Thank you for your interest in contributing to Nova Braille!

## Ways to Contribute

- **Bug reports:** Report bugs via GitHub Issues
- **Feature requests:** Share your feature ideas
- **Code contributions:** Submit pull requests
- **Documentation:** Fix or expand documentation
- **Translations:** Add new language support or improve existing translations
- **Braille validation:** Test the accuracy of Braille outputs

## Code Contribution Process

1. **Open an issue** — Discuss major changes before coding
2. **Fork** — Fork the repo to your account
3. **Create a branch** — `git checkout -b feat/your-feature`
4. **Make changes** — Write your code
5. **Test** — Run `uv run pytest tests/ -v`
6. **Lint** — Run `uv run ruff check .`
7. **Commit** — Use `type: description` commit message format
8. **Open a PR** — Create a pull request describing your change

## Commit Message Format

```
<type>: <short description>

Types: feat, fix, refactor, test, docs, chore, ci
```

## Development Environment

```bash
# Requirements: Python >= 3.13, Liblouis 3.38.0, UV

git clone https://github.com/unverkadir71/novabraille.git
cd novabraille
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Start development server
uv run uvicorn backend.src.main:app --reload
```

## Code Standards

- PEP 8, 100 character line width
- Ruff: E, F, I, N, UP, B, SIM rules
- mypy strict mode
- Write tests for all new code
- >= 80% test coverage in service layer

## Accessibility

Nova Braille aims for WCAG 2.2 AA compliance. All changes must:

- Use semantic HTML
- Be keyboard accessible
- Be tested with screen readers (e.g., NVDA)
- Maintain sufficient color contrast

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md) code of conduct.
