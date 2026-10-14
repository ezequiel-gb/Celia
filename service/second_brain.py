"""Portable Markdown memory using Celious policy, no network or model calls.

Extraction is supplied by the reasoning client and checked against source quotes.
Plans live in private runtime storage; only approved commits change notes.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import argparse
import base64
import collections
import hashlib
import json
import math
import os
import re
import uuid
from engine import Files

TYPES = {'fact', 'decision', 'requirement', 'preference', 'lesson', 'question', 'interpretation'}
MAX_TEXT = 1024 * 1024
MAX_NOTES = 5000


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render(meta, body):
    # JSON values form a deliberately small, valid YAML subset; no YAML dependency.
    return '---\n' + ''.join(k + ': ' + json.dumps(v, ensure_ascii=False) + '\n'
                             for k, v in meta.items()) + '---\n' + body


def parse(text):
    if not text.startswith('---\n'):
        raise ValueError('Missing frontmatter')
    header, body = text[4:].split('\n---\n', 1)
    meta = {}
    for line in header.splitlines():
        key, value = line.split(': ', 1)
        if key in meta or not re.fullmatch('[a-z][a-z_0-9]*', key):
            raise ValueError('Invalid frontmatter')
        meta[key] = json.loads(value)
    return meta, body


def normalized(value):
    return ' '.join(value.casefold().split())


class Brain:
    def __init__(self, files, root='Projects', prefix='Celious/Second Brain'):
        self.files, self.root = files, root
        self.prefix = prefix.rstrip('/')
        if not self.prefix:
            raise ValueError('Memory must be a subdirectory')
        files.path(root, self.prefix)
        self.state = files.runtime / 'second-brain' / digest((root + '/' + prefix).encode())[:16]
        self.state.mkdir(parents=True, exist_ok=True)
        self._failure_after = None  # Test injection; never exposed by MCP/CLI.

    def path(self, relative, write=False):
        path = self.prefix + '/' + relative
        return self.files.mutation_path(self.root, path) if write else self.files.path(self.root, path)

    @contextmanager
    def locked(self):
        # Serialize independent processes. Reads also wait for transactions to finish.
        with self.files.lock, (self.state / 'lock').open('a+b') as lock:
            lock.seek(0)
            # Windows permits locking beyond EOF. Never read the locked byte;
            # a competing process may already own it.
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def save_state(self, path, data):
        temporary = path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)

    def records(self):
        result = []
        count = 0
        for folder in ['Sources', 'Knowledge']:
            base = self.path(folder)
            if not base.exists():
                continue
            # Policy rejects reparse points before walking into them.
            for directory, dirs, names in os.walk(base, followlinks=False):
                for name in dirs:
                    self.path((Path(directory) / name).relative_to(self.path('')).as_posix())
                for name in sorted(names):
                    relative = (Path(directory) / name).relative_to(self.path('')).as_posix()
                    node = self.path(relative)
                    if node.suffix != '.md':
                        continue
                    count += 1
                    if count > MAX_NOTES or node.stat().st_size > MAX_TEXT:
                        raise ValueError('Memory scan limit reached; partition before continuing')
                    meta, body = parse(node.read_bytes().decode('utf-8'))
                    result.append(dict(path=relative, meta=meta, body=body))
        ids = [r['meta']['id'] for r in result]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate note identities')
        return sorted(result, key=lambda r: r['meta']['id'])

    def pending(self):
        return [p for p in self.state.glob('journal-*.json')
                if json.loads(p.read_text('utf-8'))['status'] in {'prepared', 'applying', 'recovery_required'}]

    def healthy(self):
        if self.pending():
            raise ValueError('Incomplete transaction; run recovery before reading or writing')

    def catalog(self, records):
        lines = ['# Celious Second Brain', '',
                 'Read WORKFLOW.md. Sources are evidence; Knowledge holds reviewed claims.',
                 'Search this collection with Celious Files. Read source quotes before relying on a claim.', '',
                 '## Notes', '']
        for r in sorted(records, key=lambda r: (r['meta']['type'], r['meta']['id'])):
            m = r['meta']
            lines.append('- [[' + r['path'][:-3] + '|' + m['title'].replace('|', ' ') + ']] — '
                         + m['type'] + '; ' + m['status'] + '; ' + m.get('topic', '')
                         + '; ' + m.get('key', '') + '; ' + m.get('value', '')
                         + '; id=' + m['id'])
        return '\n'.join(lines) + '\n'

    def change(self, path, text):
        node = self.path(path, write=True)
        old = node.read_bytes() if node.exists() else None
        return dict(path=path, expected=digest(old) if old is not None else None,
                    before=base64.b64encode(old).decode() if old is not None else None, text=text)

    def make_plan(self, changes, warnings, summary):
        ident = uuid.uuid4().hex
        plan = dict(id=ident, created=now(), summary=summary, warnings=warnings, changes=changes,
                    snapshot={r['path']: digest(self.path(r['path']).read_bytes()) for r in self.records()})
        self.save_state(self.state / ('plan-' + ident + '.json'), plan)
        return dict(plan_id=ident, plan_sha256=digest(json.dumps(plan, sort_keys=True).encode()),
                    summary=summary, warnings=warnings,
                    changes=[dict(path=c['path'], expected=c['expected'], text=c['text']) for c in changes],
                    status='proposed', saved_to_memory=False)

    def plan_archive(self, title, text, source_ref, completeness, claims):
        with self.locked():
            self.healthy()
            if not isinstance(text, str) or not text.strip() or len(text.encode()) > MAX_TEXT:
                raise ValueError('Provide accessible source text below 1 MB')
            if completeness not in {'complete_export', 'partial', 'excerpt', 'user_supplied'}:
                raise ValueError('Specify source completeness')
            if not title.strip() or len(title) > 200 or not source_ref.strip():
                raise ValueError('Title and source reference required')
            if not isinstance(claims, list) or len(claims) > 100:
                raise ValueError('At most 100 reviewed claims')
            records = self.records()
            source_hash = digest(text.encode())
            if any(r['meta'].get('content_sha256') == source_hash for r in records):
                raise ValueError('Source already archived')
            sid = 'src-' + uuid.uuid4().hex
            source_path = 'Sources/' + sid + '.md'
            meta = dict(id=sid, type='source', title=title, created=now(), updated=now(), status='archived',
                        source_ref=source_ref, completeness=completeness, content_sha256=source_hash,
                        uncertainty='Completeness is supplied by the caller; no hidden history is retrieved.', links=[])
            added = [dict(path=source_path, meta=meta, body=text)]
            warnings = []
            active = [r for r in records if r['meta']['type'] != 'source' and r['meta']['status'] == 'active']
            changes = [self.change(source_path, render(meta, text))]
            for claim in claims:
                required = {'type', 'title', 'topic', 'key', 'value', 'evidence', 'epistemic', 'uncertainty'}
                if not isinstance(claim, dict) or not required <= claim.keys() or any(not isinstance(claim[k], str) or not claim[k].strip() for k in required):
                    raise ValueError('Claim fields must be nonempty strings')
                if claim['type'] not in TYPES or claim['epistemic'] not in {'asserted', 'observed', 'interpreted', 'accepted', 'pending'}:
                    raise ValueError('Invalid claim type or epistemic status')
                quote = claim['evidence']
                offset = text.find(quote)
                if offset < 0:
                    raise ValueError('Evidence must be an exact source excerpt')
                if any(len(claim[k]) > 4000 for k in required):
                    raise ValueError('Claim field too long')
                pairs = [r for r in active if normalized(r['meta']['topic']) == normalized(claim['topic'])
                         and normalized(r['meta']['key']) == normalized(claim['key'])]
                duplicate = [r for r in pairs if normalized(r['meta']['value']) == normalized(claim['value'])]
                conflict = [r for r in pairs if normalized(r['meta']['value']) != normalized(claim['value'])]
                if duplicate:
                    warnings.append(dict(kind='duplicate', title=claim['title'], existing=[r['meta']['id'] for r in duplicate], action='claim skipped; source retained'))
                    continue
                if conflict:
                    warnings.append(dict(kind='conflict', title=claim['title'], existing=[r['meta']['id'] for r in conflict], action='new claim pending review'))
                ident = 'note-' + uuid.uuid4().hex
                related = claim.get('links', [])
                if not isinstance(related, list) or any(i not in {r['meta']['id'] for r in records + added} for i in related):
                    raise ValueError('Links must reference existing stable identities')
                m = dict(id=ident, type=claim['type'], title=claim['title'], created=now(), updated=now(),
                         status='pending' if conflict or claim['epistemic'] == 'pending' else 'active',
                         topic=claim['topic'], key=claim['key'], value=claim['value'], epistemic=claim['epistemic'],
                         uncertainty=claim['uncertainty'], source_ids=[sid], source_completeness=completeness,
                         evidence=[dict(source_id=sid, start=offset, end=offset+len(quote), quote=quote)],
                         links=[sid] + related, supersedes=None)
                body = '# ' + claim['title'] + '\n\n' + claim['value'] + '\n\n## Evidence\n\n'
                body += '[[' + source_path[:-3] + '|' + title.replace('|', ' ') + ']]\n\n' + quote + '\n'
                for linked in related:
                    record = next(r for r in records + added if r['meta']['id'] == linked)
                    body += '\n[[' + record['path'][:-3] + ']]\n'
                r = dict(path='Knowledge/' + ident + '.md', meta=m, body=body)
                added.append(r)
                active.append(r) if m['status'] == 'active' else None
                changes.append(self.change(r['path'], render(m, body)))
            changes.append(self.change('INDEX.md', self.catalog(records + added)))
            return self.make_plan(changes, warnings, 'Archive source and evidence-backed claims')

    def plan_supersede(self, old_id, new_id, reason):
        with self.locked():
            self.healthy()
            records = self.records()
            lookup = {r['meta']['id']: r for r in records}
            if old_id not in lookup or new_id not in lookup:
                raise ValueError('Unknown note identity')
            old, new = lookup[old_id], lookup[new_id]
            if old == new or old['meta']['type'] == 'source' or new['meta']['type'] == 'source':
                raise ValueError('Choose two different knowledge notes')
            if old['meta']['status'] != 'active' or new['meta']['status'] not in {'active', 'pending'} or not reason.strip():
                raise ValueError('Active former note and reason required')
            if any(normalized(old['meta'][k]) != normalized(new['meta'][k]) for k in ['topic', 'key']):
                raise ValueError('Supersession must address the same topic and key')
            for record in [old, new]:
                if any(r['meta']['status'] == 'active' and r['meta']['id'] not in {old_id, new_id}
                       and all(normalized(r['meta'][k]) == normalized(new['meta'][k]) for k in ['topic', 'key']) for r in records):
                    raise ValueError('Resolve additional active conflicts first')
            changes = []
            for record in [old, new]:
                changes.append(self.change('History/' + record['meta']['id'] + '/' + uuid.uuid4().hex + '.md',
                                           self.path(record['path']).read_bytes().decode('utf-8')))
            old['meta'].update(status='superseded', updated=now(), superseded_by=new_id, change_reason=reason)
            new['meta'].update(status='active', updated=now(), supersedes=old_id, change_reason=reason)
            old['meta']['links'] = sorted(set(old['meta']['links'] + [new_id]))
            new['meta']['links'] = sorted(set(new['meta']['links'] + [old_id]))
            old['body'] += '\nSuperseded by [[' + new['path'][:-3] + ']].\n'
            new['body'] += '\nSupersedes [[' + old['path'][:-3] + ']].\n'
            changes += [self.change(r['path'], render(r['meta'], r['body'])) for r in [old, new]]
            changes.append(self.change('INDEX.md', self.catalog(records)))
            return self.make_plan(changes, [], 'Supersede a decision while retaining both versions')

    def load_plan(self, ident):
        if not re.fullmatch('[a-f0-9]{32}', ident):
            raise ValueError('Invalid plan identity')
        return json.loads((self.state / ('plan-' + ident + '.json')).read_text('utf-8'))

    def commit(self, ident, approved_sha256):
        with self.locked():
            self.healthy()
            plan = self.load_plan(ident)
            if digest(json.dumps(plan, sort_keys=True).encode()) != approved_sha256:
                raise ValueError('Approve the exact reviewed plan digest')
            if (self.state / ('journal-' + ident + '.json')).exists():
                raise ValueError('Plan already used; make a new proposal')
            snapshot = {r['path']: digest(self.path(r['path']).read_bytes()) for r in self.records()}
            if snapshot != plan['snapshot']:
                raise ValueError('Memory changed since review; prepare a new plan')
            for c in plan['changes']:
                if self.files.fingerprint(self.path(c['path'], write=True)) != c['expected']:
                    raise ValueError('Target changed since review')
            journal = dict(status='prepared', plan=plan, touched=[])
            path = self.state / ('journal-' + ident + '.json')
            self.save_state(path, journal)
            try:
                for i, c in enumerate(plan['changes']):
                    # Mark intent before touching target, so hard crashes are recoverable.
                    journal['status'] = 'applying'
                    journal['touched'].append(c['path'])
                    self.save_state(path, journal)
                    self.files.mkdir(self.root, self.prefix + '/' + str(Path(c['path']).parent).replace('\\', '/') if '/' in c['path'] else self.prefix)
                    if self.files.fingerprint(self.path(c['path'])) != c['expected']:
                        raise ValueError('Target changed during transaction')
                    self.files.write(self.root, self.prefix + '/' + c['path'], c['text'], expected_sha256=c['expected'] or '')
                    if self._failure_after == i + 1:
                        raise OSError('Simulated interrupted write')
                journal['status'] = 'committed'
                self.save_state(path, journal)
            except Exception:
                self.rollback(path, journal)
                raise
            return dict(status='committed', plan_id=ident, paths=[c['path'] for c in plan['changes']])

    def rollback(self, path, journal):
        unresolved = []
        for c in reversed(journal['plan']['changes']):
            if c['path'] not in journal['touched']:
                continue
            current = self.files.fingerprint(self.path(c['path']))
            after = digest(c['text'].encode())
            if current == c['expected']:
                continue
            if current != after:
                unresolved.append(c['path'])
                continue  # Preserve someone else's newer edit.
            if c['before'] is None:
                self.files.delete(self.root, self.prefix + '/' + c['path'])
            else:
                self.files.write(self.root, self.prefix + '/' + c['path'], c['before'], 'base64', expected_sha256=after)
        journal['status'] = 'recovery_required' if unresolved else 'rolled_back'
        journal['unresolved'] = unresolved
        self.save_state(path, journal)
        if unresolved:
            raise ValueError('Recovery conflict; preserve newer edits and review journal locally')

    def recover(self):
        with self.locked():
            recovered = []
            for path in self.pending():
                self.rollback(path, json.loads(path.read_text('utf-8')))
                recovered.append(path.stem)
            return dict(status='recovered', journals=recovered)

    def search(self, query, topic=None, note_type=None, status='active', limit=8, max_chars=12000, linked=True):
        with self.locked():
            self.healthy()
            if not isinstance(query, str) or len(query) > 500:
                raise ValueError('Query exceeds 500 characters')
            limit, max_chars = max(1, min(20, limit)), max(500, min(30000, max_chars))
            terms = set(re.findall(r'\w+', query.casefold()))
            records = self.records()
            candidates = []
            frequencies = collections.Counter()
            for r in records:
                m = r['meta']
                if status and m['status'] != status or topic and normalized(m.get('topic', '')) != normalized(topic) or note_type and m['type'] != note_type:
                    continue
                content = ' '.join(str(m.get(k, '')) for k in ['title', 'topic', 'key', 'value']) + '\n' + r['body']
                tokens = collections.Counter(re.findall(r'\w+', content.casefold()))
                frequencies.update(terms & tokens.keys())
                candidates.append((r, content, tokens))
            ranked = []
            for r, content, tokens in candidates:
                if terms and not terms & tokens.keys():
                    continue
                score = sum(math.log(1 + (len(candidates)+1)/(frequencies[t]+1)) * min(tokens[t], 4) for t in terms)
                score += 3 * len(terms & set(re.findall(r'\w+', r['meta']['title'].casefold())))
                ranked.append((score, r, content))
            ranked.sort(key=lambda x: (-x[0], x[1]['meta']['id']))
            hits, budget = [], max_chars
            by_id = {r['meta']['id']: r for r in records}
            for score, r, content in ranked[:limit]:
                m = r['meta']
                excerpt = content[:min(1500, budget)]
                # Prefer a snippet around a matching term in long documents.
                positions = [content.casefold().find(t) for t in terms if t in content.casefold()]
                if positions:
                    start = max(0, min(positions)-120)
                    excerpt = content[start:start+min(1500, budget)]
                hit = dict(id=m['id'], path=self.prefix+'/'+r['path'], title=m['title'], status=m['status'],
                           score=round(score, 3), excerpt=excerpt, epistemic=m.get('epistemic'),
                           uncertainty=m.get('uncertainty'), evidence=m.get('evidence', []),
                           sources=[dict(id=i, path=self.prefix+'/'+by_id[i]['path'], completeness=by_id[i]['meta'].get('completeness'))
                                    for i in m.get('source_ids', []) if i in by_id])
                hit['provenance_valid'] = all(
                    e['source_id'] in by_id and
                    by_id[e['source_id']]['body'][e['start']:e['end']] == e['quote'] and
                    digest(by_id[e['source_id']]['body'].encode()) == by_id[e['source_id']]['meta'].get('content_sha256')
                    for e in m.get('evidence', []))
                if m['type'] == 'source':
                    hit['provenance_valid'] = digest(r['body'].encode()) == m['content_sha256']
                if linked:
                    hit['related'] = [dict(id=i, path=self.prefix+'/'+by_id[i]['path'], title=by_id[i]['meta']['title'])
                                      for i in m.get('links', []) if i in by_id][:10]
                size = len(json.dumps(hit, ensure_ascii=False))
                if size > budget:
                    break
                hits.append(hit)
                budget -= size
            return dict(query=query, hits=hits, total_matches=len(ranked), truncated=len(hits)<len(ranked),
                        search='weighted lexical full-text + metadata; no embeddings', untrusted_content=True)

    def inspect(self):
        with self.locked():
            self.healthy()
            records = self.records()
            by_id = {r['meta']['id']: r for r in records}
            issues = []
            pairs = collections.defaultdict(list)
            for r in records:
                m = r['meta']
                for ident in m.get('links', []):
                    if ident not in by_id:
                        issues.append(dict(kind='broken_link', id=m['id'], target=ident))
                if m['type'] == 'source':
                    if digest(r['body'].encode()) != m['content_sha256']:
                        issues.append(dict(kind='source_modified', id=m['id']))
                    continue
                for e in m.get('evidence', []):
                    source = by_id.get(e['source_id'])
                    if not source or source['body'][e['start']:e['end']] != e['quote']:
                        issues.append(dict(kind='invalid_evidence', id=m['id']))
                if m['status'] == 'active':
                    pairs[(normalized(m['topic']), normalized(m['key']))].append(m)
                if m['status'] == 'pending':
                    issues.append(dict(kind='pending_review', id=m['id']))
            for pair, group in pairs.items():
                if len(group) > 1:
                    kind = 'duplicate' if len({normalized(m['value']) for m in group}) == 1 else 'conflict'
                    issues.append(dict(kind=kind, topic=pair[0], key=pair[1], ids=[m['id'] for m in group]))
            return dict(notes=len(records), issues=issues, pending_transactions=len(self.pending()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--root', default='Projects')
    parser.add_argument('--prefix', default='Celious/Second Brain')
    sub = parser.add_subparsers(dest='command', required=True)
    archive = sub.add_parser('plan-archive')
    archive.add_argument('input', type=Path, help='Private JSON with title, text, source_ref, completeness, claims')
    commit = sub.add_parser('commit')
    commit.add_argument('plan_id')
    commit.add_argument('approved_sha256')
    supersede = sub.add_parser('plan-supersede')
    supersede.add_argument('old_id')
    supersede.add_argument('new_id')
    supersede.add_argument('reason')
    search = sub.add_parser('search')
    search.add_argument('query')
    search.add_argument('--topic')
    search.add_argument('--type', dest='note_type')
    search.add_argument('--status', default='active')
    search.add_argument('--limit', type=int, default=8)
    sub.add_parser('inspect')
    sub.add_parser('recover')
    args = parser.parse_args()
    config = json.loads(args.config.read_text('utf-8-sig')) if args.config else None
    brain = Brain(Files(config, args.runtime), args.root, args.prefix)
    if args.command == 'plan-archive':
        result = brain.plan_archive(**json.loads(args.input.read_text('utf-8')))
    elif args.command == 'commit':
        result = brain.commit(args.plan_id, args.approved_sha256)
    elif args.command == 'plan-supersede':
        result = brain.plan_supersede(args.old_id, args.new_id, args.reason)
    elif args.command == 'search':
        result = brain.search(args.query, args.topic, args.note_type, args.status or None, args.limit)
    else:
        result = getattr(brain, args.command)()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
