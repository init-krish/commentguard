# Contributing to CommentGuard

Thanks for your interest in contributing! This project is open to improvements of all kinds.

## Getting Started

1. **Fork** the repo and clone your fork
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run tests: `cd backend && pytest tests/ -v`
5. Commit with a clear message: `git commit -m "feat: add multi-label support"`
6. Push and open a **Pull Request**

## What We're Looking For

- **Model improvements** — better classifiers, multi-label support, multilingual models
- **New site selectors** — extend the Chrome extension to support more platforms
- **Bug fixes** — especially around edge cases in comment parsing
- **Documentation** — tutorials, deployment guides, translations
- **Tests** — more test coverage is always welcome

## Code Style

- **Python**: Follow PEP 8. Use type hints where practical.
- **JavaScript**: No framework required. Keep the extension vanilla JS.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)

## Reporting Issues

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version, browser)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
