# Contributing

Thanks for your interest in improving ZPL Converter.

## Reporting bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template. Include:
- The ZPL content that fails (or a minimal reproduction)
- Your Windows version and DPI setting
- The error shown in the app or in `%TEMP%\zpl_converter\zpl_converter.log`

## Suggesting features

Open a [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) issue before writing any code, so we can discuss fit and approach first.

## Submitting a pull request

1. Fork the repo and create a branch from `main`
2. Follow the local dev setup in the README (Python 3.12 venv, macOS ARM binary)
3. Keep changes focused — one fix or feature per PR
4. Test on macOS locally; Windows behaviour is validated by CI

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

Rendering requires the `assets/labelize` binary (macOS ARM) — see README.

## Code style

- Python 3.12, no external type stubs required
- No comments unless the reason is non-obvious
- No new runtime network calls — the app must stay fully offline
