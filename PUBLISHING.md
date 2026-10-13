# Publish this source to GitHub

Upload only this source folder, never the live installation's parent folder. The generated source ZIP contains no local configuration, working vault, API keys, runtime recovery data or tunnel binaries.

The project repository is [ezequiel-gb/Celious](https://github.com/ezequiel-gb/Celious). New users should follow INSTALLATION-A-TO-Z.md; these instructions are for maintaining and repackaging the source.

1. Work on a copy or branch containing only the published source. Initialise Git locally if needed and connect it to the intended repository.
2. Stage the source, inspect the staged diff and ensure ignored personal files are absent. Do not force-add ignored files.
3. Commit and push your intended changes. Include .github and .gitignore. A ZIP alone in the repository does not make the Windows workflow run.
4. Inspect the Windows verification run. It needs no OpenAI secrets. Record the resulting run URL in VALIDATION.md after it passes.
5. Before promoting a release for general reuse, choose a licence, configure a private security-reporting contact and validate the recipe on another Windows computer/account. Account-specific authorisation and ChatGPT setup still require the operator's own account.

To rebuild the allowlisted upload ZIP, run `py -3.12 package.py`. It checks source text for likely secrets, personal Windows profile paths and account-specific tunnel IDs, then writes dist/celious-files-source.zip and its SHA-256. It intentionally excludes config.json, runtime data, working folders, binaries and virtual environments, even after installation. Review changes yourself as well: automated pattern scans do not catch every possible secret.

Local test success does not establish marketplace eligibility or OpenAI access for other accounts. A private tunnel and a public source repository are separate things.
