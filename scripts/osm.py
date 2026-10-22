import json, re, unicodedata, math, collections, os
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data') + '/'
O = os.environ.get('OSM_DIR', 'raw/osm/')
C = json.load(open(SP + 'communes.json'))
G = json.load(open(SP + 'geodata.json'))

def norm(s):
    s = (s or '').replace('œ', 'oe')
    s = unicodedata.normalize('NFD', s); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s.lower())

def pip(x, y, ring):
    ins = False; j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi: ins = not ins
        j = i
    return ins

def bb(rings):
    xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
    return (min(xs), min(ys), max(xs), max(ys))

# départements
DEP = []
for name, d in G['dep'].items():
    rings = d['rings'] if 'rings' in d else d['geo']
    DEP.append((name, rings, bb(rings)))
def dep_of(x, y):
    for name, rings, b in DEP:
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and any(pip(x, y, r) for r in rings): return name
    return None
def depkey(d): return 'Pikine' if d == 'Keur Massar' else d

# communes avec contour
CP = [(i, c['geo'], bb(c['geo'])) for i, c in enumerate(C) if c['geo']]
def com_of(x, y):
    for i, rings, b in CP:
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and any(pip(x, y, r) for r in rings): return i
    return None

# 1) localiser les communes sans contour grâce aux lieux habités OSM
PP = json.load(open(O + 'populated_places/populated_places.geojson'))['features']
rank = {'city': 0, 'town': 1, 'village': 2, 'hamlet': 3, None: 4}
places = []
for f in PP:
    p = f['properties']; g = f['geometry']
    if g['type'] != 'Point': continue
    places.append((norm(p.get('name')), p.get('place'), g['coordinates'][0], g['coordinates'][1], p.get('name')))
fixed = 0
for c in C:
    if c['geo'] or c.get('pt'): continue
    k = norm(c['n'].split('-')[0]) if norm(c['n']) not in {pl[0] for pl in places} else norm(c['n'])
    cands = sorted([pl for pl in places if pl[0] and (pl[0] == norm(c['n']) or pl[0] == k)], key=lambda pl: rank.get(pl[1], 4))
    for pl in cands:
        if depkey(dep_of(pl[2], pl[3]) or '') == depkey(c['d']) or dep_of(pl[2], pl[3]) == c['d']:
            c['pt'] = [round(pl[2], 4), round(pl[3], 4)]; fixed += 1; break
import difflib
# priorité aux villes et bourgs OSM homonymes (les localités DTGC homonymes peuvent être un autre village)
moved = []
for c in C:
    if c['geo']: continue
    kc = norm(c['n'])
    for pl in sorted([pl for pl in places if pl[0] == kc and pl[1] in ('city', 'town')], key=lambda pl: rank[pl[1]]):
        if depkey(dep_of(pl[2], pl[3]) or '') == depkey(c['d']):
            new = [round(pl[2], 4), round(pl[3], 4)]
            if c.get('pt') and math.hypot(new[0] - c['pt'][0], new[1] - c['pt'][1]) > 0.03: moved.append((c['n'], c['pt'], new))
            c['pt'] = new; break
for c in C:
    if c['n'] == 'Mékhé' and not c['geo']: c['pt'] = [-16.632, 15.110]
print('points déplacés vers la ville OSM', len(moved), moved[:40])
MAN = {'Jaxaay-Parcelles': [-17.272, 14.792], 'Keur Massar Sud': [-17.312, 14.774], 'Pikine Nord': [-17.392, 14.762],
       'Joal-Fadhiouth': [-16.833, 14.163], 'Popenguine': [-17.113, 14.553], 'Somone': [-17.078, 14.488],
       'Nioro': [-15.783, 13.75], 'Malem Hoddar': [-15.296, 14.088], 'Dioffior': [-16.669, 14.185]}
for c in C:
    if c['geo'] or c.get('pt'): continue
    if c['n'] in MAN: c['pt'] = MAN[c['n']]; fixed += 1; continue
    kc = norm(c['n'])
    best = None; br = 0.74
    for pl in places:
        if not pl[0] or abs(len(pl[0]) - len(kc)) > 5: continue
        r = difflib.SequenceMatcher(None, kc, pl[0]).ratio()
        if r > br and depkey(dep_of(pl[2], pl[3]) or '') == depkey(c['d']): br = r; best = pl
    if best: c['pt'] = [round(best[2], 4), round(best[3], 4)]; fixed += 1; print('  fuzzy', c['n'], '->', best[4], round(br, 2))
