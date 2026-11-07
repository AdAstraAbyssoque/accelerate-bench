#!/usr/bin/env python3
"""Generate a local, source-bound execution descriptor; never submit or resolve secrets."""
if not __debug__:raise RuntimeError('Validation must not be disabled with Python optimization')
from pathlib import Path
import argparse,json,hashlib,os,tomllib,zipfile,importlib.util
import yaml
ROOT=Path(__file__).resolve().parents[1]
def canonical_bytes(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return hashlib.sha256(canonical_bytes(x)).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  while b:=f.read(1024**2):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def task_contract(task,root=ROOT):
 manifest=read(root/'canonical/manifest.json');assert task in manifest['tasks'],'UnknownTask'
 source=root/'canonical/tasks'/task;records=[x for x in manifest['files']if x['path'].startswith(task+'/')];expected={x['path'].split('/',1)[1]:x for x in records}
 actual={str(p.relative_to(source))for p in source.rglob('*')if p.is_file()or p.is_symlink()};assert actual==set(expected),'MissingHydrationOrUnexpectedSourceFile'
 for name,row in expected.items():
  p=source/name;assert not p.is_symlink()and p.stat().st_size==row['size_bytes']and file_sha(p)==row['sha256']and p.stat().st_mode&0o7777==row['mode'],'CanonicalSourceChanged'
 
 for name,mode in manifest['directory_modes'].items():
  if name==task or name.startswith(task+'/'):assert (root/'canonical/tasks'/name).stat().st_mode&0o7777==mode,'CanonicalDirectoryModeChanged'
 cfg=tomllib.loads((source/'task.toml').read_text());assert cfg['agent']['timeout_sec']==28800 and cfg['verifier']['environment_mode']=='separate'
 compose=yaml.safe_load((source/'environment/docker-compose.yaml').read_text());services=compose.get('services',{});public=services.get('public-judge')
 contract={'task_id':task,'task_version':cfg['task']['version'],'source_version':manifest['source_version'],'source_sha256':digest([{k:r[k]for k in ['path','sha256','size_bytes','mode']}for r in records]),'agent_timeout_sec':28800,'verifier_timeout_sec':cfg['verifier']['timeout_sec'],'main':cfg['environment'],'private':cfg['verifier']['environment'],'public':{k:public[k]for k in ['cpus','mem_limit','network_mode']if k in public}if public else None,'canonical_file_count':len(records)}
 return contract,source,expected

def generate(task,model,backend='nexus',protocol='openai_chat',wire_model=None,root=ROOT):
 assert model and len(model)<=200 and not any(c.isspace()for c in model),'InvalidModelID'
 assert protocol in ['openai_chat','anthropic_messages'];contract,source,files=task_contract(task,root)
 profile_path='profiles/nexus/tasks.json'if backend=='nexus'else'profiles/native/profile.json';locks=read(root/'profiles/LOCK.json')['files'];assert file_sha(root/profile_path)==locks[profile_path],'UnreviewedProfileChange';profile=read(root/profile_path)
 if backend=='nexus':
  assert set(profile)=={'schema','profile_id','task_source_mutation_allowed','network_policy','archive_policy','tasks'}and profile['task_source_mutation_allowed']is False,'UnsupportedProfileMutation'
  cfg=profile['tasks'][task];allowed={'outer_resources','shared_main_public_cpu_budget','runner_timeout_sec','agent_timeout_sec','verifier_timeout_sec','timeout_multiplier','images','qualification','compatibility_profile','inner_hard_limits_proven'}
  assert set(cfg)==allowed and cfg['compatibility_profile']=='none','ExplicitVersionedCompatibilityRequired'
  assert cfg['agent_timeout_sec']==contract['agent_timeout_sec'] and cfg['verifier_timeout_sec']==contract['verifier_timeout_sec'] and cfg['timeout_multiplier']==1,'ScientificBudgetOverrideRejected'
  assert cfg['runner_timeout_sec']>=28800+contract['verifier_timeout_sec'] and cfg['inner_hard_limits_proven']is False
  assert set(cfg['outer_resources'])=={'main','verifier'}
  for role,values in cfg['outer_resources'].items():assert set(values)=={'cpu','memory'}and all(type(v)is int and v>0 for v in values.values())
  assert cfg['images']=={'runtime_worker_overlay':{'environment_variable':'AB_NEXUS_RUNTIME_IMAGE'},'controller_base':{'environment_variable':'AB_NEXUS_BASE_IMAGE'}},'ImageRoleBindingsChanged'
 else:cfg=profile;assert backend=='native'
 env_sha=digest(profile)
 identity={'model_id':model,'wire_model':wire_model or model,'protocol':protocol,'task_id':task,'task_source_sha256':contract['source_sha256'],'environment_profile_sha256':env_sha,'backend':backend}
 # Logical identity intentionally excludes retry labels/batch names. A changed cohort must
 # be explicit, and does not erase original attempt history or permit best-score selection.
 dedup={k:identity[k]for k in ['model_id','task_id','task_source_sha256','environment_profile_sha256','backend']}
 qualification=read(root/'profiles/nexus/qualification.json');blocked=next((x for x in qualification['blocked_11']if x['task_id']==task),None)
 return {'backend_qualification_scope':{'historical_route':'P1'if blocked else'Cloud','blocking_class':blocked['class']if blocked else None,'new_tuple_qualification_required':True},'schema':'acceleratebench.execution-descriptor.v1','identity':identity,'dedup_key':digest(dedup),'canonical_contract':contract,'environment_profile':cfg,'environment_profile_id':profile['profile_id'],'provider_environment':{'api_key':'ANTHROPIC_API_KEY'if protocol=='anthropic_messages'else'OPENAI_API_KEY','base_url':'ANTHROPIC_BASE_URL'if protocol=='anthropic_messages'else'OPENAI_BASE_URL','runtime_token':'NEXUS_RUNTIME_TOKEN','control_environment':'NEXUS_CONTROL_ENV','runtime_grant_binding':'NEXUS_RUNTIME_GRANT_BINDING'},'agent':{'name':'claude-code','version':'2.1.265','reasoning_effort':'high','timeout_sec':28800},'attempt_policy':{'max_attempts':1,'automatic_retries':0,'resume':False},'dry_run':True,'execution_ready':False,'blocking_requirements':['exact source and worker implementation pins','resolved role images and token-bound Runtime grant','fresh complete owner quota and attempt dedup','full-chain qualification for selected backend/source/compatibility','single durable intent in the deployment ledger'],'submission_implemented_here':False}

def materialize(plan,out,root=ROOT):
 assert not out.exists(),'FreshOutputRequired';out.mkdir(parents=True);task=plan['identity']['task_id'];_,source,files=task_contract(task,root)
 with zipfile.ZipFile(out/'task.zip','x',compression=zipfile.ZIP_DEFLATED)as z:
  directories={n.split('/',1)[1]+'/':mode for n,mode in read(root/'canonical/manifest.json')['directory_modes'].items()if n.startswith(task+'/')}
  for name,mode in sorted(directories.items()):
   info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=((0o040000|mode)<<16)|0x10;z.writestr(info,b'')
  for name,row in sorted(files.items()):
   info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=(0o100000|row['mode'])<<16;info.compress_type=zipfile.ZIP_DEFLATED
   with(source/name).open('rb')as src,z.open(info,'w')as dest:
    while b:=src.read(1024**2):dest.write(b)
 # Bytes and modes preserved. ZIP timestamps normalized; no task source or judge rewrite.
 with zipfile.ZipFile(out/'task.zip')as z:
  assert set(z.namelist())==set(files)|set(directories)
  for info in z.infolist():
   if info.is_dir():assert (info.external_attr>>16)&0o7777==directories[info.filename]
   else:assert hashlib.sha256(z.read(info)).hexdigest()==files[info.filename]['sha256']and (info.external_attr>>16)&0o7777==files[info.filename]['mode']
 result=dict(plan);result['task_bundle']={'path':'task.zip','sha256':file_sha(out/'task.zip'),'size':(out/'task.zip').stat().st_size,'format':'zip','timestamps':'1980 normalized','bytes_and_file_modes_preserved':True}
 with(out/'plan.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--task',required=True);p.add_argument('--model',required=True);p.add_argument('--wire-model');p.add_argument('--backend',choices=['native','nexus'],default='nexus');p.add_argument('--protocol',choices=['openai_chat','anthropic_messages'],default='openai_chat');p.add_argument('--output',type=Path);a=p.parse_args();v=generate(a.task,a.model,a.backend,a.protocol,a.wire_model)
 if a.output:v=materialize(v,a.output)

 if a.backend=='nexus':
  spec=importlib.util.spec_from_file_location('nexus_render',ROOT/'adapters/nexus/render_input.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);v['nexus_sdk_input_template']=module.render(v)
  if a.output:
   with(a.output/'nexus-input.template.json').open('x')as f:json.dump(v['nexus_sdk_input_template'],f,indent=2);f.write('\n')
 print(json.dumps(v,indent=2))
if __name__=='__main__':main()
