#!/usr/bin/env python3
"""Assign a stable authority_key to each annex row across years (greedy fuzzy clustering).
Writes authority_key_map.csv (name, year, key, canonical, score) for manual review and
tn_sic_annex_keyed.csv (annex rows plus key/canonical/tier)."""
import csv,re,collections,difflib
def norm(s):
    s=s.lower().replace("&"," and "); s=re.sub(r"[^a-z0-9 ]"," ",s)
    s=re.sub(r"\b(the|of|and|department|dept|tamil|nadu|tamilnadu|corporation|limited|ltd|directorate|commissionerate|office|govt|government|chennai)\b"," ",s)
    return re.sub(r"\s+"," ",s).strip()
R=list(csv.DictReader(open("tn_sic_annex.csv")))
rows=[r for r in R if r["is_total"]!="1"]
GENERIC=re.compile(r"^(secretariat|directorate|commissionerate|department|head office|office)$",re.I)
def full_name(r):
    n=re.sub(r"\s+"," ",r["name"]).strip()
    if r["layout"]=="C" and (GENERIC.match(n) or len(n)<12) and r["dept_hint"]:
        return f"{r['dept_hint']}, {n}"
    return n
for r in rows: r["name"]=full_name(r)
for r in R:
    if r["is_total"]!="1": r["name"]=full_name(r)
freq=collections.Counter(norm(r["name"]) for r in rows)
names=sorted(freq,key=lambda k:(-freq[k],k))
clusters=[]  # (key_norm, canonical_display, members)
key_of={}
for n in names:
    if not n: continue
    best=None;bs=0
    for c in clusters:
        s=difflib.SequenceMatcher(None,n,c[0]).ratio()
        # containment bonus for truncated names
        if (n in c[0] or c[0] in n) and min(len(n),len(c[0]))>=8: s=max(s,0.9)
        if s>bs: bs, best = s, c
    if best and bs>=0.86:
        best[2].append(n); key_of[n]=(best[0],bs)
    else:
        clusters.append([n,None,[n]]); key_of[n]=(n,1.0)
# canonical display name = most frequent raw spelling in cluster
raw_by_norm=collections.defaultdict(collections.Counter)
for r in rows: raw_by_norm[norm(r["name"])][re.sub(r"\s+"," ",r["name"]).strip()]+=1
canon={}
for c in clusters:
    cnt=collections.Counter()
    for m in c[2]: cnt.update(raw_by_norm[m])
    canon[c[0]]=cnt.most_common(1)[0][0]
def tier(name):
    n=name.lower()
    if "secretariat" in n: return "Secretariat"
    if re.search(r"commission\b|tribunal|court|university|corporation|board|authority|agency|society|institute|ltd|limited",n): return "Body/Corporation"
    return "HOD"
with open("authority_key_map.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["name_norm","years","n_rows","key","canonical","score"])
    for n in names:
        yrs=sorted({r["year"] for r in rows if norm(r["name"])==n})
        k,s=key_of.get(n,(n,1.0)); w.writerow([n,"|".join(yrs),freq[n],k,canon.get(k,""),f"{s:.2f}"])
with open("tn_sic_annex_keyed.csv","w",newline="") as f:
    fields=list(R[0].keys())+["key","canonical","tier"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for r in R:
        n=norm(r["name"]); k=key_of.get(n,(n,1))[0]
        r2=dict(r); r2["key"]=k; r2["canonical"]=canon.get(k,r["name"]); r2["tier"]=tier(r["name"]); w.writerow(r2)
keys_by_year=collections.defaultdict(set)
for r in rows: keys_by_year[key_of.get(norm(r["name"]),(norm(r["name"]),1))[0]].add(r["year"])
print("clusters:",len(clusters),"| present all 9 years:",sum(1 for k,v in keys_by_year.items() if len(v)==9),"| ≥7 years:",sum(1 for k,v in keys_by_year.items() if len(v)>=7),"| 1 year:",sum(1 for k,v in keys_by_year.items() if len(v)==1))
