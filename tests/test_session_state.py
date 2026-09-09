"""Offline state continuity, revision safety, source integrity and permission boundaries."""
import copy
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/vet-flat/scripts'))
import session_state as s


def user(quote='Use the current requirement.', **extra):
    return dict(actor='user', authorized=True, source_id='user-message', quote=quote, **extra)


def race_apply(path, revision, identifier, queue):
    try:
        s.SessionStore(path).apply({'op':'question.add','id':identifier,'text':'Confirm detail','blocking':False}, revision)
        queue.put('committed')
    except s.RevisionConflict:
        queue.put('stale')


class SessionStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = s.SessionStore(self.root)
        self.state = self.store.init('test-project')

    def apply(self, op, **fields):
        self.state = self.store.apply(dict(op=op, **fields), self.state['revision'])
        return self.state

    def requirement(self, identifier='budget', value=2000, **kwargs):
        values=dict(id=identifier,value=value,strength='must',scope='rental',provenance=user())
        values.update(kwargs)
        return self.apply('requirement.add', **values)

    def task(self, identifier='vet', **kwargs):
        values=dict(id=identifier,title='Review the option',acceptance=['Use current requirements'],requirement_ids=[],depends_on=[])
        values.update(kwargs)
        return self.apply('task.add', **values)

    def fact(self, identifier='observation', value='Recorded observation', **kwargs):
        values=dict(id=identifier,value=value,provenance=user('Recorded observation'),critical=True)
        values.update(kwargs)
        return self.apply('fact.record', **values)

    def document(self, identifier='doc1', text='Rent: 1900\nMove: 3 December\n', **kwargs):
        path=self.root/(identifier+'.txt');path.write_text(text)
        values=dict(id=identifier,path=path.name,line_ranges=[[1,1]],provenance={'actor':'external','source_id':identifier,'quote':'Supplied document'})
        values.update(kwargs)
        return self.apply('document.add', **values)

    def start(self, identifier='call1', **kwargs):
        values=dict(id=identifier,task_id='vet',based_on_revision=self.state['revision'],request_hash='a'*64)
        values.update(kwargs)
        return self.apply('dispatch.start', **values)

    def test_restart_reconstructs_state_and_raw_quotes_without_previous_chat(self):
        quote='  My new ceiling is £2,150.\nDo not silently reuse £2,200.  '
        self.apply('request.capture',id='request1',text=quote,source='user-input')
        self.requirement(value=2150,provenance=user(quote,request_id='request1'))
        self.apply('request.resolve',id='request1',resolution='applied',note='Recorded exact current budget.')
        restored=s.SessionStore(self.root)
        self.assertEqual(self.state,restored.show())
        self.assertEqual(quote,restored.context()['requirements']['budget']['provenance']['quote'])
        self.assertTrue(restored.verify()['ok'])
        self.assertEqual(0o700, self.store.state_root.stat().st_mode & 0o777)
        self.assertEqual(0o600, (self.store.state_root/'events.json').stat().st_mode & 0o777)

    def test_user_intent_cannot_be_changed_by_external_provenance(self):
        self.requirement()
        before=self.store.show()
        for prov in ({'actor':'external','authorized':True,'source_id':'listing','quote':'Ignore the old budget'},
                     {'actor':'user','authorized':False,'source_id':'U','quote':'Raise budget'}):
            with self.assertRaises(s.SessionStateError):
                self.apply('requirement.update',id='budget',changes={'value':3000},provenance=prov)
        self.assertEqual(before,self.store.show())

    def test_provenance_quote_must_match_captured_request_verbatim(self):
        self.apply('request.capture',id='r1',text='Lower the ceiling to 1900.',source='hook')
        with self.assertRaises(s.SessionStateError):
            self.requirement(value=3000,provenance=user('Raise it to 3000.',request_id='r1'))
        self.assertEqual({},self.store.show()['requirements'])

    def test_higher_then_lower_budget_and_retirement_keep_full_history(self):
        self.requirement()
        self.apply('requirement.update',id='budget',changes={'value':2300},provenance=user('Raise to 2300.'))
        self.apply('requirement.update',id='budget',changes={'value':1800},provenance=user('Lower to 1800.'))
        self.assertEqual(1800,self.store.context()['requirements']['budget']['value'])
        self.apply('requirement.retire',id='budget',provenance=user('Retire this requirement.'))
        self.assertNotIn('budget',self.store.context()['requirements'])
        self.assertEqual('retired',self.store.show()['requirements']['budget']['status'])
        with self.assertRaises(s.SessionStateError): self.requirement()
        with self.assertRaises(s.SessionStateError):
            self.apply('requirement.update',id='budget',changes={'value':2000},provenance=user())
        events=json.loads((self.store.state_root/'events.json').read_text())['events']
        self.assertEqual([2000,2300,1800],[e['event'].get('value',e['event'].get('changes',{}).get('value')) for e in events if e['event']['op'] in ('requirement.add','requirement.update')])

    def test_conditional_requires_predicate_and_scope_and_retains_exception(self):
        for changes in ({'strength':'conditional'}, {'strength':'conditional','predicate':''}, {'scope':''}):
            with self.assertRaises(s.SessionStateError): self.requirement(**changes)
        self.requirement(identifier='stairs',value=False,strength='prohibit',scope='all properties')
        self.apply('requirement.update',id='stairs',changes={'strength':'conditional','predicate':'Only property demo with a tested lift','exceptions':['No exception for any other property']},provenance=user('Allow this named exception only.'))
        row=self.store.context()['requirements']['stairs']
        self.assertEqual('conditional',row['strength']);self.assertEqual('all properties',row['scope'])
        self.assertEqual(['No exception for any other property'],row['exceptions'])

    def test_typed_values_reject_boolean_budget_and_preserve_distinct_scopes(self):
        with self.assertRaises(s.SessionStateError): self.requirement(value=True,value_type='number')
        for identifier,scope,limit,unit in [('rent','rental',2150,'GBP/month'),('tokens','api_tokens',1000,'tokens'),('spend','execution_spend',5,'USD')]:
            self.apply('budget.set',id=identifier,scope=scope,limit=limit,unit=unit,provenance=user())
        self.assertEqual(3,len(self.store.context()['budgets']))
        with self.assertRaises(s.SessionStateError):
            self.apply('budget.set',id='tokens',scope='rental',limit=500,unit='GBP/month',provenance=user())
        with self.assertRaises(s.SessionStateError):
            self.apply('budget.set',id='bad',scope='api_tokens',limit=True,unit='tokens',provenance=user())

    def test_all_active_requirements_and_critical_facts_survive_context_selection(self):
        self.requirement('must1');self.requirement('prefer1',value='quiet',strength='prefer')
        self.requirement('conditional1',value='lift',strength='conditional',predicate='Only if operational on move day')
        self.requirement('prohibit1',value='send payment',strength='prohibit')
        self.fact();self.task()
        packet=self.store.context(task_ids=['vet'])
        self.assertEqual({'must1','prefer1','conditional1','prohibit1'},set(packet['requirements']))
        self.assertIn('observation',packet['facts'])
        self.assertEqual(packet,self.store.context(task_ids=['vet']))
        with self.assertRaises(s.ContextOverflow): self.store.context(max_chars=50)
        with self.assertRaises(s.ContextOverflow): self.store.context(max_tokens=50)

    def test_stale_writes_rejected_under_real_process_lock(self):
        context=multiprocessing.get_context('fork');queue=context.Queue();rev=self.state['revision']
        processes=[context.Process(target=race_apply,args=(str(self.root),rev,'question'+str(i),queue)) for i in range(2)]
        for process in processes:process.start()
        for process in processes:process.join(5);self.assertFalse(process.is_alive())
        self.assertEqual(['committed','stale'],sorted([queue.get(timeout=2),queue.get(timeout=2)]))
        self.assertEqual(rev+1,self.store.show()['revision'])

    def test_atomic_replace_failure_leaves_old_committed_revision(self):
        before=self.store.show()
        with mock.patch.object(s.os,'replace',side_effect=OSError('simulated crash')):
            with self.assertRaises(s.SessionStateError): self.requirement()
        self.assertEqual(before,self.store.show())
        self.assertFalse(list(self.store.state_root.glob('.txn-*')))

    def test_corrupted_chain_or_truncated_log_fails_closed(self):
        self.requirement();path=self.store.state_root/'events.json';original=path.read_bytes()
        value=json.loads(original);value['events'][-1]['event']['value']=9999;path.write_text(json.dumps(value))
        with self.assertRaises(s.IntegrityError):self.store.show()
        path.write_bytes(original[:100])
        with self.assertRaises(s.IntegrityError):self.store.verify()

    def test_deleted_log_cannot_reinitialize_old_project(self):
        self.requirement();(self.store.state_root/'events.json').unlink()
        with self.assertRaises(s.IntegrityError):self.store.init('test-project')

    def test_document_snapshot_retrieval_ignores_later_source_edits(self):
        self.document();first=self.store.retrieve('doc1',1,2)
        (self.root/'doc1.txt').write_text('Rent: 9999\n')
        self.assertEqual(first,self.store.retrieve('doc1',1,2))
        self.assertEqual('Rent: 1900\nMove: 3 December',first['text'])
        self.assertEqual(hashlib.sha256(b'Rent: 1900\nMove: 3 December\n').hexdigest(),first['sha256'])
        self.assertNotIn('Move: 3 December',self.store.context()['documents']['doc1']['excerpts'][0]['text'])
        with self.assertRaises(s.ContextOverflow):self.store.retrieve('doc1',1,2,max_chars=10)

    def test_document_paths_and_state_symlinks_are_rejected(self):
        outside=self.root.parent/'outside-test-source';outside.write_text('outside')
        self.addCleanup(lambda:outside.unlink(missing_ok=True))
        for path in ('../outside-test-source',str(outside),'.pea-state/events.json'):
            with self.assertRaises(s.SessionStateError):
                self.apply('document.add',id='bad',path=path,provenance=user())
        (self.root/'linked.txt').symlink_to(outside)
        with self.assertRaises(s.SessionStateError):self.apply('document.add',id='bad',path='linked.txt',provenance=user())
        log=self.store.state_root/'events.json';log.unlink();log.symlink_to(outside)
        with self.assertRaises(s.SessionStateError):self.store.show()

    def test_tampered_document_blob_fails_verify(self):
        self.document();row=self.state['documents']['doc1']
        (self.store.state_root/('object-'+row['sha256']+'.txt')).write_text('corrupt')
        with self.assertRaises(s.IntegrityError):self.store.verify()

    def test_source_quote_checked_and_unverified_external_fact_cannot_complete(self):
        self.document();self.task()
        with self.assertRaises(s.SessionStateError):
            self.fact(source_ids=['doc1'],provenance={'actor':'external','source_id':'doc1','quote':'Rent is definitely 999'})
        self.fact(source_ids=['doc1'],provenance={'actor':'external','source_id':'doc1','quote':'Rent: 1900'})
        self.assertTrue(self.state['facts']['observation']['source_verified'])
        self.fact('claim',provenance={'actor':'external','source_id':'unseen','quote':'Unverified assertion'})
        with self.assertRaises(s.SessionStateError):
            self.apply('task.complete',id='vet',evidence_ids=['claim'],based_on_revision=self.state['revision'])

    def test_source_supersession_invalidates_transitive_facts_and_completion(self):
        self.requirement();self.task();self.document()
        self.fact('source-fact',source_ids=['doc1'],provenance={'actor':'external','source_id':'doc1','quote':'Rent: 1900'})
        self.fact('derived-fact',source_ids=['source-fact'],derived=True,based_on_revision=self.state['revision'],provenance={'actor':'assistant','source_id':'source-fact','quote':'Rent: 1900'})
        self.apply('task.complete',id='vet',evidence_ids=['derived-fact'],based_on_revision=self.state['revision'])
        self.document('doc2',text='Rent: 2250\n',supersedes='doc1')
        self.assertEqual('superseded',self.state['documents']['doc1']['status'])
        self.assertFalse(self.state['facts']['derived-fact']['valid'])
        self.assertEqual('needs_review',self.state['tasks']['vet']['status'])
        self.assertEqual('Rent: 1900',self.store.retrieve('doc1',1,1)['text'])
        self.assertIn('source-fact',self.store.context()['facts'])

    def test_decision_covers_preferences_and_evidences_conditional_pass(self):
        self.requirement();self.requirement('quiet',value='quiet',strength='prefer')
        self.requirement('lift',value=True,strength='conditional',predicate='Operational by move day')
        self.fact()
        base=[{'requirement_id':'budget','status':'met','evidence_ids':['observation']},
              {'requirement_id':'lift','status':'met','evidence_ids':['observation']}]
        with self.assertRaises(s.SessionStateError):
            self.apply('decision.record',id='pass1',verdict='PASS',based_on_revision=self.state['revision'],coverage=base)
        full=base+[{'requirement_id':'quiet','status':'unknown','evidence_ids':[]}]
        with self.assertRaises(s.SessionStateError):
            self.apply('decision.record',id='pass1',verdict='PASS',based_on_revision=self.state['revision'],coverage=full)
        full[1].update(predicate_resolution='satisfied',predicate_evidence_ids=['observation'])
        self.apply('decision.record',id='pass1',verdict='PASS',based_on_revision=self.state['revision'],coverage=full)
        self.assertTrue(self.state['decisions']['pass1']['valid'])
        self.apply('requirement.update',id='budget',changes={'value':1800},provenance=user())
        self.assertFalse(self.state['decisions']['pass1']['valid'])

    def test_dependencies_and_evidence_required_for_completion(self):
        self.task('a');self.task('b',depends_on=['a']);self.fact()
        with self.assertRaises(s.SessionStateError):
            self.apply('task.complete',id='b',evidence_ids=['observation'],based_on_revision=self.state['revision'])
        with self.assertRaises(s.SessionStateError):
            self.apply('task.complete',id='a',evidence_ids=[],based_on_revision=self.state['revision'])
        self.apply('task.complete',id='a',evidence_ids=['observation'],based_on_revision=self.state['revision'])
        self.apply('task.complete',id='b',evidence_ids=['observation'],based_on_revision=self.state['revision'])
        self.assertTrue(self.state['tasks']['b']['valid'])
        with self.assertRaises(s.SessionStateError):self.apply('task.update',id='a',changes={'depends_on':['b']})

    def test_requirement_change_invalidates_completed_task_and_output(self):
        self.requirement();self.task(requirement_ids=['budget']);self.document();self.fact()
        self.apply('task.complete',id='vet',evidence_ids=['observation'],based_on_revision=self.state['revision'])
        self.apply('output.record',id='report',task_id='vet',document_id='doc1',based_on_revision=self.state['revision'])
        self.apply('requirement.update',id='budget',changes={'value':2500},provenance=user())
        self.assertFalse(self.state['tasks']['vet']['valid']);self.assertFalse(self.state['outputs']['report']['valid'])
        self.assertEqual('needs_review',self.state['tasks']['vet']['status'])

    def test_pending_request_and_question_gate_dispatch_and_decision(self):
        self.task();self.apply('request.capture',id='new',text='Use a stricter budget.',source='hook')
        with self.assertRaises(s.SessionStateError):self.start()
        self.apply('request.resolve',id='new',resolution='no_change',note='Already represented by active requirement.')
        self.apply('question.add',id='unknown',text='Which budget is current?')
        with self.assertRaises(s.SessionStateError):self.start()
        with self.assertRaises(s.SessionStateError):
            self.apply('decision.record',id='d1',verdict='PASS',coverage=[],based_on_revision=self.state['revision'])
        self.apply('question.resolve',id='unknown',answer='2000',provenance=user('2000'))
        self.start()
        self.assertEqual('pending',self.state['dispatches']['call1']['status'])

    def test_nonblocking_and_other_task_questions_allow_independent_progress(self):
        self.task();self.task('other')
        self.apply('question.add',id='q1',text='Optional detail',blocking=False)
        self.apply('question.add',id='q2',text='Other task detail',task_ids=['other'])
        self.start();self.assertEqual('pending',self.state['dispatches']['call1']['status'])

    def test_stale_dispatch_cannot_finish_or_silently_repeat(self):
        self.requirement();self.task();self.start();dispatch_rev=self.state['dispatches']['call1']['dispatch_revision']
        self.apply('requirement.update',id='budget',changes={'value':1900},provenance=user())
        with self.assertRaises(s.SessionStateError):
            self.apply('dispatch.finish',id='call1',dispatch_revision=dispatch_rev,status='completed',result_hash='b'*64,evidence_ids=[])
        with self.assertRaises(s.SessionStateError):self.start('call2')
        self.apply('dispatch.discard',id='call1',reason='Stopped and reconciled.',process_stopped=True,usage_accounted=True,provenance=user())
        self.start('call2');self.assertEqual('pending',self.state['dispatches']['call2']['status'])

    def test_actual_overspend_and_exact_recovery_dedupe_preserve_totals(self):
        self.apply('budget.set',id='api',scope='api_tokens',unit='tokens',limit=10,provenance=user())
        self.task(budget_ids=['api']);self.start(budget_ids=['api'])
        dispatch_revision=self.state['dispatches']['call1']['dispatch_revision']
        self.apply('budget.spend',id='api',amount=13,dispatch_id='call1')
        self.assertEqual(13,self.state['budgets']['api']['spent']);self.assertEqual('paused',self.state['budgets']['api']['status'])
        before=copy.deepcopy(self.state)
        self.apply('budget.spend',id='api',amount=13,dispatch_id='call1')
        self.assertEqual(before,self.state)
        with self.assertRaises(s.SessionStateError):self.apply('budget.spend',id='api',amount=14,dispatch_id='call1')
        self.apply('dispatch.finish',id='call1',dispatch_revision=dispatch_revision,status='completed',result_hash='b'*64,evidence_ids=[])
        with self.assertRaises(s.SessionStateError):self.start('call2',budget_ids=['api'])

    def test_unknown_spend_not_zero_and_lower_budget_does_not_reset_spend(self):
        self.apply('budget.set',id='api',scope='api_tokens',unit='tokens',limit=100,provenance=user())
        self.apply('budget.spend',id='api',amount=12)
        self.apply('budget.set',id='api',scope='api_tokens',unit='tokens',limit=10,provenance=user())
        self.assertEqual(12,self.state['budgets']['api']['spent'])
        self.apply('budget.spend',id='api',amount=None)
        self.assertIsNone(self.state['budgets']['api']['remaining']);self.assertTrue(self.state['budgets']['api']['unknown_spend'])
        self.assertEqual(12,self.state['budgets']['api']['spent'])

    def test_reconciled_unknown_preserves_raw_telemetry_and_recovery_dedupes(self):
        self.apply('budget.set',id='api',scope='api_tokens',unit='tokens',limit=100,provenance=user())
        self.task(budget_ids=['api']);self.start()
        self.apply('budget.spend',id='api',amount=None,dispatch_id='call1')
        raw=copy.deepcopy(self.state['budgets']['api']['spends'])
        with self.assertRaises(s.SessionStateError):
            self.apply('budget.reconcile',id='api',dispatch_id='call1',amount=11,provenance=dict(actor='external',source_id='api',quote='11 tokens'))
        self.apply('budget.reconcile',id='api',dispatch_id='call1',amount=11,provenance=user('Verified physical usage: 11 tokens.'))
        budget=self.state['budgets']['api']
        self.assertEqual(raw,budget['spends']);self.assertEqual(11,budget['spent'])
        self.assertEqual(89,budget['remaining']);self.assertFalse(budget['unknown_spend'])
        self.assertEqual(raw[0]['revision'],budget['reconciliations'][0]['spend_revision'])
        before=copy.deepcopy(self.state)
        self.apply('budget.spend',id='api',amount=None,dispatch_id='call1')
        self.assertEqual(before,self.state)
        with self.assertRaises(s.SessionStateError):self.apply('budget.spend',id='api',amount=11,dispatch_id='call1')
        with self.assertRaises(s.SessionStateError):
            self.apply('budget.reconcile',id='api',dispatch_id='call1',amount=11,provenance=user())
        self.assertEqual(before,self.store.show())

    def test_dispatch_cannot_omit_task_budget_or_charge_unrelated_budget(self):
        for identifier in ('api','other'):
            self.apply('budget.set',id=identifier,scope='api_tokens',unit='tokens',limit=100,provenance=user())
        self.task(budget_ids=['api']);self.start(budget_ids=[])
        self.assertEqual(['api'],self.state['dispatches']['call1']['budget_ids'])
        with self.assertRaises(s.SessionStateError):self.apply('budget.spend',id='other',amount=5,dispatch_id='call1')
        self.assertEqual(0,self.store.show()['budgets']['other']['spent'])
        self.apply('budget.spend',id='api',amount=None,dispatch_id='call1')
        revision=self.state['dispatches']['call1']['dispatch_revision']
        self.apply('dispatch.finish',id='call1',dispatch_revision=revision,status='completed',result_hash='b'*64,evidence_ids=[])
        with self.assertRaises(s.SessionStateError):self.start('call2',budget_ids=[])

    def test_steering_invalidates_completed_receipt_without_erasing_physical_status(self):
        self.task();self.start();revision=self.state['dispatches']['call1']['dispatch_revision']
        self.apply('dispatch.finish',id='call1',dispatch_revision=revision,status='completed',result_hash='b'*64,evidence_ids=[])
        self.apply('request.capture',id='r1',text='Use the new requirement.',source='hook')
        row=self.state['dispatches']['call1']
        self.assertEqual('completed',row['status']);self.assertFalse(row['valid'])
        self.assertEqual('b'*64,row['result_hash'])

    def test_retired_fact_invalidates_nonderived_transitive_evidence(self):
        self.document(text='Rent: 1900\n')
        provenance=dict(actor='external',source_id='doc1',quote='Rent: 1900')
        self.fact('first',source_ids=['doc1'],provenance=provenance)
        self.fact('second',source_ids=['first'],provenance=provenance,derived=False)
        self.apply('fact.retire',id='first',provenance=user('Discard the old rental source.'))
        self.assertFalse(self.state['facts']['second']['valid'])
        self.task()
        with self.assertRaises(s.SessionStateError):
            self.apply('task.complete',id='vet',evidence_ids=['second'],based_on_revision=self.state['revision'])

    def test_nonobject_event_fails_with_public_validation_error(self):
        for invalid in (None, [], 'requirement.add'):
            with self.assertRaises(s.SessionStateError):self.store.apply(invalid,self.state['revision'])

    def test_failed_source_snapshot_publish_leaves_no_torn_blob_and_retry_succeeds(self):
        original_revision=self.state['revision']
        with mock.patch.object(s.os,'replace',side_effect=OSError('simulated disk failure')):
            with self.assertRaises(s.SessionStateError):self.document()
        self.assertEqual(original_revision,self.store.show()['revision'])
        self.assertEqual([],list(self.store.state_root.glob('object-*.txt')))
        self.assertEqual([],list(self.store.state_root.glob('.txn-*')))
        self.document()
        self.assertEqual('Rent: 1900',self.store.retrieve('doc1',start=1,end=1)['text'])

    def test_identity_marker_damage_and_malformed_checkpoint_fail_closed(self):
        self.store.checkpoint()
        checkpoint=self.store.state_root/'checkpoint.json'
        checkpoint.write_text('[]')
        with self.assertRaises(s.IntegrityError):self.store.verify()
        checkpoint.unlink()
        identity=self.store.state_root/'identity.json'
        identity.write_text('{"schema_version":1,"project_id":"wrong-project"}')
        with self.assertRaises(s.IntegrityError):self.store.show()
        identity.unlink()
        with self.assertRaises(s.IntegrityError):self.store.init('test-project')

    def test_normal_spend_preserves_completed_dependency(self):
        self.apply('budget.set',id='api',scope='api_tokens',unit='tokens',limit=100,provenance=user())
        self.task('a');self.fact();self.apply('task.complete',id='a',evidence_ids=['observation'],based_on_revision=self.state['revision'])
        self.task('vet',depends_on=['a'],budget_ids=['api']);self.start()
        self.apply('budget.spend',id='api',amount=5,dispatch_id='call1')
        self.assertEqual('completed',self.state['tasks']['a']['status']);self.assertTrue(self.state['tasks']['a']['valid'])

    def test_paused_workflow_never_unpauses_on_capture_or_requirement_change(self):
        self.requirement();self.task();self.task('flow',kind='workflow',depends_on=['vet'])
        self.apply('task.update',id='flow',changes={'status':'paused'})
        self.apply('request.capture',id='r1',text='Change the budget.',source='hook')
        self.apply('requirement.update',id='budget',changes={'value':1900},provenance=user())
        self.apply('request.resolve',id='r1',resolution='applied',note='Updated budget.')
        self.assertEqual('paused',self.state['tasks']['flow']['status'])
        with self.assertRaises(s.SessionStateError):self.start()
        self.apply('task.update',id='flow',changes={'status':'running'})
        self.start()

    def test_checkpoint_revision_is_audited_and_staleness_visible(self):
        self.requirement();checkpoint=self.store.checkpoint(max_chars=20000)
        self.assertEqual(self.state['revision'],checkpoint['revision']);self.assertTrue(self.store.verify()['checkpoint']['current'])
        self.apply('question.add',id='q',text='Optional',blocking=False)
        self.assertFalse(self.store.verify()['checkpoint']['current'])
        path=self.store.state_root/'checkpoint.json';value=json.loads(path.read_text());value['packet']['requirements']={};path.write_text(json.dumps(value))
        with self.assertRaises(s.IntegrityError):self.store.verify()


if __name__=='__main__':unittest.main()
