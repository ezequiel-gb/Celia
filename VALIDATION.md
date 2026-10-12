# Release validation

Verified on 2026-10-13 on the existing Windows x64 computer using Python 3.12.14.

- Copied the source into a separate installation directory containing spaces.
- Created a fresh virtual environment with system-site-packages disabled.
- Installed dependencies from PyPI and recorded the complete installed versions in service/requirements.lock.txt. pip check reported no broken requirements.
- Downloaded the official tunnel-client v0.0.16 archive and verified its pinned SHA-256 before extraction.
- Generated a profile using a dummy tunnel ID and newly created disposable Projects/Vault folders. The installer completed its local launcher check without a credential or live tunnel connection.
- Passed all 9 filesystem policy tests and 4 tray lifecycle tests.
- Passed real stdio MCP discovery of 14 tools and create/write/edit/read/move/delete plus denied-path checks.
- Passed the Windows hidden-parent/child Job Object termination check.
- Replaced the original private ODT test dependency with a generated synthetic ODT fixture.
- Scanned the source upload for personal paths, known account identifiers, credential patterns and excluded runtime/data artifacts before packaging.

The working original installation's ChatGPT connection was previously tested separately. This release verification does not use its credentials, tunnel or data. It does not create a new OpenAI tunnel or test ChatGPT account eligibility for another user.

GitHub Actions is supplied but has not run until this source is uploaded. A separate clean Windows machine/VM and another account have not been tested. Desktop/startup shortcut creation is inherited from the previously tested live installation and was intentionally not executed by the disposable installer, to avoid replacing the working shortcuts.
