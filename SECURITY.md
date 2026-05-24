# Security Policy

> 🇷🇺 Русская версия: [`SECURITY.ru.md`](SECURITY.ru.md)

## Supported versions

Mneme is pre-1.0. Only the latest minor version receives security
patches; older releases are not maintained.

| Version | Supported |
|---|---|
| 0.1.x   | ✅ |
| < 0.1   | ❌ |

## Reporting a vulnerability

Please **do not open a public GitHub issue** for security reports.

Instead, use GitHub's private vulnerability reporting:

1. Open https://github.com/vladimir120307-droid/mneme/security/advisories/new
2. Describe the issue, including:
   - The affected version
   - Reproduction steps
   - The impact you observed (data exposure, RCE, DoS, etc.)
3. We will acknowledge within 72 hours and aim to publish a fix within
   30 days. A coordinated disclosure date will be agreed upon.

If GitHub's mechanism is unavailable, email the maintainer (address on
the GitHub profile). Encrypt sensitive details if possible.

## What's in scope

- The Mneme Python package, including the C++ extension.
- The REST server (`mneme serve`).
- The default sample configurations in `docs/`.

## What's out of scope

- Upstream issues in Ollama / OpenAI / sentence-transformers / SQLite —
  please report those upstream.
- Misuse: e.g. running `mneme serve` on a public network without
  authentication. The README and `docs/configuration.md` document the
  expected deployment posture.
