"""Assemble l'application monofichier index.html à partir de src/ et data/.

Usage : python3 build.py
"""
import json, os
ROOT = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ROOT, 'data')
def load(n): return json.load(open(os.path.join(D, n), encoding='utf-8'))

G = load('geodata.json')
G['com'] = load('communes2.json')          # communes : contours, population, équipements OSM
G['osm'] = load('osm.json')                # points OSM classés, lieux habités, voies ferrées
G['A'] = load('ansd_reg.json')             # tableaux régionaux du RGPH-5 (rapport définitif)
cen = load('cen.json')                     # répertoire des localités ANSD agrégé
G['cen'], G['cenD'], G['cenR'], G['cenN'] = cen['com'], cen['dep'], cen['reg'], cen['nat']
for c in G['com']:
    c.pop('g', None)

data = json.dumps(G, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
tpl = open(os.path.join(ROOT, 'src', 'template4.html'), encoding='utf-8').read()
css = open(os.path.join(ROOT, 'src', 'css2.css'), encoding='utf-8').read()
body = tpl.replace('__CSS__', css).replace('const G = __DATA__;', 'const G = ' + data + ';')
assert '__DATA__' not in body and '__CSS__' not in body
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="description" content="Observatoire des territoires du Sénégal (CEGIT) : cartes, indicateurs ANSD et OpenStreetMap, analyse territoriale, tableaux de bord, stratégie et portraits de territoire.">\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(html)
print('index.html :', os.path.getsize(os.path.join(ROOT, 'index.html')), 'octets')