print('communes localisées via OSM', fixed, 'restantes', [(c['d'], c['n']) for c in C if not c['geo'] and not c.get('pt')])

PTC = [(i, c['pt'], depkey(c['d'])) for i, c in enumerate(C) if not c['geo'] and c.get('pt')]
PTR = {j: min(6.0, max(1.5, math.sqrt((C[j]['p'] or 5000) / 2000 / math.pi))) for j, _, _ in PTC}
def near_point(x, y, dd=None):
    best = None; bs = 1.0
    for j, (px, py), d0 in PTC:
        if dd and d0 != dd: continue
        km = math.hypot((px - x) * 111.32 * math.cos(math.radians(y)), (py - y) * 110.57)
        sc = km / PTR[j]
        if sc < bs: bs = sc; best = j
    return best
def assign(x, y):
    i = com_of(x, y)
    if i is not None:
        # une commune urbaine sans contour GADM incluse dans ce polygone récupère les objets dans son rayon
        j = near_point(x, y, depkey(C[i]['d']))
        return j if j is not None else i
    d = dep_of(x, y)
    if not d: return None
    best = None; bd = 1e9
    for j, (px, py), dd in PTC:
        if dd == depkey(d):
            e = (px - x) ** 2 + (py - y) ** 2
            if e < bd: bd = e; best = j
    return best

