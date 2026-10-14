# Celious project memory v0.4.0

This is the current upgrade, archive and retrieval guide. Celious physically separates project memory while preserving original evidence and the existing file policy, tray, credentials and tunnel. No background observer, worker, model API call, new dependency, extra plugin or authorized root is added.

## Layout and identities

```text
Second Brain/
  INDEX.md
  WORKFLOW.md
  LAYOUT.md
  Projects/<project-name>/
    PROJECT.md
    INDEX.md
    Sources/
    Knowledge/
    History/
  Shared Knowledge/
    PROJECT.md
    INDEX.md
    Sources/
    Knowledge/
    History/
  Inbox/
    INDEX.md
    candidate-<uuid>.md
```

PROJECT.md contains an immutable project UUID and display name. Location comes from its containing folder. Display-name edits retain identity; physically renaming a collection still requires a reviewed link/index migration. Runtime plans, locks and journals remain outside the Markdown collection.

Sources preserves accessible text, completeness/reference and body SHA-256. Knowledge holds reviewed claims with ID, timestamps, type, topic/key/value, status, epistemic label, uncertainty, exact source quote/character offsets and links. History retains former versions. Indexes are rebuildable. The existing restricted YAML format and exact CRLF source fidelity remain unchanged.

## Upgrade and migration

Make a complete verified backup and test isolated restoration before the mandatory approval gate. Test this upgrade in disposable roots. With the existing tray connection OFF, install server.py, memory_tools.py, second_brain.py and project_memory.py beside the compatible v0.3 file engine. Retain its absent-target expected-digest check, personal roots/configuration, tray code, tunnel and credential behavior.

The existing optional config remains `"second_brain": {"root": "Projects", "path": "Celious/Second Brain"}`. Do not widen permissions. Call memory_migrate_preview, review its complete map/digest, then memory_commit with owner authorization. Migration never runs automatically on startup.

Migration uses journaled copy-and-redirect writes. Original source/knowledge/history files are preserved byte-for-byte in the selected project. Old paths become navigation-only redirects, excluded from knowledge scanning; they preserve previous citations/wiki links without duplicating facts. The layout marker activates last. Incomplete transactions block cooperating readers until recovery. Old-layout proposals remain private evidence but cannot be replayed.

Verify original file hashes/IDs/metadata/source quotes, links, indexes, retrieval and isolated rollback. Restart the same tray connection and refresh the existing ChatGPT tools. Memory disabled still exposes the original 14 tools. Enabled v0.4 exposes **27 tools: 14 file tools and 13 memory endpoints**. No separate tunnel is created.

## Retrieval

Call memory_projects to obtain the actual stable project ID. Pass project_id to memory_search for the selected project. Legacy search calls transparently use the default project (Celious) plus Shared Knowledge; every result reports its scope. include_shared defaults true and labels shared hits. Set it false for project-only work. cross_project defaults false and must be enabled only for an explicit broader request.

Matching selected-project records are prioritized; allowed shared/cross-project records follow lexical ranking. Search terms use OR matching, not exact multiword conjunction. Filters include topic, note_type and status. Default status is active. Empty status includes source/superseded record states for requested historical context; former History copies remain navigable separately.

Results include evidence, source paths/completeness, uncertainty, epistemic labels and provenance validity. A pending/superseded claim is not an accepted current decision, and an assertion remains an assertion. Related-note traversal does not import another project's text merely because a link exists. Invalid project IDs fail rather than guessing. There is no global mutable active-project setting across chats.

Project separation is a context-quality boundary; it does not revoke the owner's existing raw filesystem access. Those tools can bypass coordinated multi-note operations.

## Proactive identification and Archive to Celious

Server guidance asks ChatGPT to use memory_identify when the active, connector-enabled conversation contains decisions, requirements, preferences, fixes, milestones, lessons or unresolved questions. Supply only actually accessible text. The tool returns bounded exact quote spans, suggested types, speaker/provisional indicators and pending epistemic status, without saving notes.

Local cues are suggestions, not proof of importance or truth. Hypotheses, assistant suggestions and unknown speakers are not automatically accepted facts. Model recognition/tool invocation is best effort; there is no continuous conversation monitor or forced tool call.

Reliable explicit fallback: “Review this accessible conversation for Celious memory in project X.” Archive trigger: “Archive to Celious for project X.” The reasoning client should identify useful material, obtain the project ID, compare the proposal and explain what will be saved/skipped/pending/superseded.

1. Provide actual accessible chat text, export or explicit input. Mark partial, excerpt, user_supplied or complete_export honestly; never infer complete history from a title/summary.
2. Supply reviewed claims_json with string fields type, title, topic, key, value, evidence, epistemic and uncertainty. Optional links contain existing stable IDs. Evidence must match the supplied source exactly.
3. Call memory_archive_preview with explicit project_id. Review proposed contents, expected hashes, warnings and exact digest. Preview is not an accepted archive.
4. With owner authorization covering that exact retention, call memory_commit with the returned digest. Stale, altered, rejected or used plans fail.
5. Call memory_inspect and retrieve the saved note/source before reporting success.

