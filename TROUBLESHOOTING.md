# Troubleshooting learned during setup

| Symptom | Resolution in this package |
| --- | --- |
| PowerShell says running scripts is disabled | Use Install.cmd and Start-Celia.cmd. They launch Python directly; changing global execution policy is unnecessary. |
| “No valid key entered” or paste appears to do nothing | Use the masked graphical input, Ctrl+V, and the actual secret beginning with sk-. “Celia API” is its label. The field intentionally hides input. |
| “n8n” appears as a service/project | A Platform project label does not install or require n8n. This program has no n8n dependency. Verify the selected organization and tunnel permissions. |
| Server executable not found when the folder contains spaces | Setup creates a quoted command with forward-slash paths. Regenerate the profile through setup instead of manually inserting unescaped backslashes. |
| Tray stays Starting | The controller keeps full MCP imports out of the GUI worker thread, initializes COM on WMI threads and prevents concurrent monitoring while the key dialog is open. Inspect service/.runtime/tray-connection.log if the current version still fails. |
| Tunnel absent from ChatGPT | Confirm the tunnel belongs to the intended Platform organization, is associated with the target ChatGPT workspace and the operator has Tunnels Read + Use. Workspace plugin permissions are separate. |
| Discovery fails | Keep the tray green during discovery. Check the local diagnostic log, authorized roots and installed Python dependencies. Run service/.venv/Scripts/python.exe service/connect.py --check for local checks without a key. |
| Connected terminal closes and tools stop responding | A foreground terminal owns its process. Use the tray shortcut for a hidden managed process. Closing the panel leaves the tray running; Exit stops the connection. |
| Icon is not next to the clock | Look in the Windows hidden-icons arrow and drag the Celia icon onto the visible tray area. |
| Access denied for a path | Use a configured root alias and a relative path. Check writable/read-only flags and whether the path is hidden, linked or outside the root. Cloud placeholders and junctions are not ordinary local folders. |
| Delete fails on another drive | Recovery storage is under service/.runtime. Recoverable rename requires the target and recovery storage to share a volume; use same-volume roots or keep those files undeleted. |
| Old terminal and tray are both running | After successful diagnostics, the tray stops matching clients for this installed executable and tunnel before starting its managed connection. Do not share one tunnel across simultaneous installations. |
| Key was pasted into chat, a screenshot or a repository | Revoke it in Platform, create a replacement with minimal tunnel permissions, exit Celia to forget the old key, then enter the replacement privately. Removing text alone does not revoke a key. |

Review logs locally before sharing: paths and account metadata may appear even when file contents and secrets are omitted. Never upload .runtime, config.json, .env files, copied keys or your working vault.

Reference: [OpenAI Secure MCP Tunnel troubleshooting](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
