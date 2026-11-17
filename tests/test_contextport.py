"""Synthetic offline regression suite; no accounts, credentials or network calls."""
import unittest,tempfile,sys,json,copy,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contextport.core import plan,inspect,verify,load,conversations

def sample():
 def n(id,parent,children,text=None,role='user',parts=None):return {'id':id,'parent':parent,'children':children,'message':None if text is None else {'author':{'role':role},'content':{'content_type':'text','parts':parts if parts is not None else [text]}}}
 return {'id':'synthetic-1','title':'Synthetic example, not a real user conversation','current_node':'a2','mapping':{'root':n('root',None,['u1']),'u1':n('u1','root',['a1'],'Use Python. Keep data local.'),'a1':n('a1','u1',['u2','alternate'],'Understood.','assistant'),'u2':n('u2','a1',['a2'],'Make a CSV parser.',parts=['Make a CSV parser.',{'asset_pointer':'file-service://missing-synthetic.csv'}]),'a2':n('a2','u2',[],'Use csv.DictReader.','assistant'),'alternate':n('alternate','a1',[],'Use JavaScript instead.')}}
class Tests(unittest.TestCase):
 def test_boolean_numeric_tamper(self):
  c=sample();c['mapping']['a2']['message']['content']['parts']=['x'];b=plan(c,1)
  self.assertEqual(b['selected_text_characters'],1)
  for value in [True,1.0]:
   changed=copy.deepcopy(b);changed['selected_text_characters']=value
   self.assertRaises(ValueError,verify,c,changed)
 def test_boolean_budget_tamper(self):
  c=sample();c['mapping']['a2']['message']['content']['parts']=['x'];b=plan(c,1);b['budget_characters']=True
  self.assertRaises(ValueError,verify,c,b)
 def test_fifo_rejected_without_blocking(self):
  if not hasattr(os,'mkfifo'):self.skipTest('FIFO not available')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fifo';os.mkfifo(p)
   run=subprocess.run([sys.executable,'-m','contextport','audit',str(p),'--conversation','x'],cwd=ROOT,capture_output=True,text=True,timeout=2)
   self.assertEqual(run.returncode,2);self.assertIn('regular file',run.stderr)
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'source';source.write_text('[]');link=Path(d)/'link'
   try:link.symlink_to(source)
   except OSError:self.skipTest('Symlinks unavailable')
   self.assertRaises(ValueError,load,link)
 def test_private_error_details_never_echoed(self):
  secret='PRIVATE_SECRET_SENTINEL'
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'source.json'
   c=sample();c['mapping'][secret]=c['mapping'].pop('u1');c['mapping'][secret]['id']=secret;c['mapping'][secret]['parent']='missing'
   inputs=['{"'+secret+'":1,"'+secret+'":2}',json.dumps([c]),b'"\xffPRIVATE_SECRET_SENTINEL"']
   for data in inputs:
    path.write_bytes(data if isinstance(data,bytes) else data.encode())
    run=subprocess.run([sys.executable,'-m','contextport','audit',str(path),'--conversation','synthetic-1'],cwd=ROOT,capture_output=True,text=True)
    self.assertEqual(run.returncode,2);self.assertNotIn(secret,run.stderr);self.assertNotIn('Traceback',run.stderr)
   missing=Path(d)/secret
   run=subprocess.run([sys.executable,'-m','contextport','audit',str(missing),'--conversation','x'],cwd=ROOT,capture_output=True,text=True)
   self.assertNotIn(secret,run.stderr)
 def test_nonfinite_json_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input.json';p.write_text('[NaN]');self.assertRaises(ValueError,load,p)
 def test_exponent_overflow_cli_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source.json'
   for value in ['1e999','-1e999']:
    raw=json.dumps([sample()]);raw=raw.replace('"title":', '"extra": {"metadata": ['+value+']}, "title":',1);p.write_text(raw)
    run=subprocess.run([sys.executable,'-m','contextport','audit',str(p),'--conversation','synthetic-1'],cwd=ROOT,capture_output=True,text=True,timeout=2)
    self.assertEqual(run.returncode,2);self.assertIn('Non-finite JSON',run.stderr);self.assertNotIn('Traceback',run.stderr)
 def test_canonical_rejects_nonfinite_direct_values(self):
  from contextport.core import canonical
  for value in [float('inf'),float('-inf'),float('nan')]:self.assertRaises(ValueError,canonical,{'nested':[value]})
 def test_plan_verify(self):self.assertTrue(verify(sample(),plan(sample()))['verified'])
 def test_every_node(self):self.assertEqual(len(plan(sample())['coverage']),6)
 def test_active_branch(self):self.assertEqual([m['node_id'] for m in plan(sample())['messages']],['u1','a1','u2','a2'])
 def test_alternate_explicit(self):self.assertEqual(next(x for x in plan(sample())['coverage'] if x['node_id']=='alternate')['disposition'],'off-branch')
 def test_assets_warn(self):self.assertIn('non-text-part:1',next(x for x in plan(sample())['coverage'] if x['node_id']=='u2')['warnings'])
 def test_budget_whole_message(self):self.assertEqual([m['node_id'] for m in plan(sample(),20)['messages']],['a2'])
 def test_pins(self):self.assertEqual([m['node_id'] for m in plan(sample(),50,['u1'])['messages']],['u1','a2'])
 def test_pin_budget_error(self):self.assertRaises(ValueError,plan,sample(),5,['u1'])
 def test_offbranch_pin_error(self):self.assertRaises(ValueError,plan,sample(),100,['alternate'])
 def test_missing_current(self):c=sample();c.pop('current_node');self.assertRaises(ValueError,plan,c)
 def test_cycle(self):c=sample();c['mapping']['root']['parent']='a2';c['mapping']['a2']['children']=['root'];self.assertRaises(ValueError,plan,c)
 def test_missing_parent(self):c=sample();c['mapping']['u1']['parent']='absent';self.assertRaises(ValueError,plan,c)
 def test_child_mismatch(self):c=sample();c['mapping']['root']['children']=[];self.assertRaises(ValueError,plan,c)
 def test_malformed_child(self):c=sample();c['mapping']['a1']=1;self.assertRaises(ValueError,plan,c)
 def test_changed_bundle(self):c=sample();b=plan(c);b['messages'][0]['text']='Changed';self.assertRaises(ValueError,verify,c,b)
 def test_changed_source(self):c=sample();b=plan(c);c['mapping']['alternate']['message']['content']['parts']=['changed'];self.assertRaises(ValueError,verify,c,b)
 def test_dropped_coverage(self):c=sample();b=plan(c);b['coverage'].pop();self.assertRaises(ValueError,verify,c,b)
 def test_duplicate_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{"a":1,"a":2}');self.assertRaises(ValueError,load,p)
 def test_deep_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('['*10000+'0'+']'*10000);self.assertRaises(ValueError,load,p)
 def test_duplicate_conversation(self):self.assertRaises(ValueError,conversations,[sample(),sample()])
 def test_cli_roundtrip_report_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'source.json';bundle=Path(d)/'bundle.json';report=Path(d)/'report.html';source.write_text(json.dumps([sample()]))
   def run(*args):return subprocess.run([sys.executable,'-m','contextport',*map(str,args)],cwd=ROOT,capture_output=True,text=True)
   self.assertEqual(run('pack',source,'--conversation','synthetic-1','--out',bundle).returncode,0)
   self.assertEqual(run('verify',source,bundle,'--conversation','synthetic-1').returncode,0)
   self.assertEqual(run('pack',source,'--conversation','synthetic-1','--out',bundle).returncode,2)
   self.assertEqual(run('report',source,'--conversation','synthetic-1','--out',report).returncode,0)
   self.assertIn('off-branch',report.read_text())
if __name__=='__main__':unittest.main(verbosity=2)
