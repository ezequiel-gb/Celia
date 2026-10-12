# Celia Files for Windows

Celia Files connects ChatGPT to selected local folders through an MCP file server and an outbound OpenAI Secure MCP Tunnel. A Windows tray switch starts and stops the connection without a terminal. Source release: 0.2.0.

**Start here if you have never used Celia:** [Follow the complete installation guide](INSTALLATION-A-TO-Z.md). It explains how to download this repository, prepare Windows, create your own OpenAI tunnel and key, enter the key privately, connect ChatGPT and verify every file operation. No knowledge of this project's development history is required.

Read [Project explained](PROJECT-EXPLAINED.md) for the purpose and components. You need a Windows x64 computer, Python 3.12 and an OpenAI account that permits tunnels and custom ChatGPT MCP connections. You do not need Git, Codex or n8n. The local installer does not purchase credits or subscribe to a service; check account eligibility before installing.

| I want to… | Open |
| --- | --- |
| Install from scratch | [A-to-Z guide](INSTALLATION-A-TO-Z.md) |
| Understand the project | [Project explanation](PROJECT-EXPLAINED.md) |
| Fix a setup problem | [Troubleshooting](TROUBLESHOOTING.md) |
| Understand access and recovery | [Security boundaries](SECURITY.md) |
| Review actual verification | [Validation record](VALIDATION.md) |

The rest of this README is the shorter technical overview.

