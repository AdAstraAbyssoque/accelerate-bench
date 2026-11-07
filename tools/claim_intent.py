#!/usr/bin/env python3
"""Local durable dedup handoff, not a batch launcher. Default previews only."""
if not __debug__:raise RuntimeError('Validation must not be disabled with Python optimization')
from pathlib import Path
import argparse,json,os,time,fcntl
from generate import digest,file_sha,read

def key(plan):
 i=plan['identity'];value={k:i[k]for k in ['model_id','task_id','task_source_sha256','environment_profile_sha256','backend']};assert digest(value)==plan['dedup_key'],'DedupIdentityMismatch';return plan['dedup_key']
def claim(plans,evidence,ledger,now=None):
 now=time.time()if now is None else now;objects=[read(p)for p in plans];keys=[key(p)for p in objects];assert len(set(keys))==len(keys),'DuplicateBatchCell'
 e=read(evidence);assert 0<=now-e['observed_epoch']<=120,'StaleAdmission';assert e['complete_attempt_inventory']is True and e['capacity_and_backend_qualification_passed']is True
 assert e['plan_sha256s']==[file_sha(p)for p in plans],'AdmissionPlanMismatch';assert e['authoritative_sources'],'MissingAuthoritySources'
 for v in e['authoritative_sources']:assert file_sha(Path(v['path']))==v['sha256'],'AuthoritySourceChanged'
 assert set(keys).isdisjoint(e['existing_dedup_keys']),'ExistingAttemptConflict'
 ledger.mkdir(parents=True,exist_ok=True)
 with(ledger/'lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for p in ledger.glob('*.intent.json'):assert set(keys).isdisjoint(read(p)['dedup_keys']),'PermanentIntentConflict'
  batch=digest(keys);dest=ledger/(batch+'.intent.json');doc={'schema':'acceleratebench.permanent-batch-intent.v1','dedup_keys':keys,'plan_sha256s':e['plan_sha256s'],'admission_sha256':file_sha(evidence),'created_epoch':now,'attempt_count':1,'automatic_retry':False,'submission_status':'not_submitted_by_this_tool'}
  with dest.open('x')as f:json.dump(doc,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  fd=os.open(ledger,os.O_RDONLY);os.fsync(fd);os.close(fd)
 return {'intent':str(dest),'intent_sha256':file_sha(dest),'submitted':False,'replay_allowed':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plans',type=Path,nargs='+',required=True);p.add_argument('--claim',action='store_true');p.add_argument('--admission-evidence',type=Path);p.add_argument('--ledger',type=Path);a=p.parse_args()
 if not a.claim:print(json.dumps({'dedup_keys':[key(read(v))for v in a.plans],'intent_created':False,'submitted':False}));return
 assert a.admission_evidence and a.ledger;print(json.dumps(claim(a.plans,a.admission_evidence,a.ledger),indent=2))
if __name__=='__main__':main()
