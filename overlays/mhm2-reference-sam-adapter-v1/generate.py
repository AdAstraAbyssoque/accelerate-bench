#!/usr/bin/env python3
"""Pure local assembly of an explicitly selected source cohort; never builds/runs images."""
from pathlib import Path, PurePosixPath
import argparse,copy,gzip,hashlib,io,json,os,shutil,tarfile
D=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
sha=lambda p:H(p.read_bytes())
def load(p):return json.loads(p.read_bytes())
def inventory(root):
 result={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():raise ValueError('SymlinksNotAcceptedInTaskInput')
  if p.is_file():result[str(p.relative_to(root))]=sha(p)
  elif not p.is_dir():raise ValueError('SpecialInputNotAccepted')
 return result
def validate_package():
 pins=load(D/'package-files.json')
 for name,digest in pins.items():
  q=PurePosixPath(name)
  if q.is_absolute() or '..' in q.parts or sha(D/name)!=digest:raise ValueError('PackagePinMismatch:'+name)
 c=load(D/'cohort.json')
 for name,key in [('canonical-task-files.json','canonical_task_files_sha256'),('source-files.json','source_files_sha256')]:
  if sha(D/name)!=c[key]:raise ValueError('ManifestPinMismatch')
 return c
def corrected_archive(original,c):
 if H(original)!=c['original_source_sha256']:raise ValueError('OriginalSourceDigestMismatch')
 output=io.BytesIO();seen=set();template=None
 with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0,compresslevel=9) as gz:
  with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as out,tarfile.open(fileobj=io.BytesIO(original),mode='r:gz') as src:
   for m in src:
    q=PurePosixPath(m.name)
    if q.is_absolute() or '..' in q.parts or q.parts[0]!='mhm2' or m.name in seen or not (m.isfile() or m.isdir()):raise ValueError('UnsafeSourceMember')
    seen.add(m.name);n=copy.copy(m);data=src.extractfile(m).read() if m.isfile() else None
    if m.name=='mhm2/include/klign.hpp':
     template=copy.copy(m);data=(D/'overlay/include/klign.hpp').read_bytes();n.size=len(data)
    out.addfile(n,io.BytesIO(data) if data is not None else None)
   if template is None:raise ValueError('OriginalAdapterMissing')
   template.name='mhm2/include/reference_sam_adapter.hpp';data=(D/'overlay/include/reference_sam_adapter.hpp').read_bytes();template.size=len(data);out.addfile(template,io.BytesIO(data))
 data=output.getvalue()
 if H(data)!=c['corrected_source_sha256'] or len(data)!=c['corrected_source_bytes']:raise ValueError('CorrectedArchiveDigestMismatch')
 files={}
 with tarfile.open(fileobj=io.BytesIO(data)) as tf:
  for m in tf:
   if m.isfile():files[str(PurePosixPath(m.name).relative_to('mhm2'))]=H(tf.extractfile(m).read())
 if files!=load(D/'source-files.json')['files']:raise ValueError('CorrectedMemberDigestMismatch')
 return data
def validate_generated(root,c):
 expected=load(D/'canonical-task-files.json')
 for name in c['placements']:expected[name]=c['corrected_source_sha256']
 if inventory(root/'task')!=expected:raise ValueError('GeneratedTaskDrift')
 if sha(root/'image-context/cohort-source.tar.gz')!=c['corrected_source_sha256']:raise ValueError('GeneratedSourceDrift')
 for name,src in [('cohort-source-files.json',D/'source-files.json'),('cohort-rebuild.py',D/'images/cohort-rebuild.py'),('Dockerfile',D/'images/Dockerfile')]:
  if (root/'image-context'/name).read_bytes()!=src.read_bytes():raise ValueError('GeneratedContextDrift')
 receipt=load(root/'cohort-selection.json')
 if receipt['cohort']!=c['cohort'] or receipt['corrected_source_sha256']!=c['corrected_source_sha256']:raise ValueError('CohortRecordMismatch')
 return {'status':'GENERATED_COHORT_VERIFIED','cohort':c['cohort'],'task_files':len(expected),'changed_task_files':c['placements'],'source_archive_sha256':c['corrected_source_sha256'],'images_built':False,'model_or_judge_calls':0}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cohort',required=True);p.add_argument('--task-root',type=Path);p.add_argument('--materialize',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--validate-generated',type=Path);a=p.parse_args();c=validate_package()
 if a.cohort!=c['cohort']:raise ValueError('ExplicitKnownCohortRequired')
 if a.validate_generated:
  if a.materialize or a.task_root or a.output:raise ValueError('AmbiguousMode')
  print(json.dumps(validate_generated(a.validate_generated,c)));return
 if not a.task_root or not a.task_root.is_dir():raise ValueError('OriginalTaskRootRequired')
 if inventory(a.task_root)!=load(D/'canonical-task-files.json'):raise ValueError('CanonicalTaskMismatch')
 source=corrected_archive((a.task_root/c['placements'][0]).read_bytes(),c)
 if not a.materialize:
  if a.output:raise ValueError('OutputRequiresMaterialize')
  print(json.dumps({'status':'DRY_RUN_VALIDATED_NO_FILES_WRITTEN','cohort':c['cohort'],'source_archive_sha256':H(source),'source_bytes':len(source),'changed_task_files':c['placements'],'images_built':False,'activation':False}));return
 if not a.output:raise ValueError('NewOutputDirectoryRequired')
 output=a.output.resolve(); original=a.task_root.resolve()
 if output.is_relative_to(original) or original.is_relative_to(output) or output.is_relative_to(D):raise ValueError('OutputMustBeOutsideCanonicalAndPackage')
 # Exclusive namespace: partial failures remain visible and cannot be silently retried.
 a.output.mkdir(parents=False,exist_ok=False);context=a.output/'image-context';context.mkdir();(context/'cohort-source.tar.gz').write_bytes(source)
 for name,src in [('cohort-source-files.json',D/'source-files.json'),('cohort-rebuild.py',D/'images/cohort-rebuild.py'),('Dockerfile',D/'images/Dockerfile')]:shutil.copy2(src,context/name)
 task=a.output/'task';task.mkdir()
 for name in load(D/'canonical-task-files.json'):
  target=task/name;target.parent.mkdir(parents=True,exist_ok=True)
  if name in c['placements']:os.link(context/'cohort-source.tar.gz',target)
  else:shutil.copy2(a.task_root/name,target)
 receipt={'cohort':c['cohort'],'original_source_sha256':c['original_source_sha256'],'corrected_source_sha256':c['corrected_source_sha256'],'task_files_unchanged_except':c['placements'],'image_roles':['main','public','private'],'base_images_unresolved':c['base_images'],'source_archives_shared_by_hardlinks':True,'model_attempts_created':0,'task_toml_unmodified':True,'do_not_override_existing_attempts_or_scores':True}
 (a.output/'cohort-selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(validate_generated(a.output,c)))
if __name__=='__main__':main()
