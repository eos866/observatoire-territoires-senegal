import sys, json, re, unicodedata, math
from collections import defaultdict, Counter
SP=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data') + '/'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/')
from rds import load, dataframe, val
import importlib.util
spec=importlib.util.spec_from_file_location('p', os.path.dirname(os.path.abspath(__file__)) + '/'+'process_lib.py')

RDS=os.environ.get('MAPSENEGAL_RDS', 'raw/mapSenegal/inst/rds/')
exec(open(os.path.dirname(os.path.abspath(__file__)) + '/'+'process_lib.py').read())   # utm2ll, rings_of, pip, rdp, area_km2

def norm(s):
    s=s.replace('œ','oe').replace('Œ','oe')
    s=unicodedata.normalize('NFD',s); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'[^a-z0-9]','',s.lower())

# --- référentiel communes (population)
VP=[l.split('|') for l in open(SP+'communes_vp.txt',encoding='utf-8').read().splitlines() if l and not l.startswith('#')]
VP=[(d,c,int(p)) for d,c,p in VP]
dsum=Counter(); [dsum.__setitem__(d,dsum[d]+p) for d,c,p in VP]

# --- GADM : départements et communes
FIX={'Birkilane':'Birkelane','Malème Hodar':'Malem Hoddar','Médina Yoro Foula':'Médina Yoro Foulah','Koupentoum':'Koumpentoum'}
dep=dataframe(load(RDS+'departements.rds'))
gid2dep={g:FIX.get(n,n) for g,n in zip(val(dep['GID_2']),val(dep['NAME']))}
com=dataframe(load(RDS+'communes.rds'))
cpolys=[rings_of(g) for g in val(com['geometry'])]
cnames=val(com['NAME']); cdep=[gid2dep[g] for g in val(com['GID_2'])]

# appariement par nom normalisé dans le département (Keur Massar est dans Pikine côté GADM)
vp_by=defaultdict(list)
for d,c,p in VP:
    dd='Pikine' if d=='Keur Massar' else d
    vp_by[dd].append((c,p,d))
ALIAS={'diacksao':'tivaouanediacksao','plateau':'dakarplateau','daliford':'dalifort','hlm':'hlm','keurmassar':'keurmassarnord'}
matched={}; used=set(); FUZ=[]
for i,(n,d) in enumerate(zip(cnames,cdep)):
    k=norm(n); k=ALIAS.get(k,k)
    best=None
    for c,p,d0 in vp_by[d]:
        kc=norm(c)
        if kc==k or kc.replace('commune','')==k: best=(c,p,d0);break
    if not best:
        for c,p,d0 in vp_by[d]:
            kc=norm(c)
            if len(k)>4 and (kc.startswith(k) or k.startswith(kc)): best=(c,p,d0);break
    if not best:
        import difflib
        cands=[(difflib.SequenceMatcher(None,k,norm(c)).ratio(),c,p,d0) for c,p,d0 in vp_by[d] if (d,c) not in used]
        cands.sort(reverse=True)
        if cands and cands[0][0]>=0.72 and n not in ('Pikine Sud','Bamba Ndiayene'): best=cands[0][1:]; FUZ.append((n,best[0],round(cands[0][0],2)))
    if best and (d,best[0]) not in used:
        matched[i]=best; used.add((d,best[0]))
print('GADM communes',len(cnames),'appariées',len(matched))
unm=[(cnames[i],cdep[i]) for i in range(len(cnames)) if i not in matched]
print('non appariées GADM',len(unm), unm[:60])
vpun=[(d,c,p) for d,c,p in VP if (('Pikine' if d=='Keur Massar' else d),c) not in used]
def vpun_final(): return []
print('FUZ',FUZ)
print('référentiel sans contour',len(vpun))
json.dump({'unm':unm,'vpun':vpun},open(SP+'match_report.json','w'),ensure_ascii=False)

# ---------- construction des communes
DREG={}
for reg,lst in {'SN-DK':'Dakar,Guédiawaye,Pikine,Rufisque,Keur Massar','SN-DB':'Bambey,Diourbel,Mbacké','SN-FK':'Fatick,Foundiougne,Gossas','SN-KA':'Birkelane,Kaffrine,Koungheul,Malem Hoddar','SN-KL':'Guinguinéo,Kaolack,Nioro du Rip','SN-KE':'Kédougou,Salémata,Saraya','SN-KD':'Kolda,Médina Yoro Foulah,Vélingara','SN-LG':'Kébémer,Linguère,Louga','SN-MT':'Kanel,Matam,Ranérou Ferlo','SN-SL':'Dagana,Podor,Saint-Louis','SN-SE':'Bounkiling,Goudomp,Sédhiou','SN-TC':'Bakel,Goudiry,Koumpentoum,Tambacounda','SN-TH':'Mbour,Thiès,Tivaouane','SN-ZG':'Bignona,Oussouye,Ziguinchor'}.items():
    for n in lst.split(','): DREG[n]=reg
bbox=[]
for polys in cpolys:
    xs=[p[0] for poly in polys for p in poly[0]]; ys=[p[1] for poly in polys for p in poly[0]]
    bbox.append((min(xs),min(ys),max(xs),max(ys)))
