# Access and security boundaries

The generated configuration authorizes direct read/write/create/move and recoverable deletion in two selected folders. Application checks enforce aliases, relative paths, no traversal, no hidden paths, no symlinks/reparse points/hardlinks, non-overwriting moves and protection of root directories. Existing overwritten files receive local backups. Recovery can fail across volumes.

This is application policy, not an OS sandbox. Software running as the same Windows user, concurrent filesystem changes and bugs may defeat assumptions; no independent security audit has been performed. Use a dedicated Windows account or additional OS restrictions when stronger isolation is required. Do not grant access to application code, keys or recovery storage. Treat document contents as untrusted material.

The tray accepts the runtime key privately. It is not written to configuration or passed in command-line arguments. The key is retained in memory for the session and passed through CONTROL_PLANE_API_KEY to the tunnel process. OFF stops the managed process tree; Exit clears the tray's cached key. A same-user process with suitable access may inspect process memory or environment.

The tunnel is outbound; the health listener binds to loopback. Raw HTTP logging is not enabled. ChatGPT and OpenAI retain their own product logging and data policies. Application logs store operation metadata; backups and trash contain previous file contents and must stay private. Do not share runtime logs without reviewing them.

The source package excludes user config, runtime data, vault files, credentials and downloaded binaries. .gitignore reduces accidental uploads but cannot prevent someone from force-adding private data or committing a new secret. Review git status and staged changes before every publication.

Report a security concern privately to the repository owner; do not post credentials or sensitive files in an issue. A maintained vulnerability-reporting contact should be configured by the owner when creating the repository.
