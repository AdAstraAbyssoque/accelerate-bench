#!/usr/bin/env python3
"""Pure arithmetic admission plan. No quota lookup, pooling, reservation or submission."""
if not __debug__:raise RuntimeError('Validation must not be disabled with Python optimization')
import argparse,json,math
from pathlib import Path

def plan_capacity(tasks,snapshot,max_inflight=None):
 assert tasks and snapshot['complete']is True,'IncompleteOwnerSnapshot'
 assert isinstance(snapshot['environment'],str)and snapshot['environment'];assert snapshot['runtime_grant']['token_binding'],'RuntimeGrantNotTokenBound'
 control=snapshot['control_available'];assert set(control)=={'managers','cpu','memory_gib','slots','active_batches'}
 for x in control.values():assert type(x)is int and x>=0
 runtime=snapshot['runtime_grant'];assert type(runtime['available_gib'])in [int,float]and math.isfinite(runtime['available_gib'])and runtime['available_gib']>=0
 reserved=snapshot['reserved_runtime_gib'];assert type(reserved)in [int,float]and math.isfinite(reserved)and reserved>=0
 shape=snapshot['manager_shape'];assert set(shape)=={'worker_slots','worker_cpu','worker_memory_gib','parent_cpu','parent_memory_gib'}and all(type(x)is int and x>0 for x in shape.values())
 assert shape['worker_memory_gib']<=4*shape['worker_cpu'] and shape['parent_memory_gib']<=4*shape['parent_cpu'],'ManagerMemoryCpuRatioExceeded'
 assert max_inflight is None or(type(max_inflight)is int and max_inflight>0),'PositiveIntegerMaxInflightRequired'
 peaks=[]
 for t in tasks:
  o=t['environment_profile']['outer_resources'];assert set(o)=={'main','verifier'};peaks.append(sum(o[r]['memory']for r in o))
 limit=min(len(tasks),len(tasks)if max_inflight is None else max_inflight);assert limit>0
 feasible=[];rejected=[]
 for n in range(1,limit+1):
  workers=math.ceil(n/shape['worker_slots']);required={'managers':workers+1,'cpu':workers*shape['worker_cpu']+shape['parent_cpu'],'memory_gib':workers*shape['worker_memory_gib']+shape['parent_memory_gib'],'slots':workers*shape['worker_slots']+1,'active_batches':1};runtime_required=sum(sorted(peaks,reverse=True)[:n])+reserved;why=[k for k,v in required.items()if v>control[k]]
  if runtime_required>runtime['available_gib']:why.append('runtime_memory_gib')
  row={'max_inflight':n,'worker_count':workers,'control_required':required,'runtime_peak_plus_reservations_gib':runtime_required}
  if why:rejected.append({**row,'insufficient':why})
  else:feasible.append(row)
 return {'environment':snapshot['environment'],'runtime_token_binding':runtime['token_binding'],'recommended':feasible[-1]if feasible else None,'rejected':rejected,'resource_semantics':'Outer Runtime requests; main+public share their outer CPU budget. Inner hard CPU/memory limits are not asserted. Main+private memory conservatively summed. Control parent manager included.','other_environment_grants_pooled':False,'freshness_and_actual_admission_not_established_by_arithmetic':True,'submitted':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plans',type=Path,nargs='+',required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--max-inflight',type=int);a=p.parse_args();print(json.dumps(plan_capacity([json.loads(p.read_text())for p in a.plans],json.loads(a.snapshot.read_text()),a.max_inflight),indent=2))
if __name__=='__main__':main()
