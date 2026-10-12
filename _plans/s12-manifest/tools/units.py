"""Build sentence-level voice units from segs.json for the six language decks."""
import json, re, collections, sys
from pathlib import Path
from hits import pats, POS, EX, ENG, segs
SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9'\"‘“(`\[])")
KEEP_WATCH = set()  # all watch labels are offered; policy is applied by the authors
def sentence_hits(t):
    cats=[]
    for tier,label,rx in pats:
        if label.startswith("em-dash pileup"): continue
        if rx.search(t): cats.append(f"{tier}:{label}")
    if t.count("—")>=2: cats.append("watch:em-dash x2 in one sentence")
    for rx in POS:
        for m in rx.finditer(t):
            ctx=t[max(0,m.start()-4):m.end()+20]
            if not any(e.search(ctx) for e in EX): cats.append("pos:"+m.group(0).lower())
    if ENG.search(t): cats.append("engine")
    return cats
decks=[d for d in segs if d.startswith("Designing")]
units=collections.OrderedDict()
for d in decks:
    short=d.split('-')[-1]
    for s in segs[d]:
        if s["code"]: continue
        for sent in SPLIT.split(s["text"]):
            c=sentence_hits(sent)
            if not c: continue
            u=units.setdefault(sent,{"cats":c,"where":[]})
            u["where"].append(f"{short}:{s['n']}/{s['sid']}{'N' if s['kind']=='notes' else ''}")
out=[]
for i,(k,v) in enumerate(units.items()):
    out.append({"u":i,"text":k,"cats":v["cats"],"where":v["where"]})
Path("units.json").write_text(json.dumps(out,indent=0,ensure_ascii=False))
c=collections.Counter()
for u in out:
    tiers={x.split(':')[0] for x in u['cats']}
    c["ban" if "ban" in tiers else "pos" if "pos" in tiers else "engine" if "engine" in tiers else "watch"]+=1
print(len(out), dict(c))
