"""One-time source-syntax scope check for the final two repairs. Run at repo root."""
import sys,json,tempfile,re,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from native import host
sys.path.insert(0,'tools/robustness');from evaluate import revision
assert revision() == 'd386e72fa109808d093cc1b0d8658f12453714db2790d77ff3c5e0a720fd551d', 'This scope check is pinned to revision 04.'
base=Path('.verification/robustness');report={'from_revision':json.load(open('docs/verification/robustness-final-freeze.json'))['code_revision'],'to_revision':revision(),'changes':['leading shared subfigure captions','implicit scientific-notation coefficient'],'papers':{}}
for group,download_file in [('sample',base/'downloads.json'),('historical',base/'historical/downloads.json')]:
 for id,record in json.loads(download_file.read_text()).items():
  hits=[]
  try:
   with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);payload=Path(record['directory'])/'source';host.extract_source(payload,d)
    for p in d.rglob('*.tex'):
     text=host._read_tex_preserving_bytes(p);_,n=host._preserve_subfigure_group_captions(text)
     if n:hits.append({'file':str(p.relative_to(d)),'subfigure_groups':n})
     if re.search(host._TEX_COMMAND_PREFIX+r'(?:SI|qty|num)\s*\{[Ee][+-]?\d+\}',host._searchable_tex_source(text)):hits.append({'file':str(p.relative_to(d)),'implicit_coefficient':True})
    state='rerun' if hits else 'no_affected_construct'
  except Exception as e:state='source_unavailable';hits=[{'error':str(e)}]
  report['papers'][id]={'group':group,'status':state,'matches':hits}
  print(id,state,flush=True)
(base/'affected-04.json').write_text(json.dumps(report,indent=2)+'\n')
