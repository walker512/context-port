"""Synthetic human-edited handoff tests; no model or destination platform."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from contextport import core,briefing
ROOT=Path(__file__).resolve().parents[1]
def conv():return json.loads((ROOT/'examples/synthetic.json').read_bytes())[0]
def spec(c):
    out=briefing.template(c);out['cards']=[{'id':'local-only','kind':'fact','text':'The user requires local processing.','human_confirmed':True,'references':[{'node_id':'u1','start':12,'end':28}]},{'id':'parser','kind':'goal','text':'Build a CSV parser.','human_confirmed':False,'references':[{'node_id':'u2','start':0,'end':18}]},{'id':'implementation','kind':'todo','text':'Evaluate the suggested standard-library parser.','human_confirmed':False,'references':[{'node_id':'a2','start':0,'end':19}]}];return out
class BriefingTests(unittest.TestCase):
 def setUp(self):self.c=conv();self.s=spec(self.c)
 def test_cards_exact_sources_and_omissions(self):
    b=briefing.build(self.c,self.s);self.assertTrue(briefing.verify(self.c,b)['verified']);self.assertEqual(b['cards'][0]['citations'][0]['quote'],'Keep data local.');self.assertTrue(all(not c['semantic_support_verified'] for c in b['cards']));self.assertEqual(next(r for r in b['selection']['coverage'] if r['node_id']=='alternate')['disposition'],'off-branch')
 def test_edit_human_text_rebuild_not_auto_fact_check(self):
    self.s['cards'][0]['text']='An intentionally unsupported human assertion.';b=briefing.build(self.c,self.s);self.assertTrue(briefing.verify(self.c,b)['verified']);self.assertFalse(b['cards'][0]['semantic_support_verified'])
 def test_unselected_reference_requires_pin_or_budget(self):
    with self.assertRaises(core.PortError):briefing.build(self.c,self.s,20)
    s=spec(self.c);s['cards']=s['cards'][:1];b=briefing.build(self.c,s,50,['u1']);self.assertIn('u1',[m['node_id'] for m in b['selection']['messages']])
 def test_offbranch_reference_never_pin_repaired(self):
    self.s['cards'][0]['references']=[{'node_id':'alternate','start':0,'end':3}]
    with self.assertRaises(core.PortError):briefing.build(self.c,self.s)
    with self.assertRaises(core.PortError):briefing.build(self.c,self.s,1000,['alternate'])
 def test_source_revision_rejects_old_spec(self):
    self.c['title']='Changed title'
    with self.assertRaises(core.PortError):briefing.build(self.c,self.s)
 def test_invalid_ranges_and_exact_types(self):
    for start,end in [(True,3),(0,False),(0,3.0),(-1,3),(2,2),(0,99999)]:
      s=copy.deepcopy(self.s);s['cards'][0]['references'][0].update(start=start,end=end)
      with self.assertRaises(core.PortError):briefing.build(self.c,s)
 def test_confirmation_kind_and_duplicates(self):
    for mutate in (lambda s:s['cards'][0].update(human_confirmed=False),lambda s:s['cards'][0].update(human_confirmed=1),lambda s:s['cards'][1].update(human_confirmed=True),lambda s:s['cards'][0].update(kind='verified'),lambda s:s['cards'].append(s['cards'][0]),lambda s:s['cards'][0]['references'].append(s['cards'][0]['references'][0]),lambda s:s.update(schema=True)):
      s=copy.deepcopy(self.s);mutate(s)
      with self.assertRaises(core.PortError):briefing.build(self.c,s)
 def test_bundle_quote_text_and_coverage_tampering(self):
    b=briefing.build(self.c,self.s)
    for mutate in (lambda x:x['cards'][0]['citations'][0].update(quote='fake'),lambda x:x['cards'][0].update(human_confirmed=1),lambda x:x['cards'][0].update(human_text='edited without rebuild'),lambda x:x['selection']['coverage'].pop(),lambda x:x.update(scope='safe')):
      changed=copy.deepcopy(b);mutate(changed)
      with self.assertRaises(core.PortError):briefing.verify(self.c,changed)
 def test_markdown_markup_and_control_escaped(self):
    self.s['cards'][0]['text']='[click](https://example.invalid) ![img](x) <script>\n# new';s=briefing.markdown(self.c,briefing.build(self.c,self.s));self.assertNotIn('<script>',s);self.assertNotIn('[click]',s);self.assertNotIn('\n# new',s);self.assertIn('&#10;',s)
 def test_unicode_indices_codepoints(self):
    self.c['mapping']['u1']['message']['content']['parts']=['甲🙂乙'];s=briefing.template(self.c);s['cards']=[{'id':'u','kind':'goal','text':'Synthetic unicode','human_confirmed':False,'references':[{'node_id':'u1','start':1,'end':2}]}];b=briefing.build(self.c,s);self.assertEqual(b['cards'][0]['citations'][0]['quote'],'🙂')
 def test_empty_template_not_exported_as_finished(self):
    self.assertEqual(briefing.template(self.c)['cards'],[])
    with self.assertRaises(core.PortError):briefing.build(self.c,briefing.template(self.c))
 def test_bounds_and_unknown_fields(self):
    for mutate in (lambda s:s.update(secret='PRIVATE'),lambda s:s['cards'][0].update(text='x'*4001),lambda s:s['cards'][0].update(references=[]),lambda s:s['cards'][0].update(text='\ud800')):
      s=copy.deepcopy(self.s);mutate(s)
      with self.assertRaises(core.PortError):briefing.build(self.c,s)
 def test_write_fixed_utf8_lf_exclusive(self):
    with tempfile.TemporaryDirectory() as t:
      p=Path(t)/'out';briefing.write_new(p,'甲\n');self.assertEqual(p.read_bytes(),'甲\n'.encode())
      with self.assertRaises(FileExistsError):briefing.write_new(p,'changed')
 def test_output_bound_before_creation(self):
    with tempfile.TemporaryDirectory() as t:
      p=Path(t)/'out'
      with self.assertRaises(core.PortError):briefing.write_new(p,'<'*(briefing.LIMIT+1))
      self.assertFalse(p.exists())
 def test_large_unicode_bundle_preflight(self):
    self.c['mapping']['a2']['message']['content']['parts']=['🙂'*1000000];s=briefing.template(self.c);s['cards']=[{'id':str(i),'kind':'todo','text':'Check this','human_confirmed':False,'references':[{'node_id':'a2','start':0,'end':4000}]} for i in range(100)]
    with self.assertRaises(core.PortError):briefing.build(self.c,s,1000000)
 def test_markdown_expansion_is_controlled(self):
    self.c['mapping']['a2']['message']['content']['parts']=['<'*20000];s=briefing.template(self.c)
    s['cards']=[{'id':str(i),'kind':'todo','text':'<'*4000,'human_confirmed':False,'references':[{'node_id':'a2','start':j*4000,'end':(j+1)*4000} for j in range(5)]} for i in range(100)]
    b=briefing.build(self.c,s,30000);self.assertTrue(briefing.verify(self.c,b)['verified'])
    with self.assertRaises(core.PortError):briefing.markdown(self.c,b)
 def test_real_cli_all_commands_and_private_failure(self):
    with tempfile.TemporaryDirectory() as t:
      p=Path(t);src=p/'source';src.write_text(json.dumps([self.c]));s=p/'spec';s.write_bytes(core.canonical(self.s).encode());out=p/'brief.json'
      commands=[['brief-template',str(src),'--out',str(p/'template')],['brief-build',str(src),str(s),'--out',str(out)],['brief-verify',str(src),str(out)],['brief-text',str(src),str(out),'--out',str(p/'handoff.md')]]
      for command in commands:
       r=subprocess.run([sys.executable,'-m','contextport',*command,'--conversation','synthetic-1'],cwd=ROOT,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
      self.assertIn('Human-authored', (p/'handoff.md').read_text())
      bad=copy.deepcopy(self.s);bad['cards'][0]['references'][0]['node_id']='PRIVATE_SECRET';s.write_text(json.dumps(bad));r=subprocess.run([sys.executable,'-m','contextport','brief-build',str(src),str(s),'--conversation','synthetic-1','--out',str(p/'bad')],cwd=ROOT,capture_output=True);self.assertEqual(r.returncode,2);self.assertNotIn(b'PRIVATE_SECRET',r.stderr);self.assertFalse((p/'bad').exists())
