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

The original operator reported a personal ChatGPT Plus subscription and completed live read/write acceptance tests. This is account-specific evidence, not a guarantee of Plus eligibility. The checks below do not audit an OpenAI billing ledger or establish that tunnel traffic has a zero tariff. The documentation's current [costs and eligibility review](INSTALLATION-A-TO-Z.md#costs-keys-and-chatgpt-plus-access) separates those unresolved questions from verified application behaviour.

## Fresh GitHub Windows runner

The published repository also passed [Windows verification run 38319770042](https://github.com/ezequiel-gb/Celious/actions/runs/38319770042) for source commit `f5902c9e7fce54c64a3cf189d788213a0365fed1`.

The fresh GitHub-hosted windows-latest environment checked out this repository, installed Python 3.12 x64, ran setup with the locked dependencies and official tunnel download, then passed the 9 filesystem policy tests, 4 tray lifecycle tests, real stdio MCP protocol checks and hidden-process shutdown test. No API secret, live account connection or production folders were used.

This validates local installation on a second Windows environment. Another person's live ChatGPT account/connection and an interactive installation on a second physical PC have not been tested. Desktop/startup shortcut creation is inherited from the previously tested live installation and was intentionally not executed by either disposable installer, to avoid writing interactive user shortcuts during automated verification.
# Second Brain extension verification — 13 October 2026

Local Windows verification of v0.3.0 passed 13 isolated memory acceptance tests, the original 9 filesystem policy tests and 4 tray lifecycle tests. The original real stdio MCP workflow passed with memory disabled (14 tools). An isolated enabled server advertised 19 tools, rejected an incorrect approval digest, archived supplied text and retrieved its evidence through a fresh second MCP process. Hidden parent/child Job Object shutdown passed. No mutation test used production roots or a real tunnel credential.

Memory checks cover exact source/CRLF fidelity, evidence quotes, completeness, duplicate/conflict review, supersession and retained history, retrieval filters/ranking against distractors, nonexistent-result queries, output bounds, stable links, stale plans, failed writes/crash recovery, preservation of unrelated edits, path/read-only boundaries and competing processes. An explicit absence-conflict check protects against a file appearing after preview. Source/quote tampering is detected. These are bounded policy checks, not an independent security audit.

Deployment-specific live connector, account refresh, backup and application checks belong in a private installation report. The prior GitHub workflow results below describe v0.2.0; a v0.3.0 CI run is not claimed. Actual Obsidian navigation and a separate ChatGPT chat require environment-specific acceptance; a second MCP-session test does not establish those by itself.

