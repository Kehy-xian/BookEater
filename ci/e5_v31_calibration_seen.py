from __future__ import annotations
import ast,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31

src=(ROOT/'ci/e5_v3_calibration_seen.py').read_text(encoding='utf-8')
tree=ast.parse(src);CASES=None
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in node.targets):
        CASES=ast.literal_eval(node.value);break
if CASES is None:raise RuntimeError('CASES not found')
MODEL=ROOT/'resources/models/multilingual-e5-small-onnx';OUT=ROOT/'tests/e5_v31_calibration_seen.md'

def pct(a,b):return 100*a/b if b else 0
m=HybridE5ClassifierV31(MODEL);rows=[];gold=hit=pred=exact=0;rn=rno=wn=wno=0
for cid,text,er,ew in CASES:
    p=m.analyze(text);pr=p['response'];pw=p['world'];g=set(('r',x) for x in er)|set(('w',x) for x in ew);q=set(('r',x) for x in pr)|set(('w',x) for x in pw)
    gold+=len(g);hit+=len(g&q);pred+=len(q);exact+=g==q
    if not er:rn+=1;rno+=not pr
    if not ew:wn+=1;wno+=not pw
    rows.append((cid,text,er,ew,pr,pw))
lines=['# E5 hybrid v3.1 calibration (seen diagnostic cases)','',f'- label recall: {pct(hit,gold):.1f}%',f'- label precision: {pct(hit,pred):.1f}%',f'- exact records: {pct(exact,len(rows)):.1f}%',f'- response NULL: {pct(rno,rn):.1f}%',f'- world NULL: {pct(wno,wn):.1f}%','','## Mismatches']
for cid,text,er,ew,pr,pw in rows:
    if set(er)!=set(pr) or set(ew)!=set(pw):lines.append(f"- {cid} gold R={er or ['NULL']} W={ew or ['NULL']} / pred R={pr or ['NULL']} W={pw or ['NULL']} :: {text}")
OUT.write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines))
