# What Celia Files is and how it works

Celia Files lets you use ChatGPT to work with files in folders you explicitly select on your Windows computer. You can ask for a document summary, a file search, an edited note, a new folder or a recoverable deletion. The assistant chooses tools, while local software performs permitted operations on disk.

## The problem it solves

A conversation alone does not provide direct access to an arbitrary local project folder. Manually uploading each file becomes cumbersome and can separate the answer from the latest version on disk. Celia Files provides a controlled working surface: the assistant can read the current file and save a requested result back into the selected workspace.

A Markdown vault adds durable context. Project notes, decisions and next actions can be saved as normal files, reviewed by a person and read in a later session. This only happens when information is actually saved; the software does not convert every conversation into memory automatically.

## The components

| Component | Responsibility | Where it lives |
| --- | --- | --- |
| ChatGPT | Understand requests and decide which tools to call | Your OpenAI account |
| Celia Files plugin | Present the server's tools in a conversation | ChatGPT plugin configuration |
| Secure MCP Tunnel | Transport requests between OpenAI and the local client | OpenAI tunnel plus local client |
| tunnel-client | Run the private connection and invoke the MCP server | Windows background process |
| Celia MCP server | Expose the 14 tools and enforce file policy | Local Python process |
| Celia tray switch | Start, check and stop the local connection | Windows icon and small control panel |
| Projects and Vault | Store the files you authorize | Selected local directories |

MCP means Model Context Protocol, the interface used to describe tools and exchange calls/results. “Celia API” is the runtime credential's name. This package does not create a separate public REST API or a new AI model.

```text
You request work in ChatGPT
          |
ChatGPT calls a Celia Files tool
          |
OpenAI tunnel delivers the request to the local client
          |
Local MCP server validates the root and relative path
          |
The requested file operation runs inside the allowed folder
          |
The result returns to ChatGPT
```

The tunnel uses an outbound connection, allowing this design to keep the file server private. Account access and associations are described in the [official OpenAI tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## Example: editing a project note

You ask: “Use Celia Files to read Projects/Example/status.md and change the deadline to Friday.” ChatGPT reads the file through a tool, requests an exact-text edit and receives its result. The server checks that the root exists, is writable and contains the allowed relative path. It saves the previous content before updating the file. You can inspect the result directly in Windows.

The tray controls availability. ON starts the local tunnel and server. Hiding the panel leaves them running. OFF ends the connection; Exit also discards the tray's cached secret. Starting the icon at login leaves it OFF until you decide to connect.

## What this release can do

The 14 tools cover root/directory listing, document reads, search, paginated binary reads, direct writes and text edits, folder creation, within-root moves, recoverable deletion/restoration and optional proposed changes. The exact implementation is in `service/server.py` and `service/engine.py`.

The server extracts text from PDF, DOCX, ODT and XLSX files and reads ordinary text/code files. It does not provide OCR or rich-document layout editing. Binary writes must contain valid bytes for the intended format. File write/read limits and format behavior are in README.md.

There is no direct copy-file tool; a client could read and write permitted file contents within the size limits. Proposed changes remain pending until reviewed locally. For example, run `service\.venv\Scripts\python.exe service/review.py` to list pending requests, then rerun it with a request ID to review and explicitly apply or reject it.

## Permission boundaries

The default installation grants direct mutations inside Projects and Vault. It rejects traversal, hidden/special paths, root deletion, symlinks, Windows junctions and hard-linked files. Overwrites receive backups; deletion moves content to private recovery storage. Recovery depends on retaining that storage and using the same volume.

These are application checks, not a separate Windows sandbox or independently audited security guarantee. Local software running as the same user may still access process memory or files. ChatGPT's own tool approvals and account restrictions remain separate. Read SECURITY.md before extending access.

## How this relates to the wider Celia project

This source release is the **file-access layer** plus a starter vault and a desktop connection switch. It does not contain Celia Core, Celia Engine, Miles, autonomous agent supervision, email processing, Git promotion workflows or the broader architecture described in reference material. Installing this package does not create those components or reproduce a nine-workspace deployment.

Those capabilities would require their own implementation, configuration and validation. The file-access layer can provide a useful foundation without claiming that the full ecosystem has been delivered.

## Installation and project status

Start with [INSTALLATION-A-TO-Z.md](INSTALLATION-A-TO-Z.md). Source and configuration examples are portable; actual folder paths, tunnel IDs, credentials and shortcuts are generated separately for each computer. No personal documents or live account settings are included.

The installer creates the local environment and downloads required dependencies. Each operator completes their own OpenAI account setup and live ChatGPT test. The package passed the checks recorded in VALIDATION.md; a second computer has not yet been certified. The code makes no model inference requests or credit purchases, and external account eligibility/costs must be checked separately.
