# Celious Files for Windows

Celious is our independent Windows implementation, inspired by the original Celia project. References to Celia in original materials and to components such as Celia Core describe that original project, not a claim that those components are installed here.

Celious Files connects ChatGPT to selected local folders through an MCP file server and an outbound OpenAI Secure MCP Tunnel. A Windows tray switch starts and stops the connection without a terminal. Source release: 0.3.0.

## Second Brain extension

Version 0.3.0 adds an opt-in Markdown memory extension: evidence-backed archiving, contextual retrieval, duplicate/conflict review, decision history and transactional recovery. [Second Brain setup, workflow and limits](SECOND-BRAIN.md). Existing configurations retain the original 14 tools; enabling memory exposes five additional tools on the same service and tunnel. No model API calls or background workers are added.

## Does Celious Files cost anything?

**Celious Files itself has no download, installation or subscription fee. It makes no paid AI model API calls. Purchasing API credits is not a step in this setup.** You use your own Windows computer and existing internet connection.

Your **ChatGPT Plus subscription** pays for ChatGPT access, with its normal usage limits. **OpenAI Platform** is where you manage the tunnel connecting ChatGPT to your computer. The **API key** is a private access credential for that connection: creating it is not a credit purchase or a new subscription. Celious uses it for tunnel authentication, not to buy AI responses. ChatGPT and paid model API usage have [separate billing](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform).

**What remains uncertain:** the [official tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) and [API pricing page](https://developers.openai.com/api/docs/pricing), checked on 13 October 2026, do not give a tunnel-specific creation/operation tariff or an explicit zero-charge guarantee. We therefore cannot promise that OpenAI's tunnel service is unconditionally free for every account or forever. This is not evidence that you need to buy API credits.

**Before installing:** check that your account offers the custom tunnel connection and the read/write actions you need. Current official guidance does not establish full Celious read/write access for every personal Plus account. Buying credits does not establish that permission. See the guide's [costs, keys and Plus access explanation](INSTALLATION-A-TO-Z.md#costs-keys-and-chatgpt-plus-access), including how to check billing without making a purchase.

## Start here

**Start here if you have never used Celious:** [Follow the complete installation guide](INSTALLATION-A-TO-Z.md). It explains how to download this repository, prepare Windows, create your own OpenAI tunnel and key, enter the key privately, connect ChatGPT and verify every file operation. No knowledge of this project's development history is required.

Read [Project explained](PROJECT-EXPLAINED.md) for the purpose and components. You need a Windows x64 computer, Python 3.12 and the account permissions described above. You do not need Git, Codex or n8n.

| I want to… | Open |
| --- | --- |
| Install from scratch | [A-to-Z guide](INSTALLATION-A-TO-Z.md) |
| Understand the project | [Project explanation](PROJECT-EXPLAINED.md) |
| Fix a setup problem | [Troubleshooting](TROUBLESHOOTING.md) |
| Understand access and recovery | [Security boundaries](SECURITY.md) |
| Review actual verification | [Validation record](VALIDATION.md) |

The rest of this README is the shorter technical overview.

Download this public repository from **Code → Download ZIP**, extract it, and follow the A-to-Z guide. [Repository](https://github.com/ezequiel-gb/Celious).

This repository contains the file server, Markdown vault starter and tray controller. Celia Core, Celia Engine, Miles, autonomous agents, arbitrary command execution, Git tooling and nine-workspace configurations are outside this implementation.

## Repeatable installation

1. Install **Python 3.12, 64-bit**, from [python.org](https://www.python.org/downloads/windows/), including Tcl/Tk, pip and the Python launcher. Windows x64 is required. Administrator privileges and PowerShell execution-policy changes are unnecessary.
2. Download or clone this repository into a permanent ordinary local folder, such as `C:\Apps\Celious Files`. Avoid OneDrive placeholders, junctions and symlinks; moving the installation later requires reconfiguration and new shortcuts.
3. In OpenAI Platform, choose the intended organisation and create a tunnel. Associate it with the ChatGPT workspace you actually use. Record its `tunnel_...` ID. Create a restricted runtime secret named **Celious API** with **Tunnels Read + Use**. The name is only a label; do not enter it as the secret. Creating or managing tunnels requires separate **Tunnels Read + Manage** permissions. Verify your account's access using the [official tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
4. Double-click `Install.cmd`. Enter the tunnel ID when prompted. This creates an isolated Python environment, installs locked dependency versions, downloads official tunnel-client v0.0.16 with SHA-256 verification, prepares a local profile, creates empty authorised data folders and installs Desktop/local shortcuts. It never asks for an API key.
5. Open **Celious Switch** or `Start-Celious.cmd`. Click the switch and paste the actual runtime secret privately into the masked box using Ctrl+V. Wait for green **Connected in the background**.
6. If your account provides the required access, in [ChatGPT Plugins](https://chatgpt.com/plugins) add a custom MCP server, choose **Tunnel**, select your tunnel, configure authentication as required for your own server, review the permissions, and create the plugin. Enable it in your conversation. Follow the current [official connection instructions](https://developers.openai.com/api/docs/guides/custom-mcp-server) and the guide's Plus access check above.
7. Test from ChatGPT: “Use Celious Files to list the configured roots and read Vault/INDEX.md. Create Inbox/celious-check.txt containing hello, read it, edit hello to ready, then delete that test file.” Verify the requested operations succeeded. Only use a disposable test file.
8. Switch **OFF**, request a fresh Celious tool call, and confirm the local connection is unavailable. Switch ON again and retry. Cached answers do not prove availability.

### Choose your own folders

Instead of step 4, open Command Prompt in the repository and run:

```bat
py -3.12 setup.py --tunnel-id tunnel_YOUR_32_CHARACTER_ID_HERE --projects "D:\Work\Projects" --vault "D:\Work\Celious Vault" --shortcuts --startup
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
ChatGPT -> OpenAI tunnel -> hidden tunnel-client -> stdio MCP server -> authorised roots
                              ^
                       Windows tray switch
```

The server supports directory listing, text/document extraction, search, paginated base64 reads, UTF-8/base64 writes, exact-text edits, folder creation, moves, recoverable deletion and restoration. Optional proposed changes can be reviewed locally using `service/review.py`.

PDF, DOCX, ODT and XLSX reads extract content; they are not OCR or full document-layout editors. Overwriting a rich document should use a valid binary payload. Writes are limited to 10 MB per call. Paths must be relative to a configured root alias. Root deletion, traversal, hidden paths, Windows special paths, symlinks, junctions and hard-linked files are blocked by application policy.

Backups, trash and metadata logs are private local files under `service/.runtime`. Recovery is provided through `restore_deleted`; nonempty-folder deletion requires `recursive=true`. Moving items into recovery storage requires the same volume; a root on a different drive can therefore be read/written but deletion may fail. Test this before depending on recovery across drive boundaries.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [SECURITY.md](SECURITY.md) and [PUBLISHING.md](PUBLISHING.md).

## Distribution

This package connects a private server. Publishing its source on GitHub does not itself publish a ChatGPT marketplace plugin. For costs and account access, use the section at the beginning of this README.

No licence has been assigned to this source package. Its owner should choose a licence before distributing it for general reuse. Downloaded dependencies retain their own licences; they are not bundled in the source ZIP.
