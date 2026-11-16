"""Image-local only: original role base, corrected pristine source, original build."""
from pathlib import Path,PurePosixPath
import tarfile,json,hashlib,shutil,subprocess,sys,os
role=sys.argv[1];assert role in ['main','public','private'];source=Path('/tmp/cohort-source.tar.gz');pins=json.loads(Path('/tmp/cohort-source-files.json').read_text());h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert h(source)==pins['archive_sha256'];S=Path('/opt/mhm2-source');B=Path('/opt/mhm2-build')
for p in [S,B]:shutil.rmtree(p)
S.mkdir()
with tarfile.open(source)as t:
 seen=set()
 for m in t:
  parts=PurePosixPath(m.name).parts;assert parts[0]=='mhm2'and '..'not in parts and not m.name.startswith('/')and m.name not in seen and(m.isdir()or m.isfile());seen.add(m.name);p=S.joinpath(*parts[1:])
  if m.isdir():p.mkdir(parents=True,exist_ok=True)
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
  p.chmod(m.mode);os.chown(p,m.uid,m.gid);os.utime(p,(m.mtime,m.mtime))
actual={str(p.relative_to(S)):h(p)for p in S.rglob('*')if p.is_file()};assert actual==pins['files'];subprocess.run(['cp','-a',str(S),str(B)],check=True);subprocess.run(['bash','build_application.sh'],cwd=B,env={**os.environ,'JOBS':'4','UPCXX_NETWORK':'smp','UPCXX_CODEMODE':'O3'},timeout=2400,check=True)
if role=='main':
 shutil.rmtree('/app/mhm2');subprocess.run(['cp','-a',str(S),'/app/mhm2'],check=True);subprocess.run(['chown','-R','root:root','/app/mhm2'],check=True)
else:
 target=Path('/opt/judge'if role=='public'else'/tests')/'mhm2-source.tar.gz';shutil.copyfile(source,target);target.chmod(0o600);S.chmod(0o700);B.chmod(0o700)
stamp={'cohort':'mhm2-reference-sam-adapter-v1','role':role,'archive_sha256':h(source),'source_files':actual,'ELF_sha256':h(B/'build/bin/mhm2'),'launcher_sha256':h(B/'build/bin/mhm2.py'),'build_timeout':2400,'new_model_calls':0}
Path('/opt/accelerate-mhm2-adapter-cohort.json').write_text(json.dumps(stamp,sort_keys=True)+'\n');print(json.dumps({'cohort_build_proof':stamp},sort_keys=True));source.unlink();Path('/tmp/cohort-source-files.json').unlink();Path('/tmp/cohort-rebuild.py').unlink()
