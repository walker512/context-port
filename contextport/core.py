"""Local, extractive context planning. No model calls or destination imports."""
import hashlib
import json
import os
import stat
import math
from pathlib import Path

MAX_BYTES=32*1024*1024

class PortError(ValueError):
    """Fixed, content-free user-facing validation failure."""

def strict_equal(left,right):
    if type(left) is not type(right):return False
    if isinstance(left,dict):return left.keys()==right.keys() and all(strict_equal(left[k],right[k]) for k in left)
    if isinstance(left,list):return len(left)==len(right) and all(strict_equal(a,b) for a,b in zip(left,right))
    return left==right

def reject_constant(value):
    raise PortError("Non-finite JSON numbers are not supported.")

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def pairs(items):
    result={}
    for k,v in items:
        if k in result:raise PortError('Duplicate JSON key.')
        result[k]=v
    return result

def load(path):
    # Inspect before open and again on the descriptor. Nonblocking/no-follow
    # protects the intervening race on platforms that provide these flags.
    if not stat.S_ISREG(Path(path).lstat().st_mode):raise PortError('Input must be a regular file, not a symlink or special file.')
    flags=os.O_RDONLY | getattr(os,'O_NONBLOCK',0) | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_BINARY',0)
    fd=os.open(path,flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise PortError('Input must be a regular file.')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_BYTES+1)
    finally:os.close(fd)
    if len(raw)>MAX_BYTES:raise PortError('Input exceeds 32 MiB.')
    try:data=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject_constant)
    except (json.JSONDecodeError,UnicodeError):raise PortError('Input is not valid UTF-8 JSON.') from None
    except RecursionError:raise PortError('JSON is too deeply nested.') from None
    pending=[(data,0)]
    while pending:
        value,depth=pending.pop()
        if isinstance(value,float) and not math.isfinite(value):raise PortError("Non-finite JSON numbers are not supported.")
        if isinstance(value,(list,dict)):
            if depth>40:raise PortError('JSON exceeds depth 40.')
            pending.extend((v,depth+1) for v in (value.values() if isinstance(value,dict) else value))
    return data

def conversations(data):
    if not isinstance(data,list) or not data or len(data)>10000:raise PortError('Expected a nonempty ChatGPT conversation JSON array (up to 10000).')
    seen=set()
    for conv in data:
        if not isinstance(conv,dict):raise PortError('Invalid conversation.')
        cid=conv.get('id') or conv.get('conversation_id')
        if not isinstance(cid,str) or not cid or len(cid)>300 or cid in seen:raise PortError('Missing or duplicate conversation ID.')
        seen.add(cid)
    return {c.get('id') or c['conversation_id']:c for c in data}

def inspect(conv):
    mapping=conv.get('mapping')
    if not isinstance(mapping,dict) or not mapping or len(mapping)>10000:raise PortError('Expected 1–10000 mapping nodes.')
    current=conv.get('current_node')
    if not isinstance(current,str) or current not in mapping:raise PortError('Missing/invalid current_node. No branch is guessed.')
    if any(not isinstance(node,dict) for node in mapping.values()):raise PortError('Invalid node.')
    for nid,node in mapping.items():
        if not nid or len(nid)>300 or not isinstance(node,dict):raise PortError('Invalid node.')
        if node.get('id')!=nid:raise PortError('Mapping key and node id differ.')
        parent=node.get('parent')
        if parent is not None and (not isinstance(parent,str) or parent not in mapping):raise PortError('A node references a missing parent.')
        children=node.get('children')
        if not isinstance(children,list) or any(not isinstance(x,str) for x in children) or len(children)!=len(set(children)):raise PortError('Invalid node children.')
        for child in children:
            if child not in mapping or mapping[child].get('parent')!=nid:raise PortError('Inconsistent child link.')
        if parent is not None and nid not in mapping[parent].get('children',[]):raise PortError('A parent omits its child.')
    done=set()
    for nid in mapping:
        chain=set();cursor=nid
        while cursor is not None and cursor not in done:
            if cursor in chain:raise PortError('Cycle in conversation graph.')
            chain.add(cursor);cursor=mapping[cursor].get('parent')
        done.update(chain)
    path=[];cursor=current
    while cursor is not None:path.append(cursor);cursor=mapping[cursor].get('parent')
    path.reverse();nodes={}
    for nid,node in mapping.items():
        message=node.get('message');warnings=[];parts=[];role=None
        if message is not None:
            if not isinstance(message,dict):raise PortError('Invalid message.')
            author=message.get('author') or {};content=message.get('content') or {}
            if not isinstance(author,dict) or not isinstance(content,dict):raise PortError('Invalid message author/content.')
            role=author.get('role');rawparts=content.get('parts',[])
            if not isinstance(rawparts,list):raise PortError('Invalid content parts.')
            if content.get('content_type') not in {'text','multimodal_text'}:warnings.append('unsupported-content-type')
            for i,part in enumerate(rawparts):
                if isinstance(part,str):parts.append(part)
                else:warnings.append('non-text-part:'+str(i))
            if message.get('metadata',{}):warnings.append('metadata-not-carried')
            if role not in {'user','assistant'}:warnings.append('non-chat-role-not-carried')
        text='\n'.join(parts)
        nodes[nid]={'node_id':nid,'role':role,'text':text,'text_sha256':sha(text),'warnings':warnings,'has_message':message is not None}
    return {'path':path,'nodes':nodes,'current_node':current,'source_sha256':sha(conv)}

