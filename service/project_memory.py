"""Project-scoped v0.4 memory on the existing file policy and coordinator.

No background observer, network requests or model inference. Migration is explicit.
"""
from contextlib import contextmanager
from pathlib import Path
import collections
import json
import math
import os
import re
import threading
import uuid
from second_brain import Brain as LegacyBrain, MAX_TEXT, MAX_NOTES, TYPES, digest, now, normalized, parse, render


class ProjectBrain(LegacyBrain):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local = threading.local()
        self.flat_projects = bool(self.files.config.get('second_brain', {}).get('flat_projects', False))

    def project_container(self):
        layout = self.layout()
        return layout.get('project_container', 'Projects') if layout else ('' if self.flat_projects else 'Projects')

    def project_path(self, name):
        container = self.project_container()
        return (container+'/' if container else '')+name

    @contextmanager
    def locked(self):
        if getattr(self.local, 'depth', 0):
            self.local.depth += 1
            try:
                yield
            finally:
                self.local.depth -= 1
        else:
            with super().locked():
                self.local.depth = 1
                try:
                    yield
                finally:
                    self.local.depth = 0

    def read_note(self, relative):
        node = self.path(relative)
        if node.stat().st_size > MAX_TEXT:
            raise ValueError('Note exceeds 1 MB')
        return parse(node.read_bytes().decode('utf-8'))

    def layout(self):
        if not self.path('LAYOUT.md').exists():
            return None
        meta, _ = self.read_note('LAYOUT.md')
        if meta.get('version') != 4:
            raise ValueError('Unsupported memory layout')
        return meta

    def projects(self):
        if not self.layout():
            return []
        paths = ['Shared Knowledge']
        container = self.project_container()
        base = self.path(container)
        if base.exists():
            for node in sorted(base.iterdir()):
                if not container and (node.name in {'Shared Knowledge','Inbox','Sources','Knowledge','History','Projects'} or node.name.startswith('.')):
                    continue
                self.path(self.project_path(node.name))
                if node.is_dir():
                    paths.append(self.project_path(node.name))
        result = []
        for relative in paths:
            if not self.path(relative + '/PROJECT.md').exists():
                if self.path(relative).exists() and any(x.is_file() for x in self.path(relative).rglob('*')):
                    raise ValueError('Unregistered project folder; review before using it')
                continue  # Empty folders can remain after a failed transaction.
            meta, _ = self.read_note(relative + '/PROJECT.md')
            if not re.fullmatch('project-[a-f0-9]{32}', meta.get('id', '')) or meta.get('kind') not in {'project', 'shared'}:
                raise ValueError('Invalid project descriptor')
            result.append(dict(meta, path=relative))
        if len({p['id'] for p in result}) != len(result):
            raise ValueError('Duplicate project identities')
        return result

    def project(self, ident=None):
        layout = self.layout()
        if not layout:
            raise ValueError('Review and commit explicit initialization/migration first')
        ident = ident or layout['default_project_id']
        for p in self.projects():
            if p['id'] == ident:
                return p
        raise ValueError('Unknown project identity; use memory_projects')

    def markdown_paths(self):
        base = self.path('')
        if not base.exists():
            return []
        paths = []
        for folder, dirs, names in os.walk(base, followlinks=False):
            for name in list(dirs):
                if name.startswith('.'):
                    dirs.remove(name)  # Obsidian UI settings are not memory records.
                else:
                    self.path((Path(folder)/name).relative_to(base).as_posix())
            for name in names:
                if name.endswith('.md') and not name.startswith('.'):
                    relative = (Path(folder)/name).relative_to(base).as_posix()
                    self.path(relative)
                    paths.append(relative)
                    if len(paths) > MAX_NOTES:
                        raise ValueError('Memory inventory limit reached')
        return sorted(paths)

    def snapshot(self):
        return {p: digest(self.path(p).read_bytes()) for p in self.markdown_paths()}

    def records(self):
        if not self.layout():
            return super().records()
        result = []
        for project in self.projects():
            for collection in ['Sources', 'Knowledge']:
                base = self.path(project['path'] + '/' + collection)
                if not base.exists():
                    continue
                for folder, dirs, names in os.walk(base, followlinks=False):
                    for name in dirs:
                        self.path((Path(folder)/name).relative_to(self.path('')).as_posix())
                    for name in sorted(names):
                        relative = (Path(folder)/name).relative_to(self.path('')).as_posix()
                        self.path(relative)
                        if not name.endswith('.md'):
                            continue
                        meta, body = self.read_note(relative)
                        if meta.get('type') == 'redirect':
                            raise ValueError('Redirect found inside a knowledge collection')
                        if meta.get('project_id', project['id']) != project['id']:
                            raise ValueError('Record project identity conflicts with its collection')
                        result.append(dict(path=relative, meta=meta, body=body,
                                           project_id=project['id'], project_name=project['name'], project_kind=project['kind']))
                        if len(result) > MAX_NOTES:
                            raise ValueError('Memory record limit reached')
        if len({r['meta']['id'] for r in result}) != len(result):
            raise ValueError('Duplicate note identities')
        return sorted(result, key=lambda r: r['meta']['id'])

    def project_catalog(self, p, records):
        return '# ' + p['name'] + '\n\nProject ID: `' + p['id'] + '`\n\n' + super().catalog(records)

    def global_catalog(self, projects):
        lines = ['# Celious Second Brain', '', 'Read WORKFLOW.md. Select a project before archiving or retrieving context.', '']
        for p in sorted(projects, key=lambda x: (x['kind'], x['name'].casefold())):
            lines.append('- [[' + p['path'] + '/INDEX|' + p['name'].replace('|', ' ') + ']] — ' + p['kind'] + '; id=' + p['id'])
        lines.append('\n[[Inbox/INDEX|Project-assignment review queue]]\n')
        return '\n'.join(lines)

    def index_changes(self, records, projects=None):
        projects = projects if projects is not None else self.projects()
        return [self.change(p['path']+'/INDEX.md', self.project_catalog(p, [r for r in records if r.get('project_id') == p['id']])) for p in projects] + [self.change('INDEX.md', self.global_catalog(projects))]

    def make_plan(self, changes, warnings, summary, kind='archive', **extra):
        if len({c['path'] for c in changes}) != len(changes):
            raise ValueError('Plan contains duplicate targets')
        if any(len(c['text'].encode('utf-8')) > MAX_TEXT for c in changes):
            raise ValueError('Rendered note/queue/index exceeds the 1 MB readable limit')
        ident = uuid.uuid4().hex
        plan = dict(id=ident, schema_version=4, status='proposed', kind=kind, created=now(),
                    summary=summary, warnings=warnings, changes=changes, snapshot=self.snapshot(), **extra)
        self.save_state(self.state/('plan-'+ident+'.json'), plan)
        return dict(plan_id=ident, plan_sha256=digest(json.dumps(plan, sort_keys=True).encode()),
                    summary=summary, warnings=warnings, status='proposed', saved_to_memory=False,
                    changes=[dict(path=c['path'], expected=c['expected'], text=c['text']) for c in changes], **extra)

    def load_plan(self, ident):
        plan = super().load_plan(ident)
        if plan.get('schema_version') != 4:
            raise ValueError('Old-layout proposal cannot be replayed; prepare a new preview')
        if plan.get('status') != 'proposed':
            raise ValueError('Proposal is not pending')
        return plan

    def commit(self, ident, approved_sha256):
        with self.locked():
            self.healthy()
            plan = self.load_plan(ident)
            if digest(json.dumps(plan, sort_keys=True).encode()) != approved_sha256:
                raise ValueError('Approve the exact reviewed plan digest')
            path = self.state/('journal-'+ident+'.json')
            if path.exists() or self.snapshot() != plan['snapshot']:
                raise ValueError('Used or stale plan; prepare a fresh preview')
            for c in plan['changes']:
                if self.files.fingerprint(self.path(c['path'], write=True)) != c['expected']:
                    raise ValueError('Target changed since review')
            for relative in plan.get('new_collections', []):
                if self.path(relative).exists() and any(p.is_file() for p in self.path(relative).rglob('*')):
                    raise ValueError('New project destination gained files after preview')
            journal = dict(status='prepared', plan=plan, touched=[])
            self.save_state(path, journal)
            try:
                for relative in plan.get('directories', []):
                    self.files.mkdir(self.root, self.prefix+'/'+relative)
                for index, c in enumerate(plan['changes']):
                    journal.update(status='applying')
                    journal['touched'].append(c['path'])
                    self.save_state(path, journal)
                    parent = str(Path(c['path']).parent).replace('\\', '/')
                    self.files.mkdir(self.root, self.prefix + ('/'+parent if parent != '.' else ''))
                    self.files.write(self.root, self.prefix+'/'+c['path'], c['text'], expected_sha256=c['expected'] or '')
                    if self._failure_after == index+1:
                        raise OSError('Simulated interrupted transaction')
                journal['status'] = 'committed'
                self.save_state(path, journal)
            except Exception:
                self.rollback(path, journal)
                raise
            return dict(status='committed', plan_id=ident, kind=plan['kind'], paths=[c['path'] for c in plan['changes']])

    def descriptor(self, name, kind, path):
        p = dict(id='project-'+uuid.uuid4().hex, name=name, kind=kind, created=now(), updated=now(), path=path)
        return p, self.change(path+'/PROJECT.md', render({k:v for k,v in p.items() if k != 'path'}, '# '+name+'\n'))

    def validate_name(self, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or '/' in name or '\\' in name:
            raise ValueError('Use a nonempty project folder name below 81 characters')
        if not self.project_container() and name.casefold() in {'shared knowledge','inbox','sources','knowledge','history','projects'}:
            raise ValueError('Reserved archive folder name')
        self.path(self.project_path(name), write=True)
        if self.path(self.project_path(name)).exists() and any(p.is_file() for p in self.path(self.project_path(name)).rglob('*')):
            raise ValueError('Project folder already exists')

    def plan_project(self, name):
        with self.locked():
            self.healthy()
            self.project()
            self.validate_name(name)
            p, descriptor = self.descriptor(name, 'project', self.project_path(name))
            changes = [descriptor] + self.index_changes(self.records(), self.projects()+[p])
            return self.make_plan(changes, [], 'Create separate project memory: '+name, 'project', project_id=p['id'],
                                  directories=[p['path']+'/'+x for x in ['Sources','Knowledge','History']], new_collections=[p['path']])

    def inbox(self, include_closed=False):
        result = []
        base = self.path('Inbox')
        if base.exists():
            for node in sorted(base.glob('candidate-*.md')):
                relative = node.relative_to(self.path('')).as_posix()
                meta, body = self.read_note(relative)
                if include_closed or meta['status'] == 'awaiting_project':
                    result.append(dict(path=relative, meta=meta, body=body))
        return result

    def inbox_catalog(self, records):
        return '# Assignment review queue\n\n' + ''.join('- [['+r['path'][:-3]+'|'+r['meta']['title'].replace('|', ' ')+']] — '+r['meta']['status']+'\n' for r in sorted(records,key=lambda x:x['path']))

    def plan_migrate(self, name='Celious'):
        with self.locked():
            self.healthy()
            if self.layout():
                raise ValueError('Already initialized; migration is explicit and one-time')
            self.validate_name(name)
            if self.path('Shared Knowledge').exists() and any(p.is_file() for p in self.path('Shared Knowledge').rglob('*')):
                raise ValueError('Shared Knowledge destination is not empty')
            old = super().records()
            issues = super().inspect()['issues']
            if any(x['kind'] != 'pending_review' for x in issues):
                raise ValueError('Resolve legacy integrity issues before migration')
            p, pc = self.descriptor(name, 'project', self.project_path(name))
            shared, sc = self.descriptor('Shared Knowledge', 'shared', 'Shared Knowledge')
            changes, migrated = [pc, sc], []
            mapping = []
            for relative in self.markdown_paths():
                if relative.split('/')[0] not in {'Sources', 'Knowledge', 'History'}:
                    continue
                original = self.path(relative).read_bytes()
                target = p['path']+'/'+relative
                if self.path(target).exists():
                    raise ValueError('Migration destination collision')
                changes.append(self.change(target, original.decode('utf-8')))
                redirect = render(dict(id='redirect-'+uuid.uuid4().hex, type='redirect', status='redirect', target=target),
                                  '# Moved record\n\n[['+target[:-3]+'|Open the preserved record]]\n')
                changes.append(self.change(relative, redirect))
                mapping.append(dict(old=relative, new=target, sha256=digest(original)))
            for r in old:
                migrated.append(dict(r, path=p['path']+'/'+r['path'], project_id=p['id'], project_name=p['name'], project_kind='project'))
            changes += self.index_changes(migrated, [p, shared])
            changes.append(self.change('Inbox/INDEX.md', self.inbox_catalog([])))
            if not self.path('WORKFLOW.md').exists():
                changes.append(self.change('WORKFLOW.md', '# Second Brain workflow\n\n'
                    'Select a stable project ID with memory_projects. Retrieve scoped memory before work; '
                    'cross-project retrieval must be explicit. Cite source evidence, status and uncertainty.\n\n'
                    'Use memory_identify on accessible text for tentative read-only candidates. Review '
                    'project routing, exact quotes and completeness before memory_archive_preview. '
                    'Missing routing enters Inbox, not accepted knowledge. Review all changes and '
                    'commit only the exact digest with owner authorization. Never silently archive.\n\n'
                    'Inspect after commits. Review supersession separately; History preserves prior '
                    'versions. Read the installed PROJECT-MEMORY.md for limits and recovery. '
                    'There is no continuous chat monitor or guaranteed automatic tool invocation.\n'))
            # Activate the new layout last. Recovery blocks readers during partial writes.
            changes.append(self.change('LAYOUT.md', render(dict(version=4, default_project_id=p['id'], shared_project_id=shared['id'],project_container=self.project_container()),
                                                          '# Project-based memory layout\n')))
            return self.make_plan(changes, [], 'Preserve records byte-for-byte in project memory with legacy navigation redirects',
                                  'migration', migration=mapping, default_project_id=p['id'],
                                  directories=[x['path']+'/'+c for x in [p,shared] for c in ['Sources','Knowledge','History']],
                                  new_collections=[p['path'],shared['path']])

    def validate_archive(self, title, text, source_ref, completeness, claims):
        if not isinstance(text, str) or not text.strip() or len(text.encode()) > MAX_TEXT:
            raise ValueError('Supply accessible source text below 1 MB')
        if re.search(r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}', text):
            raise ValueError('Possible credential in source; redact locally before archival')
        if not title.strip() or len(title) > 200 or not source_ref.strip() or completeness not in {'partial', 'excerpt', 'user_supplied', 'complete_export'}:
            raise ValueError('Valid title, source reference and completeness required')
        if not isinstance(claims, list) or len(claims) > 100:
            raise ValueError('At most 100 reviewed claims')
        required = {'type', 'title', 'topic', 'key', 'value', 'evidence', 'epistemic', 'uncertainty'}
        for c in claims:
            if not isinstance(c, dict) or not required <= c.keys() or any(not isinstance(c[k], str) or not c[k].strip() or len(c[k]) > 4000 for k in required):
                raise ValueError('Invalid claim structure')
            if c['type'] not in TYPES or c['epistemic'] not in {'asserted', 'observed', 'interpreted', 'accepted', 'pending'} or c['evidence'] not in text:
                raise ValueError('Invalid type, epistemic status or exact evidence')
            if not isinstance(c.get('links', []), list) or any(not isinstance(i, str) for i in c.get('links', [])):
                raise ValueError('Links must be stable identity strings')

    def plan_archive(self, title, text, source_ref, completeness, claims, project_id=None):
        with self.locked():
            self.healthy()
            self.project()  # Do not silently initialize a legacy collection.
            self.validate_archive(title, text, source_ref, completeness, claims)
            if not project_id:
                ident = 'candidate-'+uuid.uuid4().hex
                meta = dict(id=ident, type='candidate', title=title, created=now(), status='awaiting_project',
                            source_ref=source_ref, completeness=completeness, claims=claims, content_sha256=digest(text.encode()))
                queued = dict(path='Inbox/'+ident+'.md', meta=meta, body=text)
                plan = self.make_plan([self.change(queued['path'], render(meta, text)),
                                       self.change('Inbox/INDEX.md', self.inbox_catalog(self.inbox(True)+[queued]))],
                                      [], 'Queue uncertain project assignment; no accepted knowledge changes', 'queue')
                self.commit(plan['plan_id'], plan['plan_sha256'])
                return dict(status='awaiting_project', queue_id=ident, path=queued['path'], saved_to_memory=False,
                            queued_for_review=True, confirmation_required=True)
            p = self.project(project_id)
            records = self.records()
            target = [r for r in records if r['project_id'] == p['id']]
            if any(r['meta'].get('content_sha256') == digest(text.encode()) for r in target):
                raise ValueError('Source already archived in this project')
            sid = 'src-'+uuid.uuid4().hex
            source_path = p['path']+'/Sources/'+sid+'.md'
            meta = dict(id=sid, type='source', title=title, project_id=p['id'], created=now(), updated=now(),
                        status='archived', source_ref=source_ref, completeness=completeness,
                        content_sha256=digest(text.encode()), uncertainty='Caller-supplied completeness; no inaccessible history retrieved.', links=[])
            added = [dict(path=source_path, meta=meta, body=text, project_id=p['id'], project_name=p['name'], project_kind=p['kind'])]
            changes, warnings = [self.change(source_path, render(meta, text))], []
            active = [r for r in target if r['meta']['type'] != 'source' and r['meta']['status'] == 'active']
            for c in claims:
                pairs = [r for r in active if all(normalized(r['meta'][k]) == normalized(c[k]) for k in ['topic', 'key'])]
                duplicate = [r for r in pairs if normalized(r['meta']['value']) == normalized(c['value'])]
                conflict = [r for r in pairs if normalized(r['meta']['value']) != normalized(c['value'])]
                if duplicate:
                    warnings.append(dict(kind='duplicate', existing=[r['meta']['id'] for r in duplicate], action='claim skipped; source retained'))
                    continue
                if conflict:
                    warnings.append(dict(kind='conflict', existing=[r['meta']['id'] for r in conflict], action='new claim pending review'))
                related = c.get('links', [])
                by_id = {r['meta']['id']:r for r in records+added}
                if any(i not in by_id for i in related):
                    raise ValueError('Unknown related identity')
                ident = 'note-'+uuid.uuid4().hex
                offset = text.find(c['evidence'])
                provisional = c['epistemic']=='pending' or (c['type'] in {'decision','fact','interpretation'} and
                    bool(re.search(r'\b(maybe|might|hypothes[ei]s|provisional|not decided|not a decision|could|consider|suggest)\b',c['evidence'],re.I)))
                if provisional and c['epistemic']!='pending':
                    warnings.append(dict(kind='provisional',action='Evidence contains uncertainty cues; claim remains pending'))
                m = dict(id=ident, type=c['type'], title=c['title'], project_id=p['id'], created=now(), updated=now(),
                         status='pending' if conflict or provisional else 'active', topic=c['topic'], key=c['key'],
                         value=c['value'], epistemic='pending' if provisional else c['epistemic'], uncertainty=c['uncertainty'], source_ids=[sid],
                         source_completeness=completeness, evidence=[dict(source_id=sid,start=offset,end=offset+len(c['evidence']),quote=c['evidence'])],
                         links=[sid]+related, supersedes=None)
                body = '# '+c['title']+'\n\n'+c['value']+'\n\n## Evidence\n\n[['+source_path[:-3]+']]\n\n'+c['evidence']+'\n'
                body += ''.join('\n[['+by_id[i]['path'][:-3]+']]\n' for i in related)
                r = dict(path=p['path']+'/Knowledge/'+ident+'.md', meta=m, body=body,
                         project_id=p['id'], project_name=p['name'], project_kind=p['kind'])
                added.append(r)
                if m['status'] == 'active':
                    active.append(r)
                changes.append(self.change(r['path'], render(m, body)))
            changes += self.index_changes(records+added)
            return self.make_plan(changes, warnings, 'Archive reviewed evidence into '+p['name'], project_id=p['id'])

    def resolve_queue(self, queue_id, project_id):
        with self.locked():
            self.healthy()
            if not re.fullmatch('candidate-[a-f0-9]{32}', queue_id):
                raise ValueError('Invalid queue identity')
            path = 'Inbox/'+queue_id+'.md'
            meta, body = self.read_note(path)
            if meta['status'] != 'awaiting_project' or digest(body.encode()) != meta['content_sha256']:
                raise ValueError('Queue closed or source changed')
            preview = self.plan_archive(meta['title'], body, meta['source_ref'], meta['completeness'], meta['claims'], project_id)
            plan = self.load_plan(preview['plan_id'])
            meta.update(status='archived', project_id=project_id, updated=now())
            queued = dict(path=path,meta=meta,body=body)
            plan['changes'] += [self.change(path,render(meta,body)), self.change('Inbox/INDEX.md',self.inbox_catalog([r for r in self.inbox(True) if r['path'] != path]+[queued]))]
            # Keep the initial preview as evidence; only the new combined digest authorizes closing the queue.
            return self.make_plan(plan['changes'], plan['warnings'], 'Resolve project assignment and archive reviewed candidate', 'resolve', project_id=project_id)

    def reject(self, ident):
        with self.locked():
            self.healthy()
            if re.fullmatch('[a-f0-9]{32}', ident):
                plan = self.load_plan(ident)
                if (self.state/('journal-'+ident+'.json')).exists():
                    raise ValueError('Cannot reject an applied proposal')
                plan.update(status='rejected', rejected_at=now())
                self.save_state(self.state/('plan-'+ident+'.json'), plan)
            elif re.fullmatch('candidate-[a-f0-9]{32}', ident):
                path='Inbox/'+ident+'.md'
                meta,body=self.read_note(path)
                if meta['status'] != 'awaiting_project':
                    raise ValueError('Candidate is already closed')
                meta.update(status='rejected',updated=now())
                queued=dict(path=path,meta=meta,body=body)
                plan=self.make_plan([self.change(path,render(meta,body)),self.change('Inbox/INDEX.md',self.inbox_catalog([r for r in self.inbox(True) if r['path'] != path]+[queued]))],[], 'Reject unassigned candidate; accepted knowledge unchanged','reject')
                self.commit(plan['plan_id'],plan['plan_sha256'])
            else:
                raise ValueError('Invalid proposal/candidate identity')
            return dict(status='rejected',id=ident,accepted_knowledge_changed=False)

    def plan_supersede(self, old_id, new_id, reason):
        with self.locked():
            self.healthy()
            records=self.records()
            lookup={r['meta']['id']:r for r in records}
            if old_id not in lookup or new_id not in lookup:
                raise ValueError('Unknown note identity')
            old,new=lookup[old_id],lookup[new_id]
            if old==new or old['project_id'] != new['project_id'] or any(r['meta']['type']=='source' for r in [old,new]):
                raise ValueError('Supersede distinct knowledge records within one project')
            if old['meta']['status'] != 'active' or new['meta']['status'] not in {'active','pending'} or new['meta']['epistemic']=='pending' or not reason.strip():
                raise ValueError('Reviewed replacement and reason required; provisional claims cannot be promoted')
            if any(normalized(old['meta'][k]) != normalized(new['meta'][k]) for k in ['topic','key']):
                raise ValueError('Replacement must address the same topic/key')
            if any(r['project_id']==old['project_id'] and r['meta']['id'] not in {old_id,new_id} and r['meta']['status']=='active' and r['meta']['type']!='source' and all(normalized(r['meta'][k])==normalized(new['meta'][k]) for k in ['topic','key']) for r in records):
                raise ValueError('Resolve additional active conflicts')
            p=self.project(old['project_id'])
            changes=[self.change(p['path']+'/History/'+r['meta']['id']+'/'+uuid.uuid4().hex+'.md',self.path(r['path']).read_bytes().decode('utf-8')) for r in [old,new]]
            old['meta'].update(status='superseded',updated=now(),superseded_by=new_id,change_reason=reason)
            new['meta'].update(status='active',updated=now(),supersedes=old_id,change_reason=reason)
            for record,other in [(old,new),(new,old)]:
                record['meta']['links']=sorted(set(record['meta']['links']+[other['meta']['id']]))
                record['body']+='\nRelated decision: [['+other['path'][:-3]+']].\n'
                changes.append(self.change(record['path'],render(record['meta'],record['body'])))
            changes+=self.index_changes(records)
            return self.make_plan(changes,[], 'Supersede reviewed decision and retain project history','supersede')

    def search(self, query, topic=None, note_type=None, status='active', limit=8, max_chars=12000, linked=True,
               project_id=None, include_shared=True, cross_project=False):
        with self.locked():
            self.healthy()
            p=self.project(project_id)
            if not isinstance(query,str) or len(query)>500:
                raise ValueError('Query exceeds 500 characters')
            limit,max_chars=max(1,min(20,limit)),max(500,min(30000,max_chars))
            projects=self.projects()
            allowed={x['id'] for x in projects} if cross_project else {p['id']} | ({x['id'] for x in projects if x['kind']=='shared'} if include_shared else set())
            scoped=[r for r in self.records() if r['project_id'] in allowed]
            by_id={r['meta']['id']:r for r in scoped}
            terms=set(re.findall(r'\w+',query.casefold()))
            candidates=[]
            freq=collections.Counter()
            for r in scoped:
                m=r['meta']
                if (status and m['status']!=status) or (topic and normalized(m.get('topic',''))!=normalized(topic)) or (note_type and m['type']!=note_type):
                    continue
                content=' '.join(str(m.get(k,'')) for k in ['title','topic','key','value'])+'\n'+r['body']
                tokens=collections.Counter(re.findall(r'\w+',content.casefold()))
                if terms and not terms & tokens.keys():
                    continue
                freq.update(terms & tokens.keys())
                candidates.append((r,content,tokens))
            ranked=[]
            for r,content,tokens in candidates:
                score=sum(math.log(1+(len(candidates)+1)/(freq[t]+1))*min(tokens[t],4) for t in terms)+3*len(terms & set(re.findall(r'\w+',r['meta']['title'].casefold())))
                ranked.append((0 if r['project_id']==p['id'] else 1, -score, r['meta']['id'],r,content))
            ranked.sort(key=lambda x:x[:3])
            hits,budget=[],max_chars
            for _,negscore,_,r,content in ranked[:limit]:
                m=r['meta']
                positions=[content.casefold().find(t) for t in terms if t in content.casefold()]
                start=max(0,min(positions)-120) if positions else 0
                evidence=m.get('evidence',[])
                valid=all(e['source_id'] in by_id and by_id[e['source_id']]['body'][e['start']:e['end']]==e['quote'] and digest(by_id[e['source_id']]['body'].encode())==by_id[e['source_id']]['meta'].get('content_sha256') for e in evidence)
                if m['type']=='source': valid=digest(r['body'].encode())==m['content_sha256']
                hit=dict(id=m['id'],path=self.prefix+'/'+r['path'],title=m['title'],status=m['status'],project_id=r['project_id'],project_name=r['project_name'],
                         scope='shared' if r['project_kind']=='shared' else 'project',score=round(-negscore,3),excerpt=content[start:start+min(1500,budget)],
                         epistemic=m.get('epistemic'),uncertainty=m.get('uncertainty'),evidence=evidence,provenance_valid=valid,
                         sources=[dict(id=i,path=self.prefix+'/'+by_id[i]['path'],completeness=by_id[i]['meta'].get('completeness')) for i in m.get('source_ids',[]) if i in by_id])
                if linked: hit['related']=[dict(id=i,path=self.prefix+'/'+by_id[i]['path'],title=by_id[i]['meta']['title']) for i in m.get('links',[]) if i in by_id][:10]
                size=len(json.dumps(hit,ensure_ascii=False))
                if size>budget: break
                hits.append(hit)
                budget-=size
            return dict(query=query,project_id=p['id'],project_name=p['name'],cross_project=cross_project,include_shared=include_shared,
                        hits=hits,total_matches=len(ranked),truncated=len(hits)<len(ranked),untrusted_content=True,search='project-scoped weighted lexical search')

    def inspect(self):
        with self.locked():
            self.healthy()
            if not self.layout():
                return dict(super().inspect(), layout='legacy', projects=0)
            records=self.records()
            by_id={r['meta']['id']:r for r in records}
            issues=[]
            pairs=collections.defaultdict(list)
            for r in records:
                m=r['meta']
                for i in m.get('links',[]):
                    if i not in by_id: issues.append(dict(kind='broken_link',id=m['id'],target=i))
                if m['type']=='source':
                    if digest(r['body'].encode())!=m['content_sha256']: issues.append(dict(kind='source_modified',id=m['id']))
                else:
                    for e in m.get('evidence',[]):
                        source=by_id.get(e['source_id'])
                        if not source or source['body'][e['start']:e['end']]!=e['quote']: issues.append(dict(kind='invalid_evidence',id=m['id']))
                    if m['status']=='active': pairs[(r['project_id'],normalized(m['topic']),normalized(m['key']))].append(m)
                    if m['status']=='pending': issues.append(dict(kind='pending_review',id=m['id']))
            for key,group in pairs.items():
                if len(group)>1: issues.append(dict(kind='duplicate' if len({normalized(m['value']) for m in group})==1 else 'conflict',project_id=key[0],ids=[m['id'] for m in group]))
            expected={p['path']+'/INDEX.md':self.project_catalog(p,[r for r in records if r['project_id']==p['id']]) for p in self.projects()}
            expected['INDEX.md']=self.global_catalog(self.projects())
            expected['Inbox/INDEX.md']=self.inbox_catalog(self.inbox(True))
            for path,text in expected.items():
                if not self.path(path).exists() or self.path(path).read_bytes()!=text.encode(): issues.append(dict(kind='index_outdated',path=path))
            for relative in self.markdown_paths():
                if relative.endswith(('INDEX.md','WORKFLOW.md')) or relative=='LAYOUT.md': continue
                meta,body=self.read_note(relative)
                if meta.get('type')=='candidate' and digest(body.encode()) != meta['content_sha256']:
                    issues.append(dict(kind='candidate_source_modified',path=relative))
                if meta.get('type')=='redirect' and not self.path(meta['target']).is_file(): issues.append(dict(kind='broken_redirect',path=relative))
                if meta.get('type') in {'source','candidate'}: continue  # Original evidence may contain quoted/illustrative wiki syntax.
                for target in re.findall(r'\[\[([^]|]+)(?:\|[^]]*)?\]\]',body):
                    if not self.path(target+'.md').is_file(): issues.append(dict(kind='broken_wiki_link',path=relative,target=target))
            return dict(notes=len(records),projects=len(self.projects()),issues=issues,pending_transactions=len(self.pending()),pending_assignments=len(self.inbox()),layout='project-v4')

    def plan_rebuild(self):
        with self.locked():
            self.healthy()
            changes=self.index_changes(self.records())+[self.change('Inbox/INDEX.md',self.inbox_catalog(self.inbox(True)))]
            return self.make_plan(changes,[], 'Rebuild portable project and review indexes','rebuild')

    def identify(self, text, project_id=None):
        with self.locked():
            self.healthy()
            return self._identify(text, project_id)

    def _identify(self, text, project_id=None):
        if not isinstance(text,str) or len(text.encode())>MAX_TEXT:
            raise ValueError('Supply accessible text below 1 MB')
        if re.search(r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',text):
            raise ValueError('Possible credential; redact locally before review')
        project=self.project(project_id) if project_id else None
        cues=[('decision',r'\b(decided|decision|we will|choose|chosen)\b'),('requirement',r'\b(must|requirement|required)\b'),
              ('preference',r'\b(prefer|preference)\b'),('lesson',r'\b(lesson|learned)\b'),('fact',r'\b(fixed|resolved|solution|milestone|verified)\b'),
              ('question',r'\b(todo|outstanding|unresolved|question)\b|\?')]
        candidates=[]
        speaker='unknown'
        for match in re.finditer(r'[^\r\n]+',text):
            line=match.group()
            role=re.match(r'\s*(User|Assistant)\s*:',line,re.I)
            if role: speaker=role.group(1).lower()
            for kind,pattern in cues:
                cue=re.search(pattern,line,re.I)
                if cue:
                    provisional=bool(re.search(r'\b(maybe|might|hypothes[ei]s|suggest|provisional|not decided|not a decision|could|consider)\b',line,re.I)) or speaker!='user'
                    excerpt_start=max(0,cue.start()-200)
                    quote=line[excerpt_start:excerpt_start+1200].strip()
                    start=match.start()+line.find(quote,excerpt_start)
                    candidates.append(dict(type=kind,quote=quote,start=start,end=start+len(quote),speaker=speaker,
                                           provisional=provisional,epistemic='pending',reason='Local cue match; human/model review still required'))
                    break
            if len(candidates)>=50: break
        return dict(project_id=project['id'] if project else None,assignment_required=project is None,candidates=candidates,
                    saved_to_memory=False,confirmation_required=True,trigger='supplied text in an explicit MCP call; no continuous monitoring')
