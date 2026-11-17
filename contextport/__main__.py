import argparse,json,sys,html
from pathlib import Path
from .core import load,conversations,inspect,plan,verify,PortError

def write_new(path,text):
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(text)

def main():
    p=argparse.ArgumentParser(description='Inspect and plan a traceable local ChatGPT text handoff; never upload or import.')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['audit','pack','verify','report']:
        q=sub.add_parser(name);q.add_argument('input');q.add_argument('--conversation',required=True)
        if name in {'pack','report'}:q.add_argument('--budget',type=int,default=12000);q.add_argument('--pin',action='append',default=[]);q.add_argument('--out',required=True)
        if name=='verify':q.add_argument('bundle')
    args=p.parse_args()
    try:
        conv=conversations(load(args.input)).get(args.conversation)
        if conv is None:raise ValueError('Conversation ID not found.')
        if args.command=='audit':
            result=inspect(conv);result={'source_sha256':result['source_sha256'],'current_node':result['current_node'],'path':result['path'],'nodes':[{k:v for k,v in n.items() if k!='text'} for n in result['nodes'].values()]}
        elif args.command=='verify':result=verify(conv,load(args.bundle))
        else:
            result=plan(conv,args.budget,args.pin)
            if args.command=='pack':write_new(args.out,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            else:
                esc=html.escape
                rows=''.join('<tr><td>'+esc(n['node_id'])+'</td><td>'+esc(n['disposition'])+'</td><td>'+esc(', '.join(n['warnings']))+'</td></tr>' for n in result['coverage'])
                messages=''.join('<article><h2>'+esc(m['role'])+' · '+esc(m['node_id'])+'</h2><pre>'+esc(m['text'])+'</pre></article>' for m in result['messages'])
                doc='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;"><title>Context Port handoff review</title><style>body{font:16px/1.6 system-ui;max-width:1000px;padding:24px;margin:auto;overflow-wrap:anywhere}pre{white-space:pre-wrap}td,th{text-align:left;border:1px solid #ccc;padding:8px}table{width:100%;border-collapse:collapse}article{border-top:1px solid #ccc}</style><h1>Review before you move</h1><p>Local extractive context plan. Not an import, summary, redaction, or proof that nothing important was lost.</p><ul>'+''.join('<li>'+esc(x)+'</li>' for x in result['limitations'])+'</ul><h2>Every node accounted for</h2><table><tr><th>Source node</th><th>Disposition</th><th>Not carried</th></tr>'+rows+'</table><h2>Selected text</h2>'+messages+'</html>'
                write_new(args.out,doc)
            result={'written':args.out,'selected_messages':len(result['messages']),'selected_text_characters':result['selected_text_characters'],'coverage_nodes':len(result['coverage'])}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except PortError as e:
        print('Error: '+str(e),file=sys.stderr);return 2
    except (ValueError,TypeError,KeyError,OSError):
        print('Error: Input, output or schema could not be processed. Check the supplied files and options.',file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
