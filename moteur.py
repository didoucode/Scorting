"""Backend : système d'inférence flou (SIF) de type Mamdani pour évaluer un Center Back.

Architecture hiérarchique (article « SIF arrière latéral », slide 4) :
  - 4 critères PRINCIPAUX  -> entrent directement dans le SIF final
  - critères SECONDAIRES   -> SIF intermédiaire « Bloc secondaire » -> 1 entrée du SIF final

Méthode (cours de logique floue) :
  fuzzification      : degré de vérité de « V est A » = fonction d'appartenance de A
  ET (conjonction)   : t-norme min
  implication        : Mamdani (min)
  agrégation         : t-conorme max
  défuzzification    : centre de gravité
"""
import itertools
import re
import unicodedata

import numpy as np
import skfuzzy as fuzz

UNIVERS = np.arange(0, 101, 1)
TERMES = ("faible", "moyen", "fort")

N_PRINCIPAUX = 4          # les 4 premiers critères sont principaux
MAX_SECONDAIRES = 4       # 3^4 = 81 règles max pour le bloc secondaire
POIDS_SECONDAIRES = 0.20  # poids du bloc secondaire dans le SIF final
CLES_RESERVEES = {"secondaires", "note"}

# Poids : ordre d'importance, choisis pour reproduire les règles d'exemple de
# l'article (fort-fort-fort-faible -> niveau5, fort-faible-faible-faible -> niveau3,
# faible-fort-faible-faible -> niveau2, ...).
CRITERES_DEFAUT = [
    {"cle": "duels",   "label": "Duels défensifs", "role": "principal", "poids": 0.35},
    {"cle": "aerien",  "label": "Jeu aérien",      "role": "principal", "poids": 0.25},
    {"cle": "vitesse", "label": "Vitesse",         "role": "principal", "poids": 0.20},
    {"cle": "relance", "label": "Relance",         "role": "principal", "poids": 0.20},
]


