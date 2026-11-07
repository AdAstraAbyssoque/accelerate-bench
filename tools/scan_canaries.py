#!/usr/bin/env python3
"""Scan explicitly named local text/JSONL files. Never recurse or infer training."""
import argparse,json,re,stat,uuid
from pathlib import Path
PATTERN=re.compile(r'(?<![A-Za-z0-9_])ACCELERATEBENCH_CANARY_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![A-Za-z0-9_])')
def load_markers(path):
 x=json.loads(path.read_text());assert x['schema']=='acceleratebench.publication-canaries.v1'
 known={x['release_marker']:{'scope':'release'}}
 for row in x['tasks']:
  if row['marker'] in known:raise ValueError('DuplicateMarker')
  known[row['marker']]={'scope':'task','task_id':row['task_id']}
 if len(known)!=33 or len({r['task_id']for r in x['tasks']})!=32:raise ValueError('ExpectedReleasePlus32Tasks')
 for marker in known:
  if not PATTERN.fullmatch(marker) or uuid.UUID(marker.removeprefix('ACCELERATEBENCH_CANARY_')).version!=4:raise ValueError('InvalidUUIDv4Marker')
 return known

def scan(path,known,max_bytes):
 if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):raise ValueError('ExplicitRegularFilesOnly')
 if path.stat().st_size>max_bytes:raise ValueError('FileExceedsByteLimit')
 hits=[];consumed=0
 with path.open('rb') as f:
  lineno=0
  while True:
   line=f.readline(max_bytes-consumed+1)
   if not line:break
   lineno+=1
   consumed+=len(line)
   if consumed>max_bytes:raise ValueError('FileGrewBeyondByteLimit')
   # byte-limit includes arbitrarily long lines; only decode already bounded data.
   for m in PATTERN.finditer(line.decode('utf-8')):
    marker=m.group();hits.append({'line':lineno,'marker':marker,'recognized':marker in known,**known.get(marker,{'scope':'unknown'})})
 return {'file':str(path),'bytes_read':consumed,'match_count':len(hits),'matches':hits}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--max-bytes',type=int,default=64*1024**2);p.add_argument('files',type=Path,nargs='+');a=p.parse_args()
 if a.max_bytes<=0:p.error('--max-bytes must be positive')
 known=load_markers(a.manifest);result={'interpretation':'Marker text presence only; not evidence of training, memorization or cheating.','files':[],'errors':[]}
 for path in a.files:
  try:result['files'].append(scan(path,known,a.max_bytes))
  except (OSError,ValueError,UnicodeError) as e:result['errors'].append({'file':str(path),'error_type':type(e).__name__})
 result['match_count']=sum(x['match_count']for x in result['files']);print(json.dumps(result,ensure_ascii=False,indent=2));return 2 if result['errors']else 0
if __name__=='__main__':raise SystemExit(main())
