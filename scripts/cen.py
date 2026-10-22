import os
"""Agrège le répertoire des localités ANSD (2013, 2023) par commune, département, région et l'apparie aux communes de l'observatoire."""
import json, re, unicodedata, difflib, collections
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data') + '/'
C = json.load(open(SP + 'communes2.json'))
def norm(s):
    s = (s or '').replace('’', "'").replace('œ', 'oe').replace('Œ', 'OE')
    s = unicodedata.normalize('NFD', s); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s.lower())
DEPFIX = {'mbacke': 'mbacke', 'nioro': 'niorodurip', 'saintlouis': 'saintlouis', 'mbour': 'mbour', 'koupentoum': 'koumpentoum',
          'ranerou': 'raneroufrlo', 'raneroufrlo': 'raneroufrlo', 'raneroufrelo': 'raneroufrlo', 'raneroufrelo ': 'raneroufrlo', 'medinayorofoula': 'medinayorofoulah',
          'birkilane': 'birkelane', 'malemhodar': 'malemhoddar'}
def dk(s):
    k = norm(s); k = DEPFIX.get(k, k)
    return 'raneroufrlo' if k.startswith('ranerou') else k
DREG = {}
for c in C: DREG[dk(c['d'])] = c['r']
DREG['keurmassar'] = 'SN-DK'
rows = {'2023': {}, '2013': {}}
dep_t = collections.defaultdict(lambda: [0] * 6); reg_t = collections.defaultdict(lambda: [0] * 6); nat = [0] * 6
for l in open(SP + 'ansd23.txt', encoding='utf-8').read().split('\n'):
    if not l.strip(): continue
    d, com, v = l.split('|'); v = [int(x) for x in v.split(',')]
    key = (dk(d), norm(com)); assert key not in rows['2023'], key
    rows['2023'][key] = v
    for i in range(6): dep_t[dk(d)][i] += v[i]; reg_t[DREG[dk(d)]][i] += v[i]; nat[i] += v[i]
dep13 = collections.defaultdict(lambda: [0, 0]); reg13 = collections.defaultdict(lambda: [0, 0]); nat13 = [0, 0]
for l in open(SP + 'ansd13.txt', encoding='utf-8').read().split('\n'):
    if not l.strip(): continue
    d, com, v = l.split('|'); v = [int(x) for x in v.split(',')]
    key = (dk(d), norm(com)); assert key not in rows['2013'], key
    rows['2013'][key] = [0, v[1], 0, 0, v[0], 0]
    for i in range(2): dep13[dk(d)][i] += v[i]; reg13[DREG[dk(d)]][i] += v[i]; nat13[i] += v[i]
# Jaxaay-Parcelles : département de Rufisque en 2013, de Keur Massar (compté avec Pikine) en 2023
jx = rows['2013'][('rufisque', 'jaxaayparcellesniakoulrap')]
rows['2013'][('pikine', 'jaxaayparcelles')] = jx
dep13['rufisque'][0] -= jx[4]; dep13['rufisque'][1] -= jx[1]; dep13['pikine'][0] += jx[4]; dep13['pikine'][1] += jx[1]
print('totaux 2023', nat, '2013', nat13, 'départements', len(dep_t), sorted(set(dep_t) - set(DREG)))
def match(year, dept, name):
    pool = {kk[1]: vv for kk, vv in rows[year].items() if kk[0] == dept}
    k = norm(name)
    if k in pool: return pool[k], k
    for kk in (pool if year == '2023' else []):
        if len(k) > 4 and (kk.startswith(k) or k.startswith(kk)): return pool[kk], kk
    best = max(pool, key=lambda kk: difflib.SequenceMatcher(None, k, kk).ratio(), default=None)
    if best and difflib.SequenceMatcher(None, k, best).ratio() >= 0.8: return pool[best], best
    return None, None
out = []; miss23 = []; miss13 = 0; k13s = []
for c in C:
    d = dk(c['d'])
    a, k23 = match('2023', d, c['n'])
    if a is None: miss23.append((c['d'], c['n'])); out.append(None); k13s.append(None); continue
    d13 = 'pikine' if d == 'keurmassar' else d
    b, k13 = match('2013', d13, c['n'])
    if b is None: miss13 += 1
    k13s.append((d13, k13) if b else None)
    out.append([a[0], a[1], a[2], a[3], a[4], a[5], b[4] if b else None, b[1] if b else None])
cnt = collections.Counter(k for k in k13s if k)
for i, k in enumerate(k13s):
    if k and cnt[k] > 1 and out[i]: out[i][6] = out[i][7] = None; print('  2013 ambigu', C[i]['n'], k)
print('communes appariées 2023', sum(1 for o in out if o), '/', len(C), 'sans 2013', miss13)
print('non appariées', miss23)
DEPN = sorted({c['d'] for c in C})
depo = {}
for dn in DEPN:
    k = dk(dn); a = dep_t.get(k); b = dep13.get(k)
    if not a: print('dép. absent', dn, k); continue
    depo[dn] = [a[0], a[1], a[2], a[3], a[4], a[5], b[0] if b else None, b[1] if b else None]
if 'Keur Massar' in depo and 'Pikine' in depo:
    km = depo.pop('Keur Massar'); pk = depo['Pikine']
    depo['Pikine'] = [pk[i] + km[i] if i < 6 else pk[i] for i in range(8)]
rego = {r: [a[0], a[1], a[2], a[3], a[4], a[5], reg13[r][0], reg13[r][1]] for r, a in reg_t.items()}
nato = nat + nat13
for dn, v in depo.items():
    if v[6]: print(f"{dn:20s} {v[4]:>9} {v[6]:>9} {((v[4]/v[6])**.1-1)*100:5.1f}%")
json.dump({'com': out, 'dep': depo, 'reg': rego, 'nat': nato}, open(SP + 'cen.json', 'w'), separators=(',', ':'))
