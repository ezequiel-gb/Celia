# Release validation

## Current v0.4 release candidate

The readiness correction adds explicit memory opt-in (no silent initialization), reviewed public-baseline source upgrade, conditional WORKFLOW creation, package manifest/privacy/integrity checks and real disposable installer coverage. Local acceptance results for this candidate are recorded below; GitHub execution remains pending until an approved development-branch push. The older clean-install/runner evidence is labelled historical.

Local Windows x64 / Python 3.12.14 acceptance on 13 October 2026 passed:

- Two real disposable installers, each creating a new virtual environment with system-site-packages disabled, installing the locked dependencies and downloading/checking official tunnel-client v0.0.16. No actual key, live tunnel, shortcuts or production roots were used. pip check passed in both environments.
- Fresh --second-brain setup exposed 27 tools without creating a layout. The OFF/local CLI reviewed initialization created empty project/shared collections and WORKFLOW.md; later MCP inspection passed. Disabling memory returned the original 14-tool schema.
- The pinned public v0.2 source was extracted from Git, actually installed and tested before overlay. upgrade.py preview was non-mutating; ON-state, overlapping-backup and missing OFF acknowledgement were rejected. Apply preserved config fields/roots/tunnel, profile bytes and existing files; original code/config checkpoint CRC and contents were verified. The updated engine was present. Synthetic legacy records migrated byte-for-byte through the MCP alternative, preserving an existing CRLF workflow and valid provenance.
- All suites ran using the freshly installed environment: 3 package/overlay tests, 9 file-policy tests, 4 tray tests, 13 legacy memory tests and 17 project cases. **45 passed, 1 expected private-baseline skip**. Both stdio workflows and actual hidden parent/child shutdown passed. The project suite also ran separately against the available private baseline: all 17 passed, including the private case.
- Package checks validate exact allowlisted membership, source bytes, per-file manifest, ZIP CRC and SHA-256; privacy fixtures and a tampered ZIP are rejected. An interrupted source overlay restores originals and preserves added files; dependency-lock comparison tolerates line-ending differences.
- Python syntax and local documentation file links passed. Source/history privacy checks are repeated at the final commit/package boundary; the package checksum belongs in its generated SHA256SUMS.txt, avoiding a self-referential documentation hash.

The Windows workflow includes dependency verification, package and unpublished-history checks, real fresh-install/public-baseline upgrade coverage and all suites, with a 30-minute limit. **No v0.4 GitHub-hosted run has occurred yet.** Registry/download availability, hosted runner behavior and runtime duration must pass after an approved development-branch push. Public CI intentionally skips the private baseline and never receives private notes/backups. Real ChatGPT access, model-selected proactive invocation, interactive shortcuts on another computer and Obsidian remain environment-specific checks.

## Historical v0.2 clean installation

Verified on 2026-10-13 on the existing Windows x64 computer using Python 3.12.14, before the memory extension.

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

## Historical v0.2 GitHub Windows runner

The published repository also passed [Windows verification run 38319770042](https://github.com/ezequiel-gb/Celious/actions/runs/38319770042) for source commit `f5902c9e7fce54c64a3cf189d788213a0365fed1`.

The fresh GitHub-hosted windows-latest environment checked out this repository, installed Python 3.12 x64, ran setup with the locked dependencies and official tunnel download, then passed the 9 filesystem policy tests, 4 tray lifecycle tests, real stdio MCP protocol checks and hidden-process shutdown test. No API secret, live account connection or production folders were used.

This validates local installation on a second Windows environment. Another person's live ChatGPT account/connection and an interactive installation on a second physical PC have not been tested. Desktop/startup shortcut creation is inherited from the previously tested live installation and was intentionally not executed by either disposable installer, to avoid writing interactive user shortcuts during automated verification.
# Second Brain extension verification — 13 October 2026

Local Windows verification of v0.3.0 passed 13 isolated memory acceptance tests, the original 9 filesystem policy tests and 4 tray lifecycle tests. The original real stdio MCP workflow passed with memory disabled (14 tools). An isolated enabled server advertised 19 tools, rejected an incorrect approval digest, archived supplied text and retrieved its evidence through a fresh second MCP process. Hidden parent/child Job Object shutdown passed. No mutation test used production roots or a real tunnel credential.

Memory checks cover exact source/CRLF fidelity, evidence quotes, completeness, duplicate/conflict review, supersession and retained history, retrieval filters/ranking against distractors, nonexistent-result queries, output bounds, stable links, stale plans, failed writes/crash recovery, preservation of unrelated edits, path/read-only boundaries and competing processes. An explicit absence-conflict check protects against a file appearing after preview. Source/quote tampering is detected. These are bounded policy checks, not an independent security audit.

Deployment-specific live connector, account refresh, backup and application checks belong in a private installation report. The prior GitHub workflow results above describe v0.2.0; a v0.3.0 CI run is not claimed. Actual Obsidian navigation and a separate ChatGPT chat require environment-specific acceptance; a second MCP-session test does not establish those by itself.

# Project memory v0.4.0 — local isolated verification

The original 13 memory, 9 file-policy and 4 tray tests remain the regression baseline. The new 17-test project suite covers project spaces/identities, A/B/shared/cross retrieval, correct archive routing, review queue/resolve/reject, duplicate/conflict scope, supersession/history, provisional evidence, index rebuild, exact/stale plans, unrelated destination files, failed operations, hard interruption recovery, legacy byte preservation, isolated restoration to v0.3.0 and competing commit processes. A private verified-baseline migration case runs locally when available and explicitly skips in public environments without that private fixture.

The isolated stdio test advertises 27 tools and exercises all 13 memory endpoints, including supersede preview and rejection. A fresh second process retrieves persisted project data. The original 14-tool stdio workflow and real hidden parent/child shutdown remain tested separately. These checks use disposable roots and no real key or tunnel. Production migration/account refresh and model-selected proactive behavior belong in the private deployment report; unit tests alone do not prove universal tool invocation. No new GitHub workflow run/publication is claimed.