def locate(x,y):
    for k,polys in enumerate(cpolys):
        b=bbox[k]
        if b[0]<=x<=b[2] and b[1]<=y<=b[3] and any(pip(x,y,p) for p in polys): return k
    return None
CAT={'hopital':'hop','centre de sante':'cs','centre medical':'cs','polyclinique':'cs','district sanitaire':'cs','poste de sante':'ps','case de sante':'ps','dispensaire':'ps','maternite':'ps','infirmerie':'ps','pharmacie':'ph','clinique':'pr','cabinet':'pr','plateau medical':'pr'}
st=[{'h':Counter(),'loc':0,'rd':Counter()} for _ in cpolys]
ss=dataframe(load(RDS+'structures_sanitaires.rds'))
for t,g in zip(val(ss['TYPE']),val(ss['geom'])):
    x,y=val(g); k=locate(x,y)
    if k is not None: st[k]['h'][CAT.get(t,'au')]+=1
lo=dataframe(load(RDS+'localites.rds'))
for g in val(lo['geom']):
    x,y=val(g); k=locate(x,y)
    if k is not None: st[k]['loc']+=1
ro=dataframe(load(RDS+'routes.rds'))
for t,g in zip(val(ro['TYPE']),val(ro['geometry'])):
    v=val(g); n=len(v)//2; P=list(zip(v[:n],v[n:])); t=int(t)
    for (x1,y1),(x2,y2) in zip(P,P[1:]):
        k=locate((x1+x2)/2,(y1+y2)/2)
        if k is not None: st[k]['rd'][t]+=math.hypot(x2-x1,y2-y1)/1000
out=[]
for i,polys in enumerate(cpolys):
    rings=[]
    for poly in polys:
        ring=poly[0]; dk=cdep[i] in ('Dakar','Guédiawaye','Pikine','Rufisque')
        s2=rdp(ring,60 if dk else 260)
        if len(s2)>=4 and area_km2([[ring]])>0.05: rings.append([[round(c,4 if dk else 3) for c in utm2ll(x,y)] for x,y in s2])
    m=matched.get(i)
    d=m[2] if m else cdep[i]
    out.append({'n':m[0] if m else cnames[i],'g':cnames[i],'d':d,'r':DREG[d],'p':m[1] if m else None,'a':round(area_km2(polys),1),'geo':rings,
      'h':dict(st[i]['h']),'loc':st[i]['loc'],'rd':{str(k):round(v,1) for k,v in st[i]['rd'].items()}})
for d,c in vpun_final():
    pass


# --- communes sans contour GADM (surtout urbaines) : point = localité homonyme DTGC, statistiques = résidu du département
dnames=[gid2dep[g] for g in val(dep['GID_2'])]
dpolys=[rings_of(g) for g in val(dep['geometry'])]
def dep_of(x,y):
    for k,polys in enumerate(dpolys):
        if any(pip(x,y,p) for p in polys): return dnames[k]
    return None
locs=[(n,val(g)) for n,g in zip(val(lo['NAME']),val(lo['geom']))]
pts={}
for d,c,p in vpun:
    dd='Pikine' if d=='Keur Massar' else d; kc=norm(c); cand=None
    hits=sorted([(len(norm(n)),x,y) for n,(x,y) in locs if n and len(kc)>=4 and (norm(n)==kc or kc in norm(n))],key=lambda t:t[0])
    for L,x,y in hits:
        if dep_of(x,y)==dd: cand=(x,y); break
    pts[(d,c)]=cand
print('communes sans contour localisées',sum(1 for v in pts.values() if v),'/',len(pts))
# résidus : objets dans un département mais hors de toute commune GADM -> commune urbaine la plus proche du département
rst={k:{'h':Counter(),'loc':0,'rd':Counter()} for k in pts}
def nearest(x,y,dd):
    best=None;bd=1e18
    for (d,c),q in pts.items():
        if q and ('Pikine' if d=='Keur Massar' else d)==dd:
            e=(q[0]-x)**2+(q[1]-y)**2
            if e<bd: bd=e;best=(d,c)
    return best
def resid(x,y):
    if locate(x,y) is not None: return None
    dd=dep_of(x,y); return nearest(x,y,dd) if dd else None
for t,g in zip(val(ss['TYPE']),val(ss['geom'])):
    x,y=val(g); k=resid(x,y)
    if k: rst[k]['h'][CAT.get(t,'au')]+=1
for n,(x,y) in locs:
    k=resid(x,y)
    if k: rst[k]['loc']+=1
for d,c,p in vpun:
    q=pts[(d,c)]; ll=[round(v,4) for v in utm2ll(*q)] if q else None
    out.append({'n':c,'g':None,'d':d,'r':DREG[d],'p':p,'a':None,'geo':None,'pt':ll,'h':None,'loc':None,'rd':None})
json.dump(out,open(SP+'communes.json','w'),separators=(',',':'),ensure_ascii=False)
import os; print('communes',len(out),'avec contour',sum(1 for o in out if o['geo']),'taille',os.path.getsize(SP+'communes.json'))
print('pop totale',sum(o['p'] or 0 for o in out))