Download this public repository from **Code → Download ZIP**, extract it, and follow the A-to-Z guide. [Repository](https://github.com/ezequiel-gb/Celia).

This repository contains the file server, Markdown vault starter and tray controller. Celia Core, Celia Engine, Miles, autonomous agents, arbitrary command execution, Git tooling and nine-workspace configurations are outside this implementation.

## Repeatable installation

1. Install **Python 3.12, 64-bit**, from [python.org](https://www.python.org/downloads/windows/), including Tcl/Tk, pip and the Python launcher. Windows x64 is required. Administrator privileges and PowerShell execution-policy changes are unnecessary.
2. Download or clone this repository into a permanent ordinary local folder, such as `C:\Apps\Celia Files`. Avoid OneDrive placeholders, junctions and symlinks; moving the installation later requires reconfiguration and new shortcuts.
3. In OpenAI Platform, choose the intended organization and create a tunnel. Associate it with the ChatGPT workspace you actually use. Record its `tunnel_...` ID. Create a restricted runtime secret named **Celia API** with **Tunnels Read + Use**. The name is only a label; do not enter it as the secret. Creating or managing tunnels requires separate **Tunnels Read + Manage** permissions. Verify your account's access using the [official tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
4. Double-click `Install.cmd`. Enter the tunnel ID when prompted. This creates an isolated Python environment, installs locked dependency versions, downloads official tunnel-client v0.0.16 with SHA-256 verification, prepares a local profile, creates empty authorized data folders and installs Desktop/local shortcuts. It never asks for an API key.
5. Open **Celia Switch** or `Start-Celia.cmd`. Click the switch and paste the actual runtime secret privately into the masked box using Ctrl+V. Wait for green **Connected in the background**.
6. In [ChatGPT Plugins](https://chatgpt.com/plugins), add a custom MCP server, choose **Tunnel**, select your tunnel, configure authentication as required for your own server, review the permissions, and create the plugin. Enable it in your conversation. This step depends on your account and workspace permissions; an existing Plus subscription alone is not proof of access on every account. Follow the current [official connection instructions](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
7. Test from ChatGPT: “Use Celia Files to list the configured roots and read Vault/INDEX.md. Create Inbox/celia-check.txt containing hello, read it, edit hello to ready, then delete that test file.” Verify the requested operations succeeded. Only use a disposable test file.
8. Switch **OFF**, request a fresh Celia tool call, and confirm the local connection is unavailable. Switch ON again and retry. Cached answers do not prove availability.

### Choose your own folders

Instead of step 4, open Command Prompt in the repository and run:

```bat
py -3.12 setup.py --tunnel-id tunnel_YOUR_32_CHARACTER_ID_HERE --projects "D:\Work\Projects" --vault "D:\Work\Celia Vault" --shortcuts --startup
```

Replace the example ID with your actual tunnel ID. The defaults are `data/Projects` and `data/Vault` inside this installation. Both roots receive direct read/write access and recoverable deletion. Choose folders deliberately: every ordinary file under them is potentially available to the connected assistant. Select narrow roots, separate from application code and runtime data. Projects and Vault cannot overlap. Existing files and vault starter documents are preserved.

`--startup` installs the tray icon at login **with the connection OFF**. Without it, launch the shortcut when needed. Your key remains only in this application's memory during the session and in the child tunnel client's environment. OFF stops the tunnel; Exit and reboot discard the cached key. There is no stored password and no always-on Windows service.

Optional `--plugin-url https://chatgpt.com/plugins/...` sets the tray's ChatGPT button. Intentional reconfiguration requires `--replace-config`; turn OFF and exit first. Re-run shortcut installation after moving or changing the Python environment. A failed installation can be retried; if configuration already exists, review it and explicitly use `--replace-config`.

## Verification

Use a fresh installation with disposable roots. Tests create and recoverably delete data in the configured Vault; do not point test installations at your production folders.

```bat
service\.venv\Scripts\python.exe service/test_service.py
service\.venv\Scripts\python.exe service/test_tray.py
service\.venv\Scripts\python.exe service/tray.py --self-test
```

These cover 9 filesystem policy tests, 4 tray lifecycle tests, discovery of 14 MCP tools and actual stdio create/write/edit/read/move/delete calls, plus termination of a hidden Windows parent and child process. They require no real API key. The supplied Windows GitHub Actions workflow installs with a dummy tunnel ID and runs these checks; it does not connect to an account or grant repository workflows a secret.

The installer uses requirements.lock.txt, which records the tested direct and transitive Python dependency versions. requirements.txt describes the six direct dependencies for future deliberate upgrades. Python patch versions, package hashes and the Windows runner image are not frozen; this is a repeatable installation recipe rather than a byte-identical build. See [VALIDATION.md](VALIDATION.md) for the release's actual verification results.

## How the components fit

```text
ChatGPT -> OpenAI tunnel -> hidden tunnel-client -> stdio MCP server -> authorized roots
                              ^
                       Windows tray switch
```

The server supports directory listing, text/document extraction, search, paginated base64 reads, UTF-8/base64 writes, exact-text edits, folder creation, moves, recoverable deletion and restoration. Optional proposed changes can be reviewed locally using `service/review.py`.

PDF, DOCX, ODT and XLSX reads extract content; they are not OCR or full document-layout editors. Overwriting a rich document should use a valid binary payload. Writes are limited to 10 MB per call. Paths must be relative to a configured root alias. Root deletion, traversal, hidden paths, Windows special paths, symlinks, junctions and hard-linked files are blocked by application policy.

Backups, trash and metadata logs are private local files under `service/.runtime`. Recovery is provided through `restore_deleted`; nonempty-folder deletion requires `recursive=true`. Moving items into recovery storage requires the same volume; a root on a different drive can therefore be read/written but deletion may fail. Test this before depending on recovery across drive boundaries.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [SECURITY.md](SECURITY.md) and [PUBLISHING.md](PUBLISHING.md).

## Cost and distribution

The installer makes no model inference calls, buys no credits and enables no paid model integration. Confirm current OpenAI account eligibility and costs separately; this project does not promise that every external service is free. Secure tunnels are for private connections; uploading this source to GitHub does not publish a ChatGPT marketplace plugin.

No license has been assigned to this source package. Its owner should choose a license before distributing it for general reuse. Downloaded dependencies retain their own licenses; they are not bundled in the source ZIP.
