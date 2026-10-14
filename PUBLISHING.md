# Publish this source to GitHub

Upload only this source folder, never the live installation's parent folder. The generated source ZIP contains no local configuration, working vault, API keys, runtime recovery data or tunnel binaries.

The project repository is [ezequiel-gb/Celious](https://github.com/ezequiel-gb/Celious). New users should follow INSTALLATION-A-TO-Z.md; these instructions are for maintaining and repackaging the source.

1. Work on a copy or branch containing only the published source. Initialise Git locally if needed and connect it to the intended repository.
2. Stage the source, inspect the staged diff and ensure ignored personal files are absent. Do not force-add ignored files.
3. Commit locally and run package.py --check-tracked --check-history 1181f82fd6df5802cf5cc4317dd35ce3f42799b0, package.py --verify --check-tracked, test_package.py, the isolated suites and test_installation.py. Preserve prior commits; inspect all unpublished commit trees, not just the final ZIP. Do not run mutation tests against a production installation.
4. Only after explicit publication approval, push a development branch (never directly overwrite main) and inspect Windows verification for its exact SHA. It fetches history for the pinned public-v0.2 fixture, installs/checks dependencies, validates package privacy/membership/manifest/checksum and subsequent commit trees, runs real disposable fresh-install/upgrade tests and all file/memory/tray checks. No OpenAI secret is needed. A ZIP alone in the repository does not run CI.
5. Record the actual passing run URL/SHA in VALIDATION.md without presenting historical runs as new evidence. Review the complete PR before approved merge/tag/release steps. Further commits need their own passing checks.
6. Before promoting general reuse, obtain owner approval of a licence and a private reporting channel. MIT, Apache-2.0 and GPL-3.0 are options; none is selected here. Prefer GitHub Private Vulnerability Reporting over publishing a personal address. Enabling repository settings is a separate approved GitHub action. Another operator's account/ChatGPT acceptance and optional Obsidian navigation remain separate checks.

To build the allowlisted ZIP (deterministic for identical source bytes), run `py -3.12 package.py --check-tracked`. It checks likely secrets, personal profile paths, account-specific IDs and email addresses requiring review, rejects linked source files and requires Git tracked paths to equal the allowlist. It includes a generated per-file PACKAGE-MANIFEST.json and writes dist/celious-files-source.zip plus SHA256SUMS.txt. Run `py -3.12 package.py --verify --check-tracked` to check CRC, exact membership, every source byte, privacy rules, manifest and ZIP checksum. Private config/runtime/data/binaries/environments remain excluded. Automated patterns do not identify every possible private datum; review manually too. Any later approved LICENSE must be added deliberately to the allowlist and retested.

Local test success does not establish marketplace eligibility or OpenAI access for other accounts. A private tunnel and a public source repository are separate things.