def plan(conv,budget=12000,pins=()):
    if type(budget) is not int or not 1<=budget<=1000000:raise PortError('Character budget must be 1–1000000.')
    if not isinstance(pins,(list,tuple)) or any(not isinstance(x,str) for x in pins) or len(set(pins))!=len(pins):raise PortError('Pins must be unique node IDs.')
    parsed=inspect(conv);nodes=parsed['nodes'];path=parsed['path']
    eligible=[n for n in path if nodes[n]['role'] in {'user','assistant'} and nodes[n]['text'] and 'unsupported-content-type' not in nodes[n]['warnings']]
    if any(n not in eligible for n in pins):raise PortError('Pinned node is not eligible text on the selected branch.')
    selected=set(pins);used=sum(len(nodes[n]['text']) for n in pins)
    if used>budget:raise PortError('Pinned text exceeds budget; nothing is silently unpinned.')
    # Keep a contiguous suffix of eligible messages, plus explicit pins. Stop
    # at the first message that will not fit, rather than skipping to tiny old turns.
    for n in reversed(eligible):
        if n in selected:continue
        size=len(nodes[n]['text'])
        if used+size>budget:break
        selected.add(n);used+=size
    if not selected:raise PortError('No complete message fits the budget. Increase budget; text is never truncated.')
    coverage=[]
    for nid,n in nodes.items():
        reason='selected' if nid in selected else 'off-branch' if nid not in path else 'structural-node' if not n['has_message'] else 'unsupported-or-empty' if nid not in eligible else 'budget-omission'
        coverage.append({'node_id':nid,'disposition':reason,'warnings':n['warnings'],'text_sha256':n['text_sha256']})
    return {'format':'context-port-v1','source_sha256':parsed['source_sha256'],'conversation_id':conv.get('id') or conv['conversation_id'],'current_node':parsed['current_node'],'budget_characters':budget,'pins':list(pins),'selected_text_characters':used,'messages':[{k:nodes[n][k] for k in ('node_id','role','text','text_sha256')} for n in path if n in selected],'coverage':coverage,'limitations':['Extractive selection, not semantic summarization or fact verification.','Budget counts selected Unicode text characters, not tokens or surrounding JSON/report overhead.','Attachments and non-text content are not transferred or checked for existence.','Metadata, tool/system roles and alternate branches are excluded from the context.','No platform import or continued-model-behavior guarantee. Review before sharing.']}

def verify(conv,bundle):
    if not isinstance(bundle,dict):raise PortError('Bundle must be an object.')
    expected=plan(conv,bundle.get('budget_characters'),bundle.get('pins'))
    if not strict_equal(bundle,expected):raise PortError('Bundle differs from the reproducible plan for this source: content, coverage, provenance or settings changed.')
    return {'verified':True,'scope':'Exact deterministic plan reproduced against supplied original; not authorship, completeness of original export, or semantic adequacy.'}
