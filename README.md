# ⚽ CB Scout : évaluation d'un Center Back par logique floue

Application Python qui note un joueur pour le poste de **défenseur central (CB)**
à partir de critères numériques (0 à 100) et dit s'il est **recommandé ou non**.
Le calcul repose sur un **système d'inférence flou (SIF) de type Mamdani**.

## Principe en 5 étapes

1. **Saisie** : l'utilisateur entre une valeur de 0 à 100 pour chaque critère (curseurs).
2. **Fuzzification** : chaque valeur devient un niveau linguistique **faible / moyen / fort**,
   avec un degré d'appartenance entre 0 et 1. Les ensembles se **chevauchent** : 70 est à la fois
   un peu « moyen » et un peu « fort ».
3. **Inférence** : des règles `SI ... ET ... ALORS niveau est ...` se déclenchent avec une force
   donnée par le **min** des degrés (t-norme).
4. **Agrégation et défuzzification** : les résultats des règles sont fusionnés (max), puis la
   **note finale** est le centre de gravité de la forme obtenue.
5. **Décision** : la note donne un niveau (1 à 6) et un verdict.

| Note | Niveau | Verdict |
|---|---|---|
| ≥ 70 | 5 à 6 | ✅ Recommandé |
| 50 à 70 | 4 | ⚠️ À considérer |
| < 50 | 1 à 3 | ❌ Non recommandé |

## Lancer le projet

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

L'interface s'ouvre dans le navigateur sur `http://localhost:8501`
(utiliser Chrome ou Firefox : Streamlit s'affiche mal sur un vieux Safari).

## Structure du dépôt

| Fichier | Rôle |
|---|---|
| `moteur.py` | **Backend** : toute la logique floue (aucun code d'interface) |
| `app.py` | **Interface** Streamlit (curseurs, carte joueur, graphiques) |
| `.streamlit/config.toml` | Thème clair, vert |
| `requirements.txt` | Dépendances Python |

Règle d'or : **`app.py` ne contient aucun calcul flou**, il appelle seulement `moteur.py`.

## Architecture du modèle (`moteur.py`)

Le modèle suit l'article *« Application des SIF dans le football : étude de cas Arrière Latéral »*
(Ramdani & Machaa, IAF'2025), qui utilise des sous-systèmes flous reliés à un système final.

```
 4 critères PRINCIPAUX ──────────────────────────┐
 (duels, aérien, vitesse, relance)               ▼
                                          ┌─────────────┐
 critères SECONDAIRES ─► SIF bloc ───────►│  SIF final  │──► note 0-100 ──► niveau 1-6
 (ajoutés par l'utilisateur)  secondaire  └─────────────┘
```

- Les **4 premiers critères sont principaux** et entrent directement dans le SIF final.
- Tout critère **ajouté** est **secondaire** (4 au maximum). Les secondaires passent d'abord par
  un SIF intermédiaire dont la sortie est la 5ᵉ entrée du SIF final (poids 20 %).
- Ce découpage évite l'explosion du nombre de règles (3ⁿ règles pour n entrées).

### Variables linguistiques

- **Entrées** (chaque critère, 0 à 100) : trapèzes `faible (0,0,30,50)`, `moyen (30,50,60,80)`,
  `fort (60,80,100,100)`, ceux de l'article (agilité, 0-10) ramenés à 0-100.
- **Sortie** : `niveau1` à `niveau6`, triangles régulièrement espacés tous les 20 points.

### Base de règles

La base est **complète** : une règle par combinaison faible / moyen / fort des entrées
(81 règles pour 4 entrées). Elle est **générée automatiquement** (`generer_regles`) :

1. chaque critère a un **poids** (duels 0.35, aérien 0.25, vitesse 0.20, relance 0.20) ;
2. on calcule le score pondéré de la combinaison (faible = 0, moyen = 1, fort = 2) ;
3. ce score donne le niveau de sortie le plus proche.

Quand le score tombe exactement entre deux niveaux (ex. tout « moyen »), deux règles sont
créées (niveaux 3 et 4), d'où 94 règles au lieu de 81. Les poids reproduisent les règles d'exemple de l'article
(fort-fort-fort-fort → niveau6, fort-fort-fort-faible → niveau5, fort-faible-faible-faible → niveau3...).

### Opérateurs (cours de logique floue)

| Opération | Choix |
|---|---|
| ET | t-norme **min** |
| Implication | **Mamdani** (min) |
| Agrégation | t-conorme **max** |
| Défuzzification | **centre de gravité** (`skfuzzy.defuzz`) |

### Contenu de `moteur.py`

| Élément | Rôle |
|---|---|
| `CRITERES_DEFAUT` | Les 4 critères principaux, leurs poids |
| `VariableFloue` | Variable linguistique : univers 0-100 + ensembles flous ; `appartenance(x)` = fuzzification |
| `variable_trois_termes()` / `variable_niveaux()` | Créent les ensembles des entrées et de la sortie |
| `generer_regles()` | Construit la base de règles complète à partir des poids |
| `SIF` | Un système Mamdani : `inferer()` calcule fuzzification, règles, agrégation, centre de gravité |
| `ModeleCB` | Assemble les SIF (principaux, bloc secondaire, final) ; `evaluer(valeurs)` renvoie note, niveau et détail |
| `niveau_de()` / `verdict()` | Transforment la note en niveau 1-6 et en décision |

## Interface (`app.py`)

- **Barre latérale** : nom du joueur, curseurs des critères, ajout / suppression d'un critère secondaire.
- **🎯 Évaluation** : note, niveau, verdict, profil par critère, radar, détail de la fuzzification.
- **📈 Fonctions d'appartenance** : courbes de chaque variable avec la valeur courante.
- **🧠 Raisonnement** : sortie floue agrégée, centre de gravité, règles activées.
- **📋 Règles** : toutes les règles générées, en français.

## Exemples de résultats

| Joueur (duels, aérien, vitesse, relance) | Note | Niveau |
|---|---|---|
| 85, 80, 70, 60 | 82.4 | 5 |
| 50, 50, 50, 50 | 50.0 | 4 |
| 20, 30, 50, 50 | 20.0 | 2 |
| 100, 100, 100, 100 | 93.3 | 6 |

La note maximale est d'environ 93, car c'est le centre de gravité du niveau 6.

## Modifier le modèle

- **Poids des critères** : champ `poids` dans `CRITERES_DEFAUT` (`moteur.py`).
- **Poids du bloc secondaire** : constante `POIDS_SECONDAIRES`.
- **Forme des ensembles** : `variable_trois_termes()` et `variable_niveaux()`.
- **Seuils de décision** : fonction `verdict()`.
- **Nombre max de critères secondaires** : `MAX_SECONDAIRES`.

## Évolutions prévues

- Charger un **dataset de joueurs** (CSV) et classer automatiquement les meilleurs CB.
- Ajuster les ensembles et les poids avec des données réelles.

## Références

- Cours *Logique floue et applications*, M. Ramdani.
- M. Ramdani & L. Machaa, *Application des SIF dans le football : étude de cas Arrière Latéral*, IAF'2025.