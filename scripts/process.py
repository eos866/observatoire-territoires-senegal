import sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data') + '/'
from rds import load, dataframe, val
from collections import Counter, defaultdict
RDS = os.environ.get('MAPSENEGAL_RDS', 'raw/mapSenegal/inst/rds/')

# --- UTM 28N -> WGS84
def utm2ll(E, N, zone=28):
    a=6378137.0; f=1/298.257223563; k0=0.9996; e2=f*(2-f); ep2=e2/(1-e2)
    x=E-500000.0; y=N; m=y/k0
    mu=m/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
    p1=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)+(151*e1**3/96)*math.sin(6*mu)+(1097*e1**4/512)*math.sin(8*mu)
    n1=a/math.sqrt(1-e2*math.sin(p1)**2); t1=math.tan(p1)**2; c1=ep2*math.cos(p1)**2
    r1=a*(1-e2)/(1-e2*math.sin(p1)**2)**1.5; d=x/(n1*k0)
    lat=p1-(n1*math.tan(p1)/r1)*(d**2/2-(5+3*t1+10*c1-4*c1**2-9*ep2)*d**4/24+(61+90*t1+298*c1+45*t1**2-252*ep2-3*c1**2)*d**6/720)
    lon=(d-(1+2*t1+c1)*d**3/6+(5-2*c1+28*t1-3*c1**2+8*ep2+24*t1**2)*d**5/120)/math.cos(p1)
    return math.degrees(lon)+(zone-1)*6-180+3, math.degrees(lat)

def rings_of(g):
    """sfg MULTIPOLYGON/POLYGON -> list of polygons (list of rings of (x,y))"""
    cls=g['a']['class'][1]
    def mat(m):
        v=val(m); n=len(v)//2; return list(zip(v[:n], v[n:]))
    if cls=='POLYGON': return [[mat(r) for r in val(g)]]
    return [[mat(r) for r in val(p)] for p in val(g)]

def pip(x, y, poly):
    inside=False
    for ring in poly:
        n=len(ring); j=n-1
        for i in range(n):
            xi,yi=ring[i]; xj,yj=ring[j]
            if (yi>y)!=(yj>y) and x < (xj-xi)*(y-yi)/(yj-yi+1e-12)+xi: inside=not inside
            j=i
    return inside

def rdp(pts, eps):
    if len(pts)<3: return pts
    a,b=pts[0],pts[-1]; dx,dy=b[0]-a[0],b[1]-a[1]; L=math.hypot(dx,dy)
    dm,im=0,0
    for i in range(1,len(pts)-1):
        p=pts[i]
        dd=abs(dy*p[0]-dx*p[1]+b[0]*a[1]-b[1]*a[0])/L if L>1e-9 else math.hypot(p[0]-a[0],p[1]-a[1])
        if dd>dm: dm,im=dd,i
    if dm>eps: return rdp(pts[:im+1],eps)[:-1]+rdp(pts[im:],eps)
    return [a,b]

FIX={'Birkilane':'Birkelane','Malème Hodar':'Malem Hoddar','Médina Yoro Foula':'Médina Yoro Foulah','Koupentoum':'Koumpentoum'}
DREG={}
for reg,lst in {'SN-DK':'Dakar,Guédiawaye,Pikine,Rufisque','SN-DB':'Bambey,Diourbel,Mbacké','SN-FK':'Fatick,Foundiougne,Gossas','SN-KA':'Birkelane,Kaffrine,Koungheul,Malem Hoddar','SN-KL':'Guinguinéo,Kaolack,Nioro du Rip','SN-KE':'Kédougou,Salémata,Saraya','SN-KD':'Kolda,Médina Yoro Foulah,Vélingara','SN-LG':'Kébémer,Linguère,Louga','SN-MT':'Kanel,Matam,Ranérou Ferlo','SN-SL':'Dagana,Podor,Saint-Louis','SN-SE':'Bounkiling,Goudomp,Sédhiou','SN-TC':'Bakel,Goudiry,Koumpentoum,Tambacounda','SN-TH':'Mbour,Thiès,Tivaouane','SN-ZG':'Bignona,Oussouye,Ziguinchor'}.items():
    for n in lst.split(','): DREG[n]=reg
HASC2ISO={'DK':'SN-DK','DB':'SN-DB','FK':'SN-FK','KA':'SN-KA','KL':'SN-KL','KE':'SN-KE','KD':'SN-KD','LG':'SN-LG','MT':'SN-MT','SL':'SN-SL','SE':'SN-SE','TC':'SN-TC','TH':'SN-TH','ZG':'SN-ZG'}

dep=dataframe(load(RDS+'departements.rds'))
names=[FIX.get(n,n) for n in val(dep['NAME'])]
hasc=val(dep['HASC_2'])
dpolys=[rings_of(g) for g in val(dep['geometry'])]
bbox=[]
for polys in dpolys:
    xs=[p[0] for poly in polys for p in poly[0]]; ys=[p[1] for poly in polys for p in poly[0]]
    bbox.append((min(xs),min(ys),max(xs),max(ys)))
