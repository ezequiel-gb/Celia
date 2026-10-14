"""Memory acceptance tests use isolated roots only, never production config."""
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from engine import Files
from second_brain import Brain, parse, digest


def claim(value='Markdown', evidence='Use Markdown'):
    return dict(type='decision', title='Storage format', topic='Celious', key='storage',
                value=value, evidence=evidence, epistemic='accepted', uncertainty='Explicit supplied decision; current until superseded')


def competing_commit(config, runtime, plan, queue):
    try:
        b = Brain(Files(config, runtime))
        b.commit(plan['plan_id'], plan['plan_sha256'])
        queue.put('committed')
    except ValueError:
        queue.put('conflict')


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='celious-memory-test-')
        self.base = Path(self.temporary.name)
        (self.base / 'projects').mkdir()
        self.config = dict(direct_operations=True, roots=dict(Projects=dict(path=str(self.base/'projects'), writable=True)))
        self.files = Files(self.config, self.base/'runtime')
        self.brain = Brain(self.files)

    def tearDown(self):
        self.temporary.cleanup()

    def plan(self, text='User: Use Markdown', claims=None):
        return self.brain.plan_archive('Sample accessible conversation', text, 'test-session', 'excerpt',
                                       [claim()] if claims is None else claims)

    def commit(self, plan):
        return self.brain.commit(plan['plan_id'], plan['plan_sha256'])

    def test_archive_provenance_and_new_session(self):
        plan = self.plan()
        self.assertFalse(self.brain.path('INDEX.md').exists())
        self.commit(plan)
        other = Brain(Files(self.config, self.base/'runtime'))
        hit = other.search('storage Markdown')['hits'][0]
        self.assertEqual(hit['epistemic'], 'accepted')
        self.assertEqual(hit['sources'][0]['completeness'], 'excerpt')
        self.assertIn('Use Markdown', hit['evidence'][0]['quote'])
        self.assertEqual(other.inspect()['issues'], [])
        with self.assertRaises(ValueError):
            self.commit(plan)

    def test_evidence_validation_and_completeness(self):
        with self.assertRaises(ValueError):
            self.plan(claims=[claim(evidence='Never supplied')])
        with self.assertRaises(ValueError):
            self.brain.plan_archive('x','x','x','inferred complete',[])
        plan = self.plan(text='User: Use Markdown\r\nAssistant: OK\r\n')
        self.commit(plan)
        self.assertEqual(self.brain.inspect()['issues'], [])

    def test_duplicate_and_conflict_then_supersession(self):
        self.commit(self.plan())
        duplicate = self.plan('User: Use Markdown, please')
        self.assertEqual(duplicate['warnings'][0]['kind'], 'duplicate')
        self.commit(duplicate)
        self.assertEqual(len([r for r in self.brain.records() if r['meta']['type']=='decision']), 1)
        conflict = self.plan('User: Use plain text', [claim('plain text', 'Use plain text')])
        self.assertEqual(conflict['warnings'][0]['kind'], 'conflict')
        self.commit(conflict)
        notes = [r for r in self.brain.records() if r['meta']['type']=='decision']
        old = next(r for r in notes if r['meta']['status']=='active')
        new = next(r for r in notes if r['meta']['status']=='pending')
        update = self.brain.plan_supersede(old['meta']['id'], new['meta']['id'], 'User revised decision')
        self.commit(update)
        self.assertEqual(self.brain.search('plain text')['hits'][0]['id'], new['meta']['id'])
        self.assertEqual(len(list(self.brain.path('History').rglob('*.md'))), 2)
        self.assertEqual(self.brain.inspect()['issues'], [])
        self.assertIn(old['meta']['id'], self.brain.path('INDEX.md').read_text())

    def test_stale_plan_rejected_and_exact_approval(self):
        first, second = self.plan(), self.plan('User: Use Markdown too')
        with self.assertRaises(ValueError):
            self.brain.commit(first['plan_id'], 'wrong')
        self.commit(first)
        with self.assertRaises(ValueError):
            self.commit(second)
        self.assertEqual(self.brain.inspect()['notes'], 2)

    def test_failed_write_rolls_back_and_retains_recovery(self):
        self.commit(self.plan())
        original = self.brain.path('INDEX.md').read_bytes()
        plan = self.plan('User: Use plain text', [claim('plain text', 'Use plain text')])
        self.brain._failure_after = 2
        with self.assertRaises(OSError):
            self.commit(plan)
        self.assertEqual(self.brain.path('INDEX.md').read_bytes(), original)
        self.assertEqual(self.brain.inspect()['notes'], 2)
        self.assertTrue(list((self.files.runtime/'trash').glob('*/payload')))

    def test_crash_recovery_and_preserve_concurrent_edit(self):
        plan = self.plan()
        data = self.brain.load_plan(plan['plan_id'])
        c = data['changes'][0]
        self.files.mkdir('Projects', self.brain.prefix+'/Sources')
        self.files.write('Projects', self.brain.prefix+'/'+c['path'], c['text'])
        journal = dict(status='applying', plan=data, touched=[c['path']])
        path = self.brain.state/('journal-'+plan['plan_id']+'.json')
        self.brain.save_state(path, journal)
        with self.assertRaises(ValueError):
            self.brain.search('anything')
        self.brain.recover()
        self.assertFalse(self.brain.path(c['path']).exists())
        # A newer third-party edit must never be overwritten by recovery.
        self.files.write('Projects', self.brain.prefix+'/'+c['path'], 'someone else changed it')
        self.brain.save_state(path, journal)
        with self.assertRaises(ValueError):
            self.brain.recover()
        self.assertEqual(self.brain.path(c['path']).read_text(), 'someone else changed it')

    def test_policy_boundaries_and_read_only(self):
        for prefix in ['../escape', 'C:/outside', '.hidden', 'Celious/../escape']:
            with self.assertRaises(PermissionError):
                Brain(self.files, prefix=prefix)
        self.files.config['read_only'] = True
        with self.assertRaises(PermissionError):
            self.plan()

    def test_metadata_filters_budget_and_deterministic_rank(self):
        self.commit(self.plan())
        self.assertEqual(self.brain.search('Markdown', topic='Other')['hits'], [])
        self.assertEqual(self.brain.search('Markdown', note_type='source')['hits'], [])
        self.assertEqual(self.brain.search('missing')['hits'], [])
        a = self.brain.search('Markdown')
        self.assertEqual(a, self.brain.search('Markdown'))
        self.assertLessEqual(len(json.dumps(self.brain.search('Markdown', max_chars=500))), 1000)

    def test_integrity_detects_tampered_evidence_and_links(self):
        self.commit(self.plan())
        source = next(r for r in self.brain.records() if r['meta']['type']=='source')
        node = self.brain.path(source['path'])
        node.write_bytes(node.read_bytes().replace(b'Use Markdown', b'Use changed!'))
        issues = self.brain.inspect()['issues']
        self.assertTrue(any(i['kind']=='source_modified' for i in issues))
        self.assertTrue(any(i['kind']=='invalid_evidence' for i in issues))

    def test_cross_process_concurrent_commits(self):
        context = multiprocessing.get_context('spawn')
        queue = context.Queue()
        plans = [self.plan(), self.plan('User: Use Markdown again')]
        workers = [context.Process(target=competing_commit, args=(self.config, str(self.base/'runtime'), p, queue)) for p in plans]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(20)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(sorted([queue.get(timeout=2), queue.get(timeout=2)]), ['committed','conflict'])
        queue.close()
        self.assertEqual(self.brain.inspect()['issues'], [])

    def test_retrieval_relevance_against_distractors(self):
        examples = [
            ('storage', 'portable Markdown', 'Keep knowledge in portable Markdown files.'),
            ('connection', 'single secure tunnel', 'Use a single secure tunnel connection.'),
            ('credential', 'memory only', 'Keep the credential in memory only.'),
            ('approval', 'review recovery first', 'Review the recovery plan before modifying files.'),
            ('navigation', 'Obsidian backlinks', 'Navigate knowledge with Obsidian backlinks.'),
            ('inference', 'no paid model calls', 'Do not add paid model inference calls.'),
        ]
        for key, value, text in examples:
            c = claim(value, text)
            c.update(title=key.title(), key=key)
            self.commit(self.plan(text, [c]))
        for query, expected in [('Markdown files','storage'), ('secure tunnel','connection'),
                                ('credential memory','credential'), ('Obsidian backlinks','navigation'),
                                ('paid inference','inference')]:
            result = self.brain.search(query)
            top = next(r for r in self.brain.records() if r['meta']['id']==result['hits'][0]['id'])
            self.assertEqual(top['meta']['key'], expected)
        self.assertEqual(self.brain.search('unrelated giraffe')['hits'], [])

    def test_wiki_links_resolve_without_obsidian(self):
        self.commit(self.plan())
        import re
        for path in self.brain.path('').rglob('*.md'):
            for target in re.findall(r'\[\[([^]|]+)(?:\|[^]]*)?\]\]', path.read_text('utf-8')):
                self.assertTrue(self.brain.path(target+'.md').is_file(), target)


    def test_file_created_after_final_check_is_preserved(self):
        plan = self.plan()
        original = self.files.write
        injected = False
        def race(root, path, content, *args, **kwargs):
            nonlocal injected
            if not injected:
                injected = True
                self.files.path(root, path).write_text('Concurrent writer content', 'utf-8')
            return original(root, path, content, *args, **kwargs)
        self.files.write = race
        with self.assertRaises(ValueError):
            self.commit(plan)
        target = self.brain.path(self.brain.load_plan(plan['plan_id'])['changes'][0]['path'])
        self.assertEqual(target.read_text(), 'Concurrent writer content')
        self.assertTrue(self.brain.pending())


if __name__ == '__main__':
    unittest.main(verbosity=2)
