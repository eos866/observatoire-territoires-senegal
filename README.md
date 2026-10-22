# Observatoire des territoires du Sénégal

Application web de **CEGIT** (Centre d'Expertise en Géomatique et Ingénierie Territoriale) pour explorer, comparer et analyser les **14 régions, 46 départements et 558 communes** du Sénégal, puis produire leur **portrait de territoire**.

Mise en ligne (GitHub Pages) : https://eos866.github.io/observatoire-territoires-senegal/

L'application tient dans un seul fichier, `index.html`, qui contient les données. Elle fonctionne sans serveur ni base de données : il suffit de l'ouvrir dans un navigateur.

## Fonctionnalités

| Vue | Contenu |
|---|---|
| **Explorer la carte** | Carte en aplats ou en cercles proportionnels (régions, départements, communes), avec la possibilité de superposer un second indicateur. Indicateurs rangés par thématiques repliables. Fiche du territoire : valeur, rang, comparaison au Sénégal, équipements OpenStreetMap. Couches à pictogrammes : routes, voies ferrées, villes et villages, santé, universités, 12 catégories d'équipements OSM. Plein écran et export PNG. |
| **Analyse territoriale** | Écart à la médiane des territoires de même niveau, profil en radar, atouts et points de vigilance, flux énergétiques des ménages (Sankey), fiches didactiques (objectif, diagnostic, indicateurs, leviers d'action). |
| **Tableaux de bord** | Tableaux sur mesure : carte, chiffre clé, comparaison, classement, jauge, anneau, barres. Modèle « Portrait complet (toutes thématiques) ». Export Excel et PNG. |
| **Stratégie territoriale** | Prospective 2023-2050 : trajectoire démographique réglable (tableau ou points à faire glisser), plan d'actions, impacts comparés au fil de l'eau, scénarios enregistrés, export Excel. |
| **Rapport du territoire** | Portrait A4 de 10 pages : présentation, démographie, habitat, économie, social, mobilité, environnement, attractivité, tourisme, sources. Export **PDF** et **Word (.docx)**. |
| **Comparer · Données · Sources** | Comparaison de 5 territoires au plus, tableau triable et filtrable exportable en **Excel** et **CSV**, documentation des sources et de la méthode. |

Les tableaux de bord et les scénarios sont enregistrés dans le navigateur de chaque utilisateur (`localStorage`). Le mode sombre suit le réglage du système.

## Sources des données

| Donnée | Producteur | Millésime | Échelle |
|---|---|---|---|
| Population, superficie, urbanisation | ANSD, RGPH-5 | 2023 | Région |
| Habitat, éclairage, cuisson, activité, alphabétisation, migrations, agriculture | ANSD, RGPH-5, rapport définitif | 2023 | Région, urbain, rural |
| Ménages, concessions, hommes, femmes, localités, population 2013 | ANSD, répertoire des localités | 2013, 2023 | Agrégé par commune |
| Population des départements et communes | Vie-Publique.sn (référentiel RGPH 2023) | 2023 | Département, commune |
| Pauvreté monétaire | ANSD, EHCVM II | 2021-2022 | Région (8 sur 14) |
| Équipements, lieux habités, voies ferrées | OpenStreetMap, exports HOT (HDX) | oct. 2026 | Point, ligne |
| Santé publique, routes classées, universités | DTGC, diffusé par le projet mapSenegal | n.c. | Point, ligne |
| Limites administratives | GADM 4.1 | 2022 | Région, département, commune |

**Licences.** Données OpenStreetMap © contributeurs OpenStreetMap, licence ODbL. Les limites GADM sont sous licence **non commerciale** : pour un usage commercial, il faut les remplacer par les limites officielles (DTGC, ANAT) ou par geoBoundaries (CC BY 4.0).

## Organisation du dépôt

```
index.html            application assemblée, publiée sur GitHub Pages
build.py              assemble index.html à partir de src/ et data/
src/template4.html    interface : HTML, styles propres aux vues, JavaScript
src/css2.css          feuille de style de base, insérée dans le gabarit
data/                 données préparées en JSON, injectées dans index.html
  geodata.json        départements, régions, santé et routes (DTGC)
  communes.json       communes : contours GADM, population, statistiques DTGC
  communes2.json      communes enrichies des comptages OpenStreetMap
  osm.json            points OSM classés, villes et villages, voies ferrées
  ansd_reg.json       tableaux régionaux du RGPH-5 (rapport définitif)
  cen.json            répertoire des localités ANSD agrégé (communes, départements, régions)
  ansd23.txt / ansd13.txt / communes_vp.txt   données sources saisies
scripts/              chaîne de préparation des données (Python 3, sans dépendance)
tests/                tests de bout en bout (Playwright pour Python)
```

## Mettre à jour l'application

Après une modification de `src/` ou de `data/` :

```bash
python3 build.py
```

Pour régénérer les données à partir des sources brutes, placez les fichiers dans `raw/` (dossier ignoré par git), puis lancez les scripts dans l'ordre :

```bash
# couches DTGC du projet mapSenegal (https://github.com/mapSenegal/mapSenegal)
git clone --depth 1 https://github.com/mapSenegal/mapSenegal raw/mapSenegal
python3 scripts/process.py      # départements, régions, santé, routes
python3 scripts/communes.py     # communes : appariement GADM / référentiel, statistiques
# exports OpenStreetMap HOT (HDX) décompressés dans raw/osm/<thème>/
python3 scripts/osm.py          # classement OSM, rattachement aux communes
python3 scripts/ansd_reg.py     # tableaux régionaux RGPH-5
python3 scripts/cen.py          # répertoire des localités ANSD
python3 build.py
```

Pour utiliser d'autres emplacements, définissez les variables `MAPSENEGAL_RDS` et `OSM_DIR`.

## Tests

```bash
pip install playwright        # le navigateur Chromium doit être installé
python3 tests/test11.py       # carte, analyse, tableaux de bord, stratégie (ordinateur et mobile)
python3 tests/test5.py SN-DK  # rapport de 10 pages et export Word pour un territoire
python3 tests/test_x.py       # exports Excel et CSV du tableau de données
```

## Limites connues

- 125 communes, surtout urbaines, n'ont pas de contour dans GADM. Elles sont localisées par un point, et les équipements OSM proches leur sont rattachés.
- OpenStreetMap est contributif : sa couverture varie selon les territoires. Les comptages servent à comparer, pas à faire un inventaire.
- Certains indicateurs ne sont publiés par l'ANSD qu'à l'échelle régionale. Ils portent la mention « (région) » dans les fiches et les rapports des départements et des communes.
- Le département de Keur Massar, créé en 2021, est compté avec Pikine.

---

© 2026 CEGIT · Document d'information, sans valeur officielle · [cegitgroup.com](https://cegitgroup.com)
