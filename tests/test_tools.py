from pathlib import Path
import sys,tempfile,json,copy,time,unittest,importlib.util
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));import generate as g,capacity_plan as c,claim_intent as ci
spec=importlib.util.spec_from_file_location('render',R/'adapters/nexus/render_input.py');render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=g.generate('datalife-io-monitoring','example-model');cls.snapshot=g.read(R/'profiles/nexus/capacity-example.json')
 def test_exact_budgets(self):self.assertEqual(self.plan['canonical_contract']['agent_timeout_sec'],28800);self.assertEqual(self.plan['environment_profile']['verifier_timeout_sec'],self.plan['canonical_contract']['verifier_timeout_sec'])
 def test_messages_no_tool_choice(self):
  p=g.generate('datalife-io-monitoring','example-model',protocol='anthropic_messages');b=render.render(p)['body'];self.assertNotIn('tool_choice',b['openai_clients']['main']['config']['request_args']);self.assertEqual(b['agent_config']['extra_env']['CLAUDE_CODE_EFFORT_LEVEL'],'high')
 def test_profile_mutation_rejected(self):
  with tempfile.TemporaryDirectory()as td:
   q=Path(td);(q/'canonical').symlink_to(R/'canonical',target_is_directory=True);(q/'profiles/nexus').mkdir(parents=True);(q/'profiles/LOCK.json').write_bytes((R/'profiles/LOCK.json').read_bytes());p=g.read(R/'profiles/nexus/tasks.json');p['tasks']['datalife-io-monitoring']['agent_timeout_sec']=14400;(q/'profiles/nexus/tasks.json').write_text(json.dumps(p))
   with self.assertRaises(AssertionError):g.generate('datalife-io-monitoring','example-model',root=q)
 def test_missing_hydration_refused(self):
  with self.assertRaises(AssertionError):g.generate('icon-atmosphere-checkpoint','example-model')
 def test_real_zip_roundtrip(self):
  with tempfile.TemporaryDirectory()as td:
   q=Path(td)/'out';p=g.materialize(self.plan,q);self.assertTrue(p['task_bundle']['bytes_and_file_modes_preserved']);self.assertEqual(render.render(p)['task_files']['sha256'],p['task_bundle']['sha256'])
   with self.assertRaises(AssertionError):g.materialize(self.plan,q)
 def test_all32_resource_rows(self):
  import tomllib
  p=g.read(R/'profiles/nexus/tasks.json');self.assertEqual(len(p['tasks']),32)
  for name,v in p['tasks'].items():
   cfg=tomllib.loads((R/'canonical/tasks'/name/'task.toml').read_text());self.assertEqual(v['agent_timeout_sec'],cfg['agent']['timeout_sec']);self.assertEqual(v['verifier_timeout_sec'],cfg['verifier']['timeout_sec']);self.assertEqual(v['timeout_multiplier'],1)
 def test_21_11_disjoint(self):
  q=g.read(R/'profiles/nexus/qualification.json');a=set(q['historical_cloud_route_21']);b=set(q['historical_native_route_11']);self.assertEqual((len(a),len(b),len(a&b)),(21,11,0));self.assertEqual(a|b,set(g.read(R/'canonical/manifest.json')['tasks']))
 def test_parent_manager_cost(self):
  p=c.plan_capacity([self.plan]*99,self.snapshot);self.assertEqual(p['recommended']['max_inflight'],99);self.assertEqual(p['recommended']['control_required'],{'managers':4,'cpu':10,'memory_gib':19,'slots':100,'active_batches':1})
 def test_fixed_worker_slots_not_active_items(self):
  s=copy.deepcopy(self.snapshot);s['manager_shape']['worker_slots']=13;s['control_available']['slots']=2;v=c.plan_capacity([self.plan],s);self.assertIsNone(v['recommended']);self.assertEqual(v['rejected'][0]['control_required']['slots'],14)
 def test_bad_manager_memory_ratio(self):
  s=copy.deepcopy(self.snapshot);s['manager_shape']['parent_memory_gib']=8
  with self.assertRaises(AssertionError):c.plan_capacity([self.plan],s)
 def test_zero_and_bool_inflight(self):
  for n in [0,True,False,-1]:
   with self.assertRaises(AssertionError):c.plan_capacity([self.plan],self.snapshot,n)
 def test_bool_grant_rejected(self):
  s=copy.deepcopy(self.snapshot);s['control_available']['slots']=True
  with self.assertRaises(AssertionError):c.plan_capacity([self.plan],s)
 def test_batch_quota_zero(self):
  s=copy.deepcopy(self.snapshot);s['control_available']['active_batches']=0;self.assertIsNone(c.plan_capacity([self.plan],s)['recommended'])
 def test_runtime_separate(self):
  s=copy.deepcopy(self.snapshot);s['runtime_grant']['available_gib']=0;self.assertIsNone(c.plan_capacity([self.plan],s)['recommended']);self.assertEqual(s['control_available']['managers'],5)
 def test_no_unbound_pool(self):
  s=copy.deepcopy(self.snapshot);s['runtime_grant']['token_binding']=''
  with self.assertRaises(AssertionError):c.plan_capacity([self.plan],s)
 def intent(self,scenario):
  with tempfile.TemporaryDirectory()as td:
   q=Path(td);p=q/'plan.json';p.write_text(json.dumps(self.plan));authority=q/'authority.json';authority.write_text('{}');e={'observed_epoch':time.time(),'plan_sha256s':[g.file_sha(p)],'complete_attempt_inventory':True,'capacity_and_backend_qualification_passed':True,'existing_dedup_keys':[],'authoritative_sources':[{'path':str(authority),'sha256':g.file_sha(authority)}]}
   if scenario=='stale':e['observed_epoch']-=121
   if scenario=='existing':e['existing_dedup_keys']=[self.plan['dedup_key']]
   ep=q/'admission.json';ep.write_text(json.dumps(e))
   if scenario in ['stale','existing']:
    with self.assertRaises(AssertionError):ci.claim([p],ep,q/'ledger')
    self.assertFalse((q/'ledger').exists())
   else:
    x=ci.claim([p],ep,q/'ledger');self.assertFalse(x['submitted'])
    with self.assertRaises(AssertionError):ci.claim([p],ep,q/'ledger')
 def test_intent_once(self):self.intent('once')
 def test_intent_stale(self):self.intent('stale')
 def test_intent_existing_remote(self):self.intent('existing')
if __name__=='__main__':unittest.main()
