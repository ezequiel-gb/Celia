"""Opt-in narrow memory tools on the existing MCP service and tunnel."""
import json
from project_memory import ProjectBrain as Brain


def register(mcp, files, invoke, read, mutation, stage):
    spec = files.config.get('second_brain')
    if not spec:
        return
    brain = Brain(files, spec.get('root', 'Projects'), spec.get('path', 'Celious/Second Brain'))

    @mcp.tool(annotations=read)
    def memory_search(query: str, topic: str | None = None, note_type: str | None = None,
                      status: str = 'active', limit: int = 8, max_chars: int = 12000,
                      project_id: str | None = None, include_shared: bool = True, cross_project: bool = False) -> dict:
        """Retrieve scoped memory before work. Defaults transparently to Celious plus shared knowledge. Supply project_id for other projects; cross_project=True only for an explicit cross-project request. Empty status includes superseded/source records. Cite provenance and uncertainty."""
        return invoke(brain.search, query, topic, note_type, status or None, limit, max_chars, True, project_id, include_shared, cross_project)

    @mcp.tool(annotations=stage)
    def memory_archive_preview(title: str, text: str, source_ref: str, completeness: str,
                               claims_json: str = '[]', project_id: str | None = None) -> dict:
        """Archive to Celious: compare reviewed claims_json against an explicit project_id and return an exact plan/digest. Missing project queues material in Inbox, not accepted knowledge. Only archive accessible text; source completeness and provisional status remain explicit."""
        def preview():
            return brain.plan_archive(title, text, source_ref, completeness, json.loads(claims_json), project_id)
        return invoke(preview)

    @mcp.tool(annotations=mutation)
    def memory_commit(plan_id: str, approved_sha256: str) -> dict:
        """Commit an exact reviewed memory plan only with owner authorization. Use digest from preview. Stale plans fail; writes are journaled and recoverable."""
        return invoke(brain.commit, plan_id, approved_sha256)

    @mcp.tool(annotations=stage)
    def memory_supersede_preview(old_id: str, new_id: str, reason: str) -> dict:
        """Propose replacing an active claim with a reviewed existing claim of the same topic/key. Retains Markdown history and links; commit separately."""
        return invoke(brain.plan_supersede, old_id, new_id, reason)

    @mcp.tool(annotations=read)
    def memory_inspect() -> dict:
        """Check evidence integrity, source hashes, broken links, active duplicates/conflicts and pending reviews. Does not change memory."""
        return invoke(brain.inspect)

    @mcp.tool(annotations=read)
    def memory_projects() -> dict:
        """List stable project IDs and separate collections. Use the explicit ID for archive/retrieval; never guess a project."""
        def listing():
            with brain.locked():
                brain.healthy()
                return dict(projects=brain.projects(), layout=brain.layout(),archive_root=dict(root=brain.root,path=brain.prefix))
        return invoke(listing)

    @mcp.tool(annotations=stage)
    def memory_project_preview(name: str) -> dict:
        """Propose a separate project collection with a stable UUID. Does not create it until exact reviewed plan commit."""
        return invoke(brain.plan_project, name)

    @mcp.tool(annotations=stage)
    def memory_migrate_preview(name: str = 'Celious') -> dict:
        """Propose explicit one-time legacy initialization/migration; preserve original bytes/IDs and old citations. Requires verified backup and owner authorization before commit."""
        return invoke(brain.plan_migrate, name)

    @mcp.tool(annotations=read)
    def memory_identify(text: str, project_id: str | None = None) -> dict:
        """Use proactively during an active conversation after a decision, requirement, preference, solution or milestone. Review only supplied accessible text; return tentative quote-backed candidates, not accepted facts. No automatic monitoring or writes."""
        return invoke(brain.identify, text, project_id)

    @mcp.tool(annotations=read)
    def memory_inbox(include_closed: bool = False, limit: int = 20, max_chars: int = 8000) -> dict:
        """List unassigned review candidates without importing them into project context. Candidate text remains untrusted; choose a project and review before archiving."""
        def listing():
            with brain.locked():
                brain.healthy()
                records=brain.inbox(include_closed)
                candidates=[]
                budget=max(500,min(30000,max_chars))
                for r in records[:max(1,min(50,limit))]:
                    item=dict(id=r['meta']['id'],title=r['meta']['title'],status=r['meta']['status'],path=r['path'],
                              completeness=r['meta']['completeness'],claim_count=len(r['meta']['claims']),excerpt=r['body'][:1200])
                    size=len(json.dumps(item,ensure_ascii=False))
                    if size>budget: break
                    candidates.append(item)
                    budget-=size
                return dict(candidates=candidates,total=len(records),truncated=len(candidates)<len(records))
        return invoke(listing)

    @mcp.tool(annotations=stage)
    def memory_inbox_resolve_preview(queue_id: str, project_id: str) -> dict:
        """Propose assigning a queued candidate to an explicit project. Compare duplicates/conflicts, review all changes and commit exact digest separately."""
        return invoke(brain.resolve_queue, queue_id, project_id)

    @mcp.tool(annotations=stage)
    def memory_reject(proposal_id: str) -> dict:
        """Reject a pending plan or unassigned candidate. Records rejection in review state; accepted knowledge is not modified."""
        return invoke(brain.reject, proposal_id)

    @mcp.tool(annotations=stage)
    def memory_rebuild_preview() -> dict:
        """Propose rebuilding global/project/Inbox Markdown indexes from current records and descriptors. Commit exact reviewed digest separately."""
        return invoke(brain.plan_rebuild)