def locate(x,y):
    for k,polys in enumerate(dpolys):
        b=bbox[k]
        if b[0]<=x<=b[2] and b[1]<=y<=b[3] and any(pip(x,y,p) for p in polys): return k
    return None
def area_km2(polys):
    s=0
    for poly in polys:
        for i,ring in enumerate(poly):
            a=0
            for j in range(len(ring)):
                x1,y1=ring[j-1]; x2,y2=ring[j]; a+=x1*y2-x2*y1
            s+= abs(a)/2*(1 if i==0 else -1)
    return s/1e6

# --- géométries départements simplifiées (lon/lat)
geo_dep={}
for k,polys in enumerate(dpolys):
    out=[]
    for poly in polys:
        ring=poly[0]
        tol=150 if names[k] in ('Dakar','Guédiawaye','Pikine','Rufisque') else 700
        s=rdp(ring,tol)
        if len(s)>=4 and area_km2([[ring]])>2:
            out.append([[round(c,3) for c in utm2ll(x,y)] for x,y in s])
    geo_dep[names[k]]={'reg':DREG[names[k]],'rings':out,'area':round(area_km2(polys))}

# --- santé
ss=dataframe(load(RDS+'structures_sanitaires.rds'))
CAT={'hopital':'hop','centre de sante':'cs','centre medical':'cs','polyclinique':'cs','district sanitaire':'cs','poste de sante':'ps','case de sante':'ps','dispensaire':'ps','maternite':'ps','infirmerie':'ps','pharmacie':'ph','clinique':'pr','cabinet':'pr','plateau medical':'pr'}
health=defaultdict(Counter); pts=[]
miss=0
for nm,t,g in zip(val(ss['NAME']),val(ss['TYPE']),val(ss['geom'])):
    x,y=val(g); k=locate(x,y); c=CAT.get(t,'au')
    if k is None: miss+=1; continue
    health[names[k]][c]+=1
    lon,lat=utm2ll(x,y); pts.append([round(lon,4),round(lat,4),c,(nm or '').strip()[:40]])
print('santé hors polygone',miss, len(pts))

# --- localités
lo=dataframe(load(RDS+'localites.rds')); loc=Counter(); miss=0
for g in val(lo['geom']):
    x,y=val(g); k=locate(x,y)
    if k is None: miss+=1
    else: loc[names[k]]+=1
print('localités',sum(loc.values()),'hors',miss)

# --- routes : longueur par type et département (milieu de segment)
ro=dataframe(load(RDS+'routes.rds')); roads=defaultdict(Counter); lines=[]
for t,g in zip(val(ro['TYPE']),val(ro['geometry'])):
    v=val(g); n=len(v)//2; P=list(zip(v[:n],v[n:])); t=int(t)
    for (x1,y1),(x2,y2) in zip(P,P[1:]):
        k=locate((x1+x2)/2,(y1+y2)/2)
        if k is not None: roads[names[k]][t]+=math.hypot(x2-x1,y2-y1)/1000
    if t<=3:
        s=rdp(P,600)
        lines.append([t,[[round(c,3) for c in utm2ll(x,y)] for x,y in s]])

# --- universités
un=dataframe(load(RDS+'universites.rds')); unis=[]
for nm,fa,st,g in zip(val(un['NAME']),val(un['NB_FACULTIES']),val(un['NB_STUDENTS']),val(un['geom'])):
    x,y=val(g); lon,lat=utm2ll(x,y); k=locate(x,y)
    unis.append([round(lon,4),round(lat,4),nm.title(),int(st) if st==st else None, names[k] if k is not None else None])

stats={n:{'h':dict(health[n]),'loc':loc[n],'rd':{str(k):round(v,1) for k,v in roads[n].items()}} for n in names}
json.dump({'dep':geo_dep,'stats':stats,'pts':pts,'roads':lines,'unis':unis},open(DATA + 'geodata.json','w'),separators=(',',':'),ensure_ascii=False)
import os; print(os.path.getsize(DATA + 'geodata.json'))
for n in names: print(n, geo_dep[n]['reg'], geo_dep[n]['area'], stats[n]['h'], stats[n]['loc'], {k:round(v) for k,v in roads[n].items()})
print(unis)

# --- régions (contours GADM simplifiés)
rg=dataframe(load(RDS+'regions.rds')); geo_reg={}
for iso,g in zip(val(rg['ISO']),val(rg['geometry'])):
    out=[]
    for poly in rings_of(g):
        ring=poly[0]; s=rdp(ring,150 if iso=='SN-DK' else 700)
        if len(s)>=4 and area_km2([[ring]])>2: out.append([[round(c,3) for c in utm2ll(x,y)] for x,y in s])
    geo_reg[iso]=out
d=json.load(open(DATA + 'geodata.json'))
d['reg']=geo_reg
json.dump(d,open(DATA + 'geodata.json','w'),separators=(',',':'),ensure_ascii=False)
print('regions', list(geo_reg), os.path.getsize(DATA + 'geodata.json'))
