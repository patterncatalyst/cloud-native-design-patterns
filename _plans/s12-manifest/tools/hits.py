import json,re,sys,collections
from pathlib import Path
segs=json.loads((Path(__file__).resolve().parent/"segs.json").read_text())
pats=[]
for line in Path("~/Dev/cloud-native-design-patterns/scripts/voice/patterns.tsv").read_text().splitlines():
    if not line or line.startswith("#"): continue
    f=line.split("\t")
    if len(f)<4: continue
    tier,case,label,rx=f[:4]
    rx=rx.replace("[[:space:]]",r"\s")
    try: pats.append((tier,label,re.compile(rx, 0 if case=="c" else re.I)))
    except re.error as e: print("bad",label,e,file=sys.stderr)
POS=[re.compile(r"\babove\b",re.I),re.compile(r"\bbelow\b",re.I),re.compile(r"\bnext\s+slide\b",re.I),re.compile(r"\bprevious\s+slide\b",re.I),re.compile(r"\bprevious\s+section\b",re.I),re.compile(r"\bfollowing\s+section\b",re.I),re.compile(r"\bsee\s+slide\s+\d+",re.I),re.compile(r"\bpreceding\b",re.I)]
EX=[re.compile(r"\b(?:above|below)\s+(?:[$~<>]?\d|zero|the\s+(?:threshold|limit|cutoff|floor|ceiling))",re.I),re.compile(r"\b(?:above|below)-\w+",re.I),re.compile(r"\b(?:at\s+or|or)\s+(?:above|below)\b",re.I)]
ENG=re.compile("p"+"odman",re.I)
def classify(t):
    cats=[]
    for tier,label,rx in pats:
        if rx.search(t): cats.append(f"{tier}:{label}")
    for rx in POS:
        for m in rx.finditer(t):
            ctx=t[max(0,m.start()-4):m.end()+20]
            if not any(e.search(ctx) for e in EX): cats.append("pos:"+m.group(0).lower())
    if ENG.search(t): cats.append("engine")
    return cats
if __name__=="__main__":
    tier=sys.argv[1] if len(sys.argv)>1 else "ban"
    decks=[d for d in segs if d.startswith("Designing")]
    uniq=collections.OrderedDict()
    for d in decks:
        for s in segs[d]:
            if s["code"]: continue
            c=classify(s["text"])
            c=[x for x in c if x.startswith(tier) or tier=="all"]
            if not c: continue
            k=s["text"]
            uniq.setdefault(k,{"cats":c,"where":[]})["where"].append(f"{d.split('-')[-1]}:{s['n']}/{s['sid']}{'N' if s['kind']=='notes' else ''}")
    print(len(uniq),"unique segments")
    for k,v in uniq.items():
        print("----",v["cats"],v["where"]); print(k)