def creer_cle(label):
    s = unicodedata.normalize("NFD", label.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    cle = re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "critere"
    return cle + "_2" if cle in CLES_RESERVEES else cle


# ---------------------------------------------------------------- variables floues
class _Terme:
    def __init__(self, mf):
        self.mf = mf


class VariableFloue:
    """Variable linguistique (V, X, T_V) : univers X et sous-ensembles flous T_V."""

    def __init__(self, nom):
        self.nom = nom
        self.universe = UNIVERS
        self.terms = {}

    def __setitem__(self, terme, mf):
        self.terms[terme] = _Terme(np.asarray(mf, dtype=float))

    def __getitem__(self, terme):
        return self.terms[terme]

    def appartenance(self, valeur):
        """Fuzzification : degré d'appartenance de la valeur à chaque terme."""
        return {t: float(np.interp(valeur, self.universe, self.terms[t].mf))
                for t in self.terms}


def variable_trois_termes(nom):
    """faible / moyen / fort : trapèzes de l'article (agilité 0-10 ramenée à 0-100)."""
    v = VariableFloue(nom)
    v["faible"] = fuzz.trapmf(UNIVERS, [0, 0, 30, 50])
    v["moyen"] = fuzz.trapmf(UNIVERS, [30, 50, 60, 80])
    v["fort"] = fuzz.trapmf(UNIVERS, [60, 80, 100, 100])
    return v


def variable_niveaux(nom):
    """Sortie : niveau1 à niveau6 (article, slide 3), triangles régulièrement espacés."""
    v = VariableFloue(nom)
    for i, pic in enumerate(range(0, 101, 20), start=1):
        v[f"niveau{i}"] = fuzz.trimf(UNIVERS, [max(pic - 20, 0), pic, min(pic + 20, 100)])
    return v


def fuzzifier(entrees, cle, valeur):
    return entrees[cle].appartenance(valeur)


def niveau_de(note):
    """Niveau 1 à 6 dominant pour une note (frontières à 10, 30, 50, 70, 90)."""
    return 1 + min(5, int((note + 10) // 20))


# ------------------------------------------------------------------ base de règles
def _cibles(score, n):
    """Terme(s) de sortie pour un score 0-1 ; à égalité, on prend les deux voisins."""
    pos = score * (n - 1)
    bas = int(np.floor(pos + 1e-9))
    if abs(pos - bas - 0.5) < 1e-6 and bas + 1 < n:
        return [bas, bas + 1]
    return [min(n - 1, int(round(pos)))]


def generer_regles(poids, n_sorties):
    """Base de règles COMPLÈTE : une règle par combinaison faible/moyen/fort des entrées.

    Le terme de sortie dépend de la somme pondérée des niveaux (0, 1, 2).
    """
    total = float(sum(poids))
    poids = [p / total for p in poids]
    regles = []
    for niveaux in itertools.product(range(3), repeat=len(poids)):
        score = sum(p * n for p, n in zip(poids, niveaux)) / 2
        for cible in _cibles(score, n_sorties):
            regles.append((niveaux, cible))
    return regles


# --------------------------------------------------------------------------- SIF
class SIF:
    """Système d'inférence flou de type Mamdani."""

    def __init__(self, nom, entrees, sortie, poids, label_sortie):
        self.nom = nom
        self.entrees = entrees              # liste de (cle, label, VariableFloue)
        self.sortie = sortie
        self.label_sortie = label_sortie
        self.termes_sortie = list(sortie.terms)
        self.regles = generer_regles(poids, len(self.termes_sortie))

    def inferer(self, valeurs):
        degres = [var.appartenance(valeurs[cle]) for cle, _, var in self.entrees]
        agrege = np.zeros(len(UNIVERS))
        activees = []
        for niveaux, cible in self.regles:
            force = min(d[TERMES[n]] for d, n in zip(degres, niveaux))      # ET = min
            if force > 0:
                mf = self.sortie[self.termes_sortie[cible]].mf
                agrege = np.maximum(agrege, np.minimum(force, mf))           # Mamdani + max
                activees.append((force, niveaux, cible))
        activees.sort(key=lambda r: -r[0])
        valeur = float(fuzz.defuzz(UNIVERS, agrege, "centroid"))             # centre de gravité
        return {"valeur": valeur, "agrege": agrege, "activees": activees}

    def texte(self, niveaux, cible):
        cond = " ET ".join(f"{lab} est {TERMES[n]}"
                           for (_, lab, _), n in zip(self.entrees, niveaux))
        return f"SI {cond} ALORS {self.label_sortie} est {self.termes_sortie[cible]}"

    def regles_texte(self):
        return [self.texte(n, c) for n, c in self.regles]


# ------------------------------------------------------------------------ modèle
class ModeleCB:
    """4 critères principaux + critères secondaires (bloc intermédiaire)."""

    def __init__(self, criteres):
        if len(criteres) < N_PRINCIPAUX:
            raise ValueError(f"Il faut au moins {N_PRINCIPAUX} critères principaux.")
        if len(criteres) - N_PRINCIPAUX > MAX_SECONDAIRES:
            raise ValueError(f"Maximum {MAX_SECONDAIRES} critères secondaires.")

        self.criteres = criteres
        self.principaux = criteres[:N_PRINCIPAUX]
        self.secondaires = criteres[N_PRINCIPAUX:]
        self.entrees = {c["cle"]: variable_trois_termes(c["cle"]) for c in criteres}
        self.note = variable_niveaux("note")
        self.bloc = None
        self.sif_secondaire = None

        entrees_finales = [(c["cle"], c["label"], self.entrees[c["cle"]])
                           for c in self.principaux]
        poids_p = [c.get("poids", 1) for c in self.principaux]

        if self.secondaires:
            self.bloc = variable_trois_termes("secondaires")
            self.sif_secondaire = SIF(
                "Bloc secondaire",
                [(c["cle"], c["label"], self.entrees[c["cle"]]) for c in self.secondaires],
                self.bloc,
                [c.get("poids", 1) for c in self.secondaires],
                "Bloc secondaire",
            )
            total = float(sum(poids_p))
            poids_final = [p / total * (1 - POIDS_SECONDAIRES) for p in poids_p]
            poids_final.append(POIDS_SECONDAIRES)
            entrees_finales.append(("secondaires", "Bloc secondaire", self.bloc))
        else:
            poids_final = poids_p

        self.sif_final = SIF("Niveau du joueur", entrees_finales, self.note,
                             poids_final, "Niveau")

    def evaluer(self, valeurs):
        """valeurs = {cle: 0-100}. Retourne la note, le niveau et le détail du raisonnement."""
        valeurs = dict(valeurs)
        bloc = None
        if self.sif_secondaire:
            bloc = self.sif_secondaire.inferer(valeurs)
            valeurs["secondaires"] = bloc["valeur"]
        final = self.sif_final.inferer(valeurs)
        return {
            "note": final["valeur"],
            "niveau": niveau_de(final["valeur"]),
            "bloc": bloc["valeur"] if bloc else None,
            "agrege": final["agrege"],
            "activees": [(f, self.sif_final.texte(n, c)) for f, n, c in final["activees"]],
            "activees_bloc": ([(f, self.sif_secondaire.texte(n, c))
                               for f, n, c in bloc["activees"]] if bloc else []),
        }

    def regles_texte(self):
        base = {}
        if self.sif_secondaire:
            base[self.sif_secondaire.nom] = self.sif_secondaire.regles_texte()
        base[self.sif_final.nom] = self.sif_final.regles_texte()
        return base


def verdict(valeur_note):
    n = niveau_de(valeur_note)
    if valeur_note >= 70:
        return "recommande", f"✅ Recommandé : niveau {n}/6, à utiliser comme CB"
    if valeur_note >= 50:
        return "moyen", f"⚠️ À considérer : niveau {n}/6, profil moyen"
    return "rejete", f"❌ Non recommandé : niveau {n}/6 pour le poste de CB"