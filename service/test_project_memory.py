"""v0.4 acceptance tests: disposable A/B/shared collections and real baseline migration."""
from pathlib import Path
import json
import multiprocessing
import shutil
import tempfile
import unittest
from engine import Files
from second_brain import Brain as LegacyBrain, parse, render, digest
from project_memory import ProjectBrain


def claim(value='Markdown', evidence='Use Markdown', key='storage', epistemic='accepted'):
    return dict(type='decision',title='Storage format',topic='Architecture',key=key,value=value,
                evidence=evidence,epistemic=epistemic,uncertainty='Supplied test evidence; synthetic fixture only')


def competing_project_commit(config,runtime,preview,queue):
    try:
        brain=ProjectBrain(Files(config,runtime))
        brain.commit(preview['plan_id'],preview['plan_sha256'])
        queue.put('committed')
    except ValueError:
        queue.put('stale')


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='celious-v04-test-')
        self.base=Path(self.tmp.name)
        self.projects=self.base/'projects'
        self.projects.mkdir()
        self.files=Files(dict(direct_operations=True,roots=dict(Projects=dict(path=str(self.projects),writable=True))),self.base/'runtime')
        self.brain=ProjectBrain(self.files)

    def tearDown(self): self.tmp.cleanup()

    def commit(self, preview): return self.brain.commit(preview['plan_id'],preview['plan_sha256'])

    def initialize(self):
        self.commit(self.brain.plan_migrate())
        self.a=self.brain.project()['id']
        self.shared=next(p['id'] for p in self.brain.projects() if p['kind']=='shared')
        preview=self.brain.plan_project('Project-B')
        self.commit(preview)
        self.b=preview['project_id']

    def test_flat_archive_home_and_read_only_historical_aliases(self):
        self.files.config['second_brain']=dict(root='Projects',path='Archives',flat_projects=True)
        brain=ProjectBrain(self.files,prefix='Archives')
        preview=brain.plan_migrate();brain.commit(preview['plan_id'],preview['plan_sha256'])
        self.assertEqual(brain.project()['path'],'Celious')
        preview=brain.plan_project('Tango');brain.commit(preview['plan_id'],preview['plan_sha256'])
        self.assertTrue(brain.path('Tango/PROJECT.md').is_file())
        self.assertFalse(brain.path('Projects').exists())
        self.assertEqual(brain.inspect()['issues'],[])
        with self.assertRaises(ValueError):brain.plan_project('Inbox')
        self.files.config['read_path_aliases']={'Projects':{'Old/Index.md':'Archives/INDEX.md'}}
        self.assertEqual(self.files.path('Projects','Old/Index.md'),brain.path('INDEX.md'))
        with self.assertRaises(PermissionError):self.files.mutation_path('Projects','Old/Index.md')
        self.assertEqual(self.files.path('Projects','oLD\\INDEX.MD'),brain.path('INDEX.md'))
        with self.assertRaises(PermissionError):self.files.mutation_path('Projects','oLD\\INDEX.MD')
        self.files.config['read_path_aliases']['Projects']['Old/Collection']='Archives/Tango'
        self.assertEqual(self.files.path('Projects','OLD/COLLECTION/PROJECT.md'),brain.path('Tango/PROJECT.md'))
        with self.assertRaises(PermissionError):self.files.mutation_path('Projects','old/collection/new.md')
        self.assertNotEqual(self.files.path('Projects','Old/CollectionExtra'),brain.path('Tango'))
        self.files.config['read_path_aliases']['Projects']['Escape']='../outside'
        with self.assertRaises(PermissionError):self.files.path('Projects','Escape')

    def archive(self, project, text='User: Use Markdown', claims=None):
        plan=self.brain.plan_archive('Supplied test transcript',text,'synthetic session','excerpt',[claim()] if claims is None else claims,project)
        self.commit(plan)
        return plan

    def knowledge_hashes(self):
        return {r['path']:digest(self.brain.path(r['path']).read_bytes()) for r in self.brain.records()}

    def test_project_creation_stable_identity_and_physical_spaces(self):
        self.initialize()
        self.assertEqual(len(self.brain.projects()),3)
        for p in self.brain.projects():
            for folder in ['Sources','Knowledge','History']:
                self.assertTrue(self.brain.path(p['path']+'/'+folder).is_dir())
        p=self.brain.project(self.b)
        meta,body=self.brain.read_note(p['path']+'/PROJECT.md')
        meta['name']='Different display name'
        self.brain.path(p['path']+'/PROJECT.md').write_bytes(render(meta,body).encode())
        self.assertEqual(self.brain.project(self.b)['name'],'Different display name')
        self.commit(self.brain.plan_rebuild())
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_archiving_project_isolation_shared_and_explicit_cross_search(self):
        self.initialize()
        self.archive(self.a)
        self.archive(self.b,'User: Use SQLite',[claim('SQLite','Use SQLite')])
        self.archive(self.shared,'User: Prefer portable files',[claim('portable files','Prefer portable files','portability')])
        self.assertEqual(self.brain.search('SQLite',project_id=self.a)['hits'],[])
        self.assertEqual(self.brain.search('SQLite',project_id=self.b)['hits'][0]['project_id'],self.b)
        self.assertEqual(self.brain.search('SQLite',project_id=self.a,cross_project=True)['hits'][0]['project_id'],self.b)
        self.assertEqual(self.brain.search('portable',project_id=self.a)['hits'][0]['scope'],'shared')
        self.assertEqual(self.brain.search('portable',project_id=self.a,include_shared=False)['hits'],[])
        self.assertEqual(self.brain.inspect()['issues'],[])
        self.assertTrue(all(r['path'].startswith(('Projects/','Shared Knowledge/')) for r in self.brain.records()))

    def test_duplicate_conflict_scope_and_history(self):
        self.initialize()
        self.archive(self.a)
        cross=self.brain.plan_archive('Other project','User: Use SQLite','test','excerpt',[claim('SQLite','Use SQLite')],self.b)
        self.assertEqual(cross['warnings'],[])
        self.commit(cross)
        dupe=self.brain.plan_archive('Repeat','User: Use Markdown please','test','excerpt',[claim()],self.a)
        self.assertEqual(dupe['warnings'][0]['kind'],'duplicate')
        self.commit(dupe)
        changed=self.brain.plan_archive('Revision','User: Use plain text','test','excerpt',[claim('plain text','Use plain text')],self.a)
        self.assertEqual(changed['warnings'][0]['kind'],'conflict')
        self.commit(changed)
        notes=[r for r in self.brain.records() if r['project_id']==self.a and r['meta']['type']=='decision']
        old=next(r for r in notes if r['meta']['status']=='active')
        new=next(r for r in notes if r['meta']['status']=='pending')
        self.commit(self.brain.plan_supersede(old['meta']['id'],new['meta']['id'],'Reviewed new decision'))
        self.assertEqual(len(list(self.brain.path(self.brain.project(self.a)['path']+'/History').rglob('*.md'))),2)
        self.assertEqual(self.brain.search('Markdown',project_id=self.a)['hits'],[])
        self.assertTrue(self.brain.search('Markdown',project_id=self.a,status=None)['hits'])
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_missing_project_queue_resolve_and_reject_are_supervised(self):
        self.initialize()
        original=self.knowledge_hashes()
        queue=self.brain.plan_archive('Unassigned','User: Use Markdown','test','excerpt',[claim()])
        self.assertEqual(queue['status'],'awaiting_project')
        self.assertFalse(queue['saved_to_memory'])
        self.assertEqual(self.knowledge_hashes(),original)
        preview=self.brain.resolve_queue(queue['queue_id'],self.b)
        self.assertEqual(self.knowledge_hashes(),original)
        self.commit(preview)
        self.assertEqual(self.brain.search('Markdown',project_id=self.b)['hits'][0]['project_id'],self.b)
        self.assertFalse(self.brain.inbox())
        another=self.brain.plan_archive('Reject this','User: Use text','test','excerpt',[claim('text','Use text')])
        before=self.knowledge_hashes()
        self.brain.reject(another['queue_id'])
        self.assertEqual(self.knowledge_hashes(),before)
        self.assertEqual(self.brain.inbox(True)[-1]['meta']['status'] in {'archived','rejected'},True)
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_rejected_archival_plan_cannot_commit(self):
        self.initialize()
        plan=self.brain.plan_archive('Review','User: Use Markdown','test','excerpt',[claim()],self.a)
        before=self.brain.snapshot()
        self.brain.reject(plan['plan_id'])
        self.assertEqual(self.brain.snapshot(),before)
        with self.assertRaises(ValueError): self.commit(plan)

    def test_identification_trigger_discloses_provisional_and_no_writes(self):
        self.initialize()
        before=self.brain.snapshot()
        text='User: We decided to use Markdown.\nUser: Maybe we could use a database later.\nAssistant: I suggest this solution.\nUser: What remains unresolved?'
        result=self.brain.identify(text,self.a)
        self.assertEqual(result['candidates'][0]['type'],'decision')
        self.assertFalse(result['candidates'][0]['provisional'])
        self.assertTrue(any(c['provisional'] for c in result['candidates']))
        self.assertTrue(all(text[c['start']:c['end']]==c['quote'] for c in result['candidates']))
        self.assertEqual(self.brain.snapshot(),before)
        self.assertFalse(result['saved_to_memory'])
        self.assertTrue(self.brain.identify(text)['assignment_required'])
        self.assertFalse(self.brain.identify('User: Hello there.')['candidates'])

    def test_legacy_migration_preserves_every_byte_id_link_and_old_plan_invalid(self):
        legacy=LegacyBrain(self.files)
        original=legacy.plan_archive('Original source','User: Use Markdown\r\n','test','excerpt',[claim()])
        legacy.commit(original['plan_id'],original['plan_sha256'])
        abandoned=legacy.plan_archive('Old proposal','User: Use Markdown again','test','excerpt',[claim()])
        records={r['meta']['id']:(r['path'],legacy.path(r['path']).read_bytes()) for r in legacy.records()}
        history='History/'+next(i for i in records if i.startswith('note-'))+'/original.md'
        self.files.mkdir('Projects',legacy.prefix+'/'+str(Path(history).parent).replace('\\','/'))
        self.files.write('Projects',legacy.prefix+'/'+history,next(v[1].decode() for i,v in records.items() if i.startswith('note-')))
        history_bytes=legacy.path(history).read_bytes()
        migration=self.brain.plan_migrate()
        self.commit(migration)
        lookup={r['meta']['id']:r for r in self.brain.records()}
        self.assertEqual(set(records),set(lookup))
        for ident,(old,data) in records.items():
            self.assertEqual(self.brain.path(lookup[ident]['path']).read_bytes(),data)
            meta,_=self.brain.read_note(old)
            self.assertEqual(meta['type'],'redirect')
            self.assertEqual(meta['target'],lookup[ident]['path'])
        self.assertEqual(self.brain.path(self.brain.project()['path']+'/'+history).read_bytes(),history_bytes)
        self.assertEqual(self.brain.inspect()['issues'],[])
        with self.assertRaises(ValueError): self.brain.commit(abandoned['plan_id'],abandoned['plan_sha256'])

    def test_migration_interruption_and_rollback_to_working_legacy(self):
        legacy=LegacyBrain(self.files)
        p=legacy.plan_archive('Legacy','User: Use Markdown','test','excerpt',[claim()])
        legacy.commit(p['plan_id'],p['plan_sha256'])
        before=self.brain.snapshot()
        plan=self.brain.plan_migrate()
        self.brain._failure_after=5
        with self.assertRaises(OSError): self.commit(plan)
        self.assertEqual(self.brain.snapshot(),before)
        self.assertEqual(legacy.search('Markdown')['hits'][0]['provenance_valid'],True)
        self.assertIsNone(self.brain.layout())
        self.brain._failure_after=None
        self.commit(self.brain.plan_migrate())
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_stale_descriptors_indexes_and_cross_project_supersession_blocked(self):
        self.initialize()
        self.archive(self.a)
        self.archive(self.b,'User: Use SQLite',[claim('SQLite','Use SQLite')])
        notes=[r for r in self.brain.records() if r['meta']['type']=='decision']
        with self.assertRaises(ValueError): self.brain.plan_supersede(notes[0]['meta']['id'],notes[1]['meta']['id'],'Wrong project')
        p=self.brain.plan_project('New')
        self.brain.path('INDEX.md').write_text('Changed outside coordinator','utf-8')
        with self.assertRaises(ValueError): self.commit(p)
        self.assertTrue(any(i['kind']=='index_outdated' for i in self.brain.inspect()['issues']))
        self.commit(self.brain.plan_rebuild())
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_cross_links_do_not_import_other_project_context(self):
        self.initialize()
        self.archive(self.b,'User: Use SQLite',[claim('SQLite','Use SQLite')])
        other=next(r for r in self.brain.records() if r['meta']['type']=='decision')
        c=claim()
        c['links']=[other['meta']['id']]
        self.archive(self.a,claims=[c])
        hit=self.brain.search('Markdown',project_id=self.a,include_shared=False)['hits'][0]
        self.assertNotIn(other['meta']['id'],[r['id'] for r in hit['related']])
        self.assertTrue(self.brain.search('SQLite',project_id=self.a,cross_project=True)['hits'])

    def test_read_only_invalid_project_names_and_provisional_supersession(self):
        self.initialize()
        for name in ['../escape','bad/name','CON','bad.','bad ']:
            with self.assertRaises((PermissionError,ValueError)): self.brain.plan_project(name)
        with self.assertRaises(ValueError): self.brain.search('test',project_id='guessed')
        self.archive(self.a)
        self.archive(self.a,'User: Maybe use text',[claim('text','Maybe use text',epistemic='pending')])
        notes=[r for r in self.brain.records() if r['meta']['type']=='decision']
        old=next(r for r in notes if r['meta']['status']=='active')
        new=next(r for r in notes if r['meta']['status']=='pending')
        with self.assertRaises(ValueError): self.brain.plan_supersede(old['meta']['id'],new['meta']['id'],'Unconfirmed')
        self.files.config['read_only']=True
        with self.assertRaises(PermissionError): self.brain.plan_project('Readonly')

    def test_real_v03_fixture_migration_and_restoration(self):
        import zipfile
        workspace=Path(__file__).resolve().parents[2]
        backups=sorted((workspace/'Backups').glob('Celious-v0.3-before-v0.4-*/baseline.zip'))
        if not backups: self.skipTest('Private verified baseline is not part of public source')
        destination=self.brain.path('')
        prefix='Projects/Celious/Second Brain/'
        with zipfile.ZipFile(backups[-1]) as archive:
            for name in archive.namelist():
                if name.startswith(prefix) and not name.endswith('/'):
                    target=destination/name[len(prefix):]
                    self.assertTrue(target.resolve().is_relative_to(destination.resolve()))
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(name))
        before={r['meta']['id']:digest(self.brain.path(r['path']).read_bytes()) for r in self.brain.records()}
        plan=self.brain.plan_migrate()
        self.commit(plan)
        after={r['meta']['id']:digest(self.brain.path(r['path']).read_bytes()) for r in self.brain.records()}
        self.assertEqual(before,after)
        self.assertEqual(len(after),12)
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_hard_interruption_recovery_blocks_reads_and_restores_legacy(self):
        legacy=LegacyBrain(self.files)
        original=legacy.plan_archive('Legacy','User: Use Markdown','test','excerpt',[claim()])
        legacy.commit(original['plan_id'],original['plan_sha256'])
        before=self.brain.snapshot()
        preview=self.brain.plan_migrate()
        plan=self.brain.load_plan(preview['plan_id'])
        journal=dict(status='applying',plan=plan,touched=[])
        for c in plan['changes'][:5]:
            parent=str(Path(c['path']).parent).replace('\\','/')
            self.files.mkdir('Projects',self.brain.prefix+'/'+parent)
            journal['touched'].append(c['path'])
            self.files.write('Projects',self.brain.prefix+'/'+c['path'],c['text'],expected_sha256=c['expected'] or '')
        path=self.brain.state/('journal-'+preview['plan_id']+'.json')
        self.brain.save_state(path,journal)
        with self.assertRaises(ValueError): self.brain.inspect()
        self.brain.recover()
        self.assertEqual(self.brain.snapshot(),before)
        self.assertTrue(legacy.search('Markdown')['hits'])

    def test_failed_project_creation_and_archive_restore_prior_state(self):
        self.initialize()
        before=self.brain.snapshot()
        plan=self.brain.plan_project('Failed project')
        self.brain._failure_after=2
        with self.assertRaises(OSError): self.commit(plan)
        self.assertEqual(before,self.brain.snapshot())
        self.assertEqual(self.brain.inspect()['issues'],[])
        self.brain._failure_after=None
        self.commit(self.brain.plan_project('Failed project'))
        before=self.brain.snapshot()
        plan=self.brain.plan_archive('Archive','User: Use Markdown','test','excerpt',[claim()],self.a)
        self.brain._failure_after=3
        with self.assertRaises(OSError): self.commit(plan)
        self.assertEqual(before,self.brain.snapshot())
        self.assertEqual(self.brain.inspect()['issues'],[])

    def test_exact_plan_hash_and_bounded_project_context(self):
        self.initialize()
        p=self.brain.plan_archive('Archive','User: Use Markdown','test','excerpt',[claim()],self.a)
        with self.assertRaises(ValueError): self.brain.commit(p['plan_id'],'wrong digest')
        self.commit(p)
        self.assertEqual(self.brain.search('giraffe',project_id=self.a)['hits'],[])
        self.assertLess(len(json.dumps(self.brain.search('Markdown',project_id=self.a,max_chars=500))),1000)
        self.assertEqual(self.brain.identify('User: This is not a decision; maybe we might choose text.',self.a)['candidates'][0]['provisional'],True)

    def test_unrelated_destination_file_and_uncertain_fact_are_not_promoted(self):
        self.initialize()
        plan=self.brain.plan_archive('Hypothesis','User: Maybe use a database','test','excerpt',[claim('database','Maybe use a database')],self.a)
        self.assertTrue(any(w['kind']=='provisional' for w in plan['warnings']))
        self.commit(plan)
        note=next(r for r in self.brain.records() if r['meta']['type']=='decision')
        self.assertEqual((note['meta']['status'],note['meta']['epistemic']),('pending','pending'))
        p=self.brain.plan_project('Collision')
        root=self.brain.path('Projects/Collision')
        root.mkdir()
        (root/'unrelated.txt').write_text('Preserve this unrelated material','utf-8')
        with self.assertRaises(ValueError): self.commit(p)
        self.assertEqual((root/'unrelated.txt').read_text(),'Preserve this unrelated material')

    def test_independent_project_commit_processes_are_serialized(self):
        self.initialize()
        previews=[self.brain.plan_archive('A','User: Use Markdown','test','excerpt',[claim()],self.a),
                  self.brain.plan_archive('B','User: Use SQLite','test','excerpt',[claim('SQLite','Use SQLite')],self.b)]
        context=multiprocessing.get_context('spawn')
        queue=context.Queue()
        processes=[context.Process(target=competing_project_commit,args=(self.files.config,str(self.files.runtime),p,queue)) for p in previews]
        for process in processes: process.start()
        for process in processes:
            process.join(25)
            self.assertEqual(process.exitcode,0)
        self.assertEqual(sorted([queue.get(timeout=2),queue.get(timeout=2)]),['committed','stale'])
        queue.close()
        self.assertEqual(self.brain.inspect()['issues'],[])


if __name__=='__main__': unittest.main(verbosity=2)
