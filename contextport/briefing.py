"""Human-authored handoff cards with exact selected-branch quotations."""
import html,json
from . import core
LIMIT=4*1024*1024
SCOPE='Human-authored interpretations and confirmations; quotations prove text location, not truth, current intent, authorship or permission to share.'
def _keys(value,keys):
    if type(value) is not dict or set(value)!=set(keys):raise core.PortError('Unexpected briefing fields.')
def _text(value,limit,empty=False):
    if type(value) is not str or len(value)>limit or (not empty and not value.strip()):raise core.PortError('Invalid briefing text.')
    try:value.encode('utf8')
    except UnicodeError:raise core.PortError('Invalid briefing text encoding.') from None
    return value

def template(conv):return {'schema':1,'source_sha256':core.inspect(conv)['source_sha256'],'cards':[]}

def build(conv,spec,budget=12000,pins=()):
    selected=core.plan(conv,budget,pins);_keys(spec,['schema','source_sha256','cards'])
    if type(spec['schema']) is not int or spec['schema']!=1 or spec['source_sha256']!=selected['source_sha256']:raise core.PortError('Briefing source binding or schema differs.')
    if type(spec['cards']) is not list or not 1<=len(spec['cards'])<=100:raise core.PortError('Supply 1 to 100 human-authored cards.')
    by_id={m['node_id']:m for m in selected['messages']};cards=[];seen=set()
    for card in spec['cards']:
        _keys(card,['id','kind','text','human_confirmed','references']);cid=_text(card['id'],80)
        if cid in seen:raise core.PortError('Duplicate card ID.')
        seen.add(cid)
        if card['kind'] not in ('goal','fact','todo') or type(card['human_confirmed']) is not bool:raise core.PortError('Invalid card kind or confirmation.')
        _text(card['text'],4000)
        if card['kind']=='fact' and card['human_confirmed'] is not True:raise core.PortError('Facts require an explicit human confirmation; this is not tool fact verification.')
        if card['kind']!='fact' and card['human_confirmed'] is not False:raise core.PortError('Only fact cards have human confirmation.')
        if type(card['references']) is not list or not 1<=len(card['references'])<=5:raise core.PortError('Each card needs 1 to 5 exact selected-message references.')
        citations=[];refs=set()
        for ref in card['references']:
            _keys(ref,['node_id','start','end']);nid=_text(ref['node_id'],300)
            if nid not in by_id:raise core.PortError('Reference is not in selected messages; increase budget or pin an eligible active-branch message.')
            node=by_id[nid];start,end=ref['start'],ref['end']
            if type(start) is not int or type(end) is not int or not 0<=start<end<=len(node['text']) or end-start>4000:raise core.PortError('Invalid quotation character interval.')
            key=(nid,start,end)
            if key in refs:raise core.PortError('Duplicate quotation reference.')
            refs.add(key);citations.append({'node_id':nid,'role':node['role'],'start':start,'end':end,'quote':node['text'][start:end],'message_sha256':node['text_sha256']})
        cards.append({'id':cid,'kind':card['kind'],'human_text':card['text'],'human_confirmed':card['human_confirmed'],'citations':citations,'semantic_support_verified':False})
    result={'format':'context-port-briefing-v1','selection':selected,'specification':spec,'cards':cards,'scope':SCOPE,'budget_scope':'Selected original message Unicode characters only; human text, repeated citations, metadata and output bytes are additional.'}
    # Build must never produce an output larger than its own accepted reader.
    if len(core.canonical(result).encode('utf8'))>LIMIT:raise core.PortError('Briefing output exceeds 4 MiB; reduce message budget or cards.')
    return result

def verify(conv,bundle):
    if type(bundle) is not dict or type(bundle.get('selection')) is not dict:raise core.PortError('Invalid briefing bundle.')
    selection=bundle['selection'];expected=build(conv,bundle.get('specification'),selection.get('budget_characters'),selection.get('pins'))
    if not core.strict_equal(bundle,expected):raise core.PortError('Briefing differs from its source, exact quotations or human specification.')
    return {'verified':True,'scope':'Reproduced selected branch, omissions and exact quotations against supplied original; '+SCOPE}

def markdown(conv,bundle):
    verify(conv,bundle)
    # Escape explicit Markdown/HTML syntax and control characters. Renderers
    # may still auto-link plain URLs or email addresses; this is not a sanitizer.
    def esc(value):
        return ''.join('&#'+str(ord(c))+';' if c in '&<>`*_[]()!#|\\' or ord(c)<32 else c for c in value)
    lines=['# Reviewed local handoff','',SCOPE,'',bundle['budget_scope'],'']
    for kind,title in [('goal','Goals (human-authored)'),('fact','Facts (human-confirmed, not tool-verified)'),('todo','To do (human-authored)')]:
        lines+=['## '+title,'']
        for card in bundle['cards']:
            if card['kind']!=kind:continue
            lines+=['### '+esc(card['id']),esc(card['human_text']),'']
            for cite in card['citations']:
                lines+=['Source '+esc(cite['node_id'])+' ('+esc(cite['role'])+'), characters '+str(cite['start'])+'..'+str(cite['end'])+' (exclusive end):',esc(cite['quote']),'']
    lines+=['## Original-message coverage','No attachments, alternate branches or tool/system roles are transferred. See the JSON bundle for message text and warning details.','']
    for row in bundle['selection']['coverage']:
        lines.append('- '+esc(row['node_id'])+': '+row['disposition']+('; '+esc(', '.join(row['warnings'])) if row['warnings'] else ''))
    out='\n'.join(lines)+'\n'
    if len(out.encode('utf8'))>LIMIT:raise core.PortError('Rendered handoff exceeds 4 MiB; reduce content before export.')
    return out

def write_new(path,text):
    raw=text.encode('utf8')
    if len(raw)>LIMIT:raise core.PortError('Briefing output exceeds 4 MiB.')
    from pathlib import Path
    with Path(path).open('xb') as f:f.write(raw)