# 2) catégories OSM
CATS = [
 ('sante', 'Santé', {'amenity': {'hospital', 'clinic', 'doctors', 'dentist', 'pharmacy'}, 'healthcare': None}),
 ('educ', 'Éducation', {'amenity': {'school', 'college', 'kindergarten', 'university', 'training', 'library', 'language_school', 'driving_school'}}),
 ('admin', 'Services publics', {'amenity': {'townhall', 'police', 'post_office', 'public_building', 'courthouse', 'fire_station', 'community_centre', 'social_centre', 'social_facility', 'prison', 'office'}}),
 ('fin', 'Banques & finance', {'amenity': {'bank', 'atm', 'money_transfer', 'bureau_de_change'}}),
 ('comm', 'Commerces & marchés', {'amenity': {'marketplace'}, 'shop': None}),
 ('resto', 'Restauration', {'amenity': {'restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'food_court', 'ice_cream', 'nightclub'}}),
 ('heb', 'Hébergement touristique', {'tourism': {'hotel', 'guest_house', 'apartment', 'hostel', 'camp_site', 'motel', 'chalet', 'cabin', 'camp_pitch', 'alpine_hut', 'lean_to', 'wilderness_hut', 'trail_riding_station'}}),
 ('cult', 'Culture, loisirs & patrimoine', {'tourism': {'attraction', 'artwork', 'museum', 'gallery', 'viewpoint', 'zoo', 'theme_park', 'aquarium', 'picnic_site', 'information'}, 'amenity': {'theatre', 'cinema', 'arts_centre', 'casino', 'gambling'}, 'historic': None, 'leisure': None}),
 ('culte', 'Lieux de culte', {'amenity': {'place_of_worship'}}),
 ('transp', 'Transport & mobilité', {'amenity': {'fuel', 'bus_station', 'parking', 'ferry_terminal', 'taxi', 'car_rental', 'car_wash', 'charging_station', 'bicycle_parking', 'motorcycle_parking'}}),
 ('eau', 'Eau & assainissement', {'amenity': {'drinking_water', 'water_point', 'watering_place', 'fountain', 'toilets', 'waste_disposal', 'recycling', 'waste_basket'}, 'man_made': {'water_tower', 'water_well', 'water_works', 'wastewater_plant', 'pumping_station', 'reservoir_covered', 'water_tap', 'storage_tank', 'septic_tank'}}),
 ('telec', 'Énergie & télécoms', {'man_made': {'tower', 'mast', 'antenna', 'communications_tower', 'utility_pole', 'street_cabinet', 'satellite_dish', 'works', 'chimney', 'silo', 'fuel_tank', 'oil_tank', 'gasometer', 'windmill'}}),
]
def classify(p):
    for code, lab, rules in CATS:
        for k, vals in rules.items():
            v = p.get(k)
            if v and (vals is None or v in vals): return code
    return None

def centroid(g):
    t = g['type']; c = g['coordinates']
    if t == 'Point': return c
    if t == 'LineString': pts = c
    elif t == 'Polygon': pts = c[0]
    elif t == 'MultiPolygon': pts = c[0][0]
    else: return None
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]

seen = set(); pts = []; ncat = collections.Counter(); sub = collections.defaultdict(collections.Counter)
files = ['poi/points_of_interest.geojson', 'education/education_facilities.geojson', 'health/health_facilities.geojson',
         'financial/financial_services.geojson', 'cultural/cultural_places.geojson', 'sea_ports/sea_ports.geojson']
for fn in files:
    for f in json.load(open(O + fn))['features']:
        p = f['properties']; oid = p.get('id')
        if oid in seen: continue
        seen.add(oid)
        cat = classify(p)
        if not cat: continue
        xy = centroid(f['geometry'])
        if not xy: continue
        typ = p.get('amenity') or p.get('shop') or p.get('tourism') or p.get('historic') or p.get('man_made') or p.get('leisure') or p.get('healthcare') or ''
        pts.append([cat, round(xy[0], 4), round(xy[1], 4), (p.get('name') or p.get('name_fr') or '').strip()[:48], typ])
        ncat[cat] += 1; sub[cat][typ] += 1
# aérodromes
for f in json.load(open(O + 'airports/airports.geojson'))['features']:
    p = f['properties']
    if p.get('aeroway') in ('aerodrome', 'helipad', 'terminal'):
        xy = centroid(f['geometry'])
        if xy: pts.append(['transp', round(xy[0], 4), round(xy[1], 4), (p.get('name') or '')[:48], p['aeroway']]); ncat['transp'] += 1; sub['transp'][p['aeroway']] += 1
print('POI classés', len(pts), ncat)

# 3) jointure spatiale
TYPE_KEYS = {}
cstat = [collections.Counter() for _ in C]
for q in pts:
    i = assign(q[1], q[2])
    q.append(i if i is not None else -1)
    if i is not None:
        cstat[i][q[0]] += 1
        if q[4] in ('hospital', 'clinic', 'doctors', 'pharmacy', 'school', 'college', 'university', 'kindergarten', 'bank', 'atm', 'marketplace', 'hotel', 'guest_house', 'fuel', 'bus_station', 'police', 'post_office', 'townhall', 'restaurant', 'museum', 'attraction', 'water_tower', 'water_well', 'aerodrome', 'ferry_terminal'):
            cstat[i]['t:' + q[4]] += 1
print('POI hors commune', sum(1 for q in pts if q[5] < 0))

# lieux habités par commune
pstat = [collections.Counter() for _ in C]
vil = []
for nm, pl, x, y, raw in places:
    i = assign(x, y)
    if i is None: continue
    pstat[i][pl or 'autre'] += 1
    if pl in ('city', 'town', 'village'): vil.append([round(x, 4), round(y, 4), raw[:40] if raw else '', {'city': 0, 'town': 1, 'village': 2}[pl], i])

# voies ferrées (longueur par commune) + géométrie simplifiée
rail = []; rstat = collections.Counter()
for f in json.load(open(O + 'railways/railways.geojson'))['features']:
    g = f['geometry']
    lines = [g['coordinates']] if g['type'] == 'LineString' else (g['coordinates'] if g['type'] == 'MultiLineString' else [])
    for L in lines:
        rail.append([[round(a, 4), round(b, 4)] for a, b in L[::max(1, len(L) // 40)] + [L[-1]]])
        for (x1, y1), (x2, y2) in zip(L, L[1:]):
            i = assign((x1 + x2) / 2, (y1 + y2) / 2)
            if i is not None: rstat[i] += math.hypot((x2 - x1) * 111.32 * math.cos(math.radians(y1)), (y2 - y1) * 110.57)

for i, c in enumerate(C):
    c['osm'] = dict(cstat[i])
    c['pl'] = dict(pstat[i])
    if rstat[i]: c['rail'] = round(rstat[i], 1)
json.dump(C, open(SP + 'communes2.json', 'w'), separators=(',', ':'), ensure_ascii=False)
types = sorted({q[4] for q in pts}); tix = {t: i for i, t in enumerate(types)}
byc = collections.defaultdict(list)
for q in pts: byc[q[0]].append([q[1], q[2], q[3], tix[q[4]], q[5] if q[5] >= 0 else None])
json.dump({'cats': [[a, b] for a, b, _ in CATS], 'types': types, 'pts': byc, 'vil': vil, 'rail': rail},
          open(SP + 'osm.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('osm.json', os.path.getsize(SP + 'osm.json'), 'villes/villages', len(vil), 'rail', len(rail))
