import math
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


def area_km2(polys):
    s=0
    for poly in polys:
        for i,ring in enumerate(poly):
            a=0
            for j in range(len(ring)):
                x1,y1=ring[j-1]; x2,y2=ring[j]; a+=x1*y2-x2*y1
            s+= abs(a)/2*(1 if i==0 else -1)
    return s/1e6