Missing/uncertain project assignment creates a candidate in Inbox, not accepted project knowledge. memory_inbox returns bounded summaries; use existing paginated file reads for full review. memory_inbox_resolve_preview requires candidate ID plus explicit project ID, compares the chosen project's memory and prepares one archival/queue-closing plan. Review and commit separately. memory_reject records rejection and leaves accepted sources/knowledge/history unchanged.

Duplicate/conflict grouping uses project/topic/key. Identical keys in unrelated projects are not contradictions. Duplicate claims are skipped while retaining the new source; different active values become pending review. Shared promotion/cross-project consolidation is never silent. Multi-project material needs reviewed assignments/splits with exact excerpts and honest completeness. No original multi-project archive is retained as shared context without authorization.

## Decision changes

Archive the new source and reviewed replacement in the same project. memory_supersede_preview requires distinct knowledge IDs, matching topic/key, a reason and a replacement that is not epistemically pending. The reviewed plan retains exact prior versions in project History, marks the old record superseded and adds reciprocal links. Cross-project supersession is rejected. A hypothesis cannot silently become an accepted decision.

## Automation boundaries

| Behavior | Mechanism |
| --- | --- |
| Validation, scoped comparison, ranking, queue construction and transactions | Deterministic mechanics after a tool call |
| Identifying important material and choosing identify/preview | Model-dependent guidance in the active supported conversation |
| Explicit review/archive prompt | User-invoked fallback using available tools |
| Accepted archival/supersession | Reviewed exact-plan commit with owner authorization |
| Universal monitoring/inaccessible chat retrieval/guaranteed context injection | Not implemented or promised |

A successful proactive-trigger test demonstrates that session, not universal autonomy. A static imported skill is not assumed installed by a tool refresh. This upgrade adds neither another plugin nor an unverified draft-extension dependency.

## Inspection, indexes and recovery

memory_inspect checks source/candidate hashes, evidence, identity/location conflicts, duplicate/conflicting active claims, wiki links/redirects, indexes and pending review. memory_rebuild_preview deterministically proposes global/project/Inbox index repair; commit its exact digest separately. Pending reviews are surfaced, not silently resolved.

Plans bind the complete canonical Markdown snapshot, including descriptors/indexes/queue, to detect concurrent changes. The existing global process lock serializes cooperating clients. Journals preserve intent, expected hashes and original bytes before writes. Failed writes roll back; new files move to recoverable trash. Empty directories can remain and be reused safely. A hard interruption blocks memory operations until local recovery. Recovery preserves unrelated newer edits and requests local conflict review instead of overwriting them.

Generic raw file readers/writers do not participate in the multi-note lock and may observe intermediate files. Use memory tools for coordinated changes. Application policy is not an OS boundary against same-user software; no independent security audit is claimed.

Complete backups and Git checkpoints remain necessary. Full rollback: OFF/Exit, preserve newer work, verify/extract the independent baseline to a disposable location, restore only intended affected files/shortcuts, then restart and enter the existing key privately if Exit cleared it. Do not overwrite historical backups or unrelated Projects changes. Journals may contain private text and must not be published.

## Local use and Obsidian

```bat
service\.venv\Scripts\python.exe service/second_brain.py projects
service\.venv\Scripts\python.exe service/second_brain.py inspect
service\.venv\Scripts\python.exe service/second_brain.py search "query" --project-id PROJECT_ID
service\.venv\Scripts\python.exe service/second_brain.py plan-migrate
service\.venv\Scripts\python.exe service/second_brain.py recover
```

Other CLI commands: plan-project, plan-archive (private JSON with explicit project_id), plan-supersede, plan-rebuild, identify (accessible text file), inbox, reject and exact digest commit. Config/runtime/root/prefix overrides precede the subcommand for isolated use. Keep private inputs outside source control.

Open the canonical folder as an Obsidian vault when installed. Relative wiki links, project/global indexes and legacy redirects keep navigation portable. No plugin, sync service or hidden settings are required. Actual app navigation is a separate acceptance check. The GUI builder uses ProjectBrain to include migrated collections; an old rendered snapshot remains historical.

## Verification

Run test_second_brain.py, test_project_memory.py, test_memory_protocol.py and original file/tray checks only in isolated configured roots. Project tests cover A/B/shared routing, supervised queue/rejection, identification limitations, scoped/cross/shared retrieval, supersession/history, exact plans, index repair, stale descriptors, interruptions, rollback and actual private-baseline migration when available. Public CI uses synthetic fixtures; private-baseline tests explicitly skip when unavailable.

The protocol test advertises 27 tools and invokes all 13 memory endpoints through initialization, project creation, identification, queue/resolve/reject, archive/commit/search, supersession, inspection and rebuild. A fresh second MCP process retrieves persisted project memory. It uses no real key/tunnel. Actual ChatGPT discovery/triggers require live checks; unit tests do not establish universal model autonomy.

Official references: [MCP instructions/tool metadata and testing](https://developers.openai.com/plugins/build/mcp-server), [skills and model-selected activation](https://developers.openai.com/plugins/concepts/skills).
