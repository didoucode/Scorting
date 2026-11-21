import html
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from moteur import (CRITERES_DEFAUT, MAX_SECONDAIRES, N_PRINCIPAUX, ModeleCB,
                    creer_cle, fuzzifier, verdict)

st.set_page_config(page_title="CB Scout", page_icon="⚽", layout="wide")

VERT, VERT_FONCE, BLEU, ROUGE = "#16A34A", "#166534", "#2563EB", "#DC2626"
TEXTE = "#0F2A1A"
COULEURS = {
    3: [BLEU, "#6B7280", VERT],
    6: ["#93C5FD", "#3B82F6", "#14B8A6", "#4ADE80", "#22C55E", "#15803D"],
}

# niveau -> (fond du badge, texte du badge, couleur de la barre)
NIVEAUX = {
    "Faible": ("#FEE2E2", "#B91C1C", "#F87171"),
    "Moyen":  ("#DBEAFE", "#1D4ED8", "#3B82F6"),
    "Fort":   ("#DCFCE7", "#166534", "#16A34A"),
}

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1200px;}

.hero {position: relative; overflow: hidden; border-radius: 18px;
  padding: 28px 32px; margin-bottom: 22px;
  background: repeating-linear-gradient(90deg, #15803D 0, #15803D 70px, #16A34A 70px, #16A34A 140px);
  box-shadow: 0 8px 24px rgba(22,101,52,.25);}
.hero::before {content: ""; position: absolute; right: -60px; top: 50%;
  width: 220px; height: 220px; margin-top: -110px;
  border: 3px solid rgba(255,255,255,.35); border-radius: 50%;}
.hero::after {content: ""; position: absolute; right: 49px; top: 0; bottom: 0;
  width: 3px; background: rgba(255,255,255,.35);}
.hero-tag {display: inline-block; background: #fff; color: #166534; font-weight: 700;
  font-size: .72rem; letter-spacing: 1px; padding: 3px 12px; border-radius: 20px;
  margin-bottom: 10px; position: relative; z-index: 1;}
.hero-titre {color: #fff; font-size: 2.2rem; font-weight: 800;
  position: relative; z-index: 1;}
.hero-sous {color: #DCFCE7; margin-top: 4px; position: relative; z-index: 1;}

.carte {background: #fff; border: 1px solid #D1FAE5; border-radius: 16px;
  padding: 22px; box-shadow: 0 4px 14px rgba(22,101,52,.08);}
.joueur {display: flex; align-items: center; gap: 14px; margin-bottom: 14px;}
.avatar {width: 54px; height: 54px; border-radius: 50%; background: #16A34A;
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 1.2rem;}
.joueur-nom {font-size: 1.25rem; font-weight: 700; color: #0F2A1A;}
.poste {display: inline-block; background: #DCFCE7; color: #166534; font-weight: 700;
  font-size: .75rem; padding: 2px 10px; border-radius: 20px;}

.anneau {width: 190px; height: 190px; border-radius: 50%; margin: 6px auto;
  display: flex; align-items: center; justify-content: center;}
.anneau-int {width: 150px; height: 150px; border-radius: 50%; background: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;}
.score {font-size: 3rem; font-weight: 800; line-height: 1;}
.sur {color: #6B7280; font-size: .85rem;}
.niveau {text-align: center; font-weight: 700; color: #166534; margin-top: 8px;}
.verdict {text-align: center; border-radius: 10px; padding: 12px;
  font-weight: 700; margin-top: 12px;}
.seuils {display: flex; gap: 6px; margin-top: 14px; font-size: .72rem; color: #4B5563;}
.seuils span {flex: 1; text-align: center; border-radius: 8px; padding: 4px 2px;
  background: #F3F4F6;}

.titre-section {font-size: 1.1rem; font-weight: 700; color: #166534; margin-bottom: 14px;}
.ligne {display: flex; align-items: center; gap: 12px; margin-bottom: 14px;}
.ligne-nom {width: 150px; font-weight: 600; color: #0F2A1A; font-size: .92rem;}
.ligne-nom small {display: block; color: #6B7280; font-weight: 400; font-size: .72rem;}
.barre {flex: 1; height: 12px; background: #E5F5EA; border-radius: 8px; overflow: hidden;}
.barre-rempli {height: 100%; border-radius: 8px;}
.valeur {width: 34px; text-align: right; font-weight: 700; color: #0F2A1A;}
.pill {width: 62px; text-align: center; font-size: .75rem; font-weight: 700;
  padding: 3px 0; border-radius: 20px;}

.stTabs [data-baseweb="tab"] {font-weight: 600;}
</style>
""", unsafe_allow_html=True)


def bloc(s):
    """Retire l'indentation pour que Streamlit lise le HTML (pas du code)."""
    return "\n".join(l.strip() for l in s.splitlines() if l.strip())


# --- Critères (4 principaux fixes + secondaires ajoutables) ---
if ("criteres" not in st.session_state
        or any("poids" not in c for c in st.session_state.criteres)):
    st.session_state.criteres = [dict(c) for c in CRITERES_DEFAUT]
criteres = st.session_state.criteres


@st.cache_resource
def moteur_pour(signature):
    liste = [dict(cle=c, label=l, role=r, poids=p) for c, l, r, p in signature]
    return ModeleCB(liste)


signature = tuple((c["cle"], c["label"], c["role"], c.get("poids", 1)) for c in criteres)
modele = moteur_pour(signature)
entrees, note = modele.entrees, modele.note

# --- Barre latérale ---
with st.sidebar:
    st.markdown("### ⚽ Fiche joueur")
    nom = st.text_input("Nom du joueur", "Joueur 1")
    st.caption("Poste : Défenseur central (CB)")

    st.markdown("### Critères (0 à 100)")
    valeurs = {}
    for c in criteres:
        etoile = " ★" if c["role"] == "principal" else ""
        valeurs[c["cle"]] = st.slider(c["label"] + etoile, 0, 100, 50, key="s_" + c["cle"])
    st.caption(f"★ = {N_PRINCIPAUX} critères principaux · les autres sont secondaires")

    nb_sec = len(criteres) - N_PRINCIPAUX
    with st.expander("➕ Ajouter un critère secondaire"):
        if nb_sec >= MAX_SECONDAIRES:
            st.info(f"Maximum atteint : {MAX_SECONDAIRES} critères secondaires.")
        else:
            with st.form("ajout", clear_on_submit=True):
                label = st.text_input("Nom du critère")
                ok = st.form_submit_button("Ajouter")
            if ok and label.strip():
                existantes = {c["cle"] for c in criteres}
                base = creer_cle(label)
                cle, i = base, 2
                while cle in existantes:
                    cle = f"{base}_{i}"
                    i += 1
                criteres.append({"cle": cle, "label": label.strip(),
                                 "role": "secondaire", "poids": 1})
                st.rerun()

    with st.expander("🗑️ Supprimer un critère secondaire"):
        secondaires = [c["label"] for c in criteres if c["role"] == "secondaire"]
        if secondaires:
            a_suppr = st.selectbox("Critère", secondaires)
            if st.button("Supprimer"):
                st.session_state.criteres = [c for c in criteres if c["label"] != a_suppr]
                st.rerun()
        else:
            st.caption("Aucun critère secondaire.")

# --- Calcul ---
calcul = modele.evaluer(valeurs)
resultat = calcul["note"]
statut, message = verdict(resultat)
couleur = {"recommande": VERT, "moyen": BLEU, "rejete": ROUGE}[statut]

degres, niveaux = {}, {}
for c in criteres:
    d = fuzzifier(entrees, c["cle"], valeurs[c["cle"]])
    degres[c["cle"]] = d
    niveaux[c["cle"]] = max(d, key=d.get).capitalize()

# --- Bannière ---
st.markdown(bloc("""
<div class="hero">
<div class="hero-tag">SCOUTING • LOGIQUE FLOUE</div>
<div class="hero-titre">⚽ CB Scout</div>
<div class="hero-sous">Rapport d'évaluation d'un défenseur central</div>
</div>
"""), unsafe_allow_html=True)


# --- Graphiques ---
def style_axes(fig, ax):
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F0FDF4")
    ax.tick_params(colors=TEXTE)
    for s in ax.spines.values():
        s.set_color("#BBF7D0")


def radar(labels, vals):
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    vals, angles = vals + vals[:1], angles + angles[:1]
    fig, ax = plt.subplots(figsize=(4.2, 4.2), subplot_kw=dict(polar=True))
    style_axes(fig, ax)
    ax.plot(angles, vals, color=VERT, linewidth=2)
    ax.fill(angles, vals, color=VERT, alpha=0.3)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXTE, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_yticklabels([])
    ax.grid(color="#BBF7D0")
    return fig


def ligne(label, sous_titre, valeur, niveau):
    bg, fg, barre = NIVEAUX[niveau]
    return (
        f'<div class="ligne">'
        f'<div class="ligne-nom">{html.escape(label)}<small>{sous_titre}</small></div>'
        f'<div class="barre"><div class="barre-rempli" '
        f'style="width:{valeur:.0f}%;background:{barre}"></div></div>'
        f'<div class="valeur">{valeur:.0f}</div>'
        f'<div class="pill" style="background:{bg};color:{fg}">{niveau}</div>'
        f'</div>'
    )


tab1, tab2, tab3, tab4 = st.tabs(
    ["🎯 Évaluation", "📈 Fonctions d'appartenance", "🧠 Raisonnement", "📋 Règles"])

with tab1:
    col_a, col_b = st.columns([1, 1.4], gap="large")

    with col_a:
        initiales = html.escape("".join(m[0] for m in nom.split()[:2]).upper() or "?")
        pct = int(round(resultat))
        st.markdown(bloc(f"""
        <div class="carte">
        <div class="joueur">
        <div class="avatar">{initiales}</div>
        <div><div class="joueur-nom">{html.escape(nom)}</div><span class="poste">CB • Défenseur central</span></div>
        </div>
        <div class="anneau" style="background: conic-gradient({couleur} {pct}%, #E5F5EA 0);">
        <div class="anneau-int">
        <div class="score" style="color:{couleur}">{resultat:.1f}</div>
        <div class="sur">/ 100</div>
        </div>
        </div>
        <div class="niveau">Niveau {calcul["niveau"]} / 6</div>
        <div class="verdict" style="background:{couleur}1A; color:{couleur}; border:1px solid {couleur}">{message}</div>
        <div class="seuils"><span>&lt; 50<br>Non retenu</span><span>50 – 70<br>À considérer</span><span>≥ 70<br>Recommandé</span></div>
        </div>
        """), unsafe_allow_html=True)

    with col_b:
        lignes_html = "".join(
            ligne(c["label"], "Principal" if c["role"] == "principal" else "Secondaire",
                  valeurs[c["cle"]], niveaux[c["cle"]])
            for c in criteres)
        if modele.bloc is not None:
            d = modele.bloc.appartenance(calcul["bloc"])
            lignes_html += ligne("Bloc secondaire", "Synthèse des secondaires",
                                 calcul["bloc"], max(d, key=d.get).capitalize())
        st.markdown(
            f'<div class="carte"><div class="titre-section">Profil technique</div>{lignes_html}</div>',
            unsafe_allow_html=True,
        )

    st.write("")
    col_c, col_d = st.columns([1, 1.4], gap="large")

    with col_c:
        if len(criteres) >= 3:
            st.pyplot(radar([c["label"] for c in criteres],
                            [valeurs[c["cle"]] for c in criteres]))
        else:
            st.info("Ajoute un 3e critère pour voir le radar du joueur.")

    with col_d:
        st.markdown('<div class="titre-section">Détail de la fuzzification</div>',
                    unsafe_allow_html=True)
        lignes = [{
            "Critère": c["label"],
            "Valeur": valeurs[c["cle"]],
            "Niveau": niveaux[c["cle"]],
            "Faible": round(degres[c["cle"]]["faible"], 2),
            "Moyen": round(degres[c["cle"]]["moyen"], 2),
            "Fort": round(degres[c["cle"]]["fort"], 2),
        } for c in criteres]
        st.dataframe(pd.DataFrame(lignes).set_index("Critère"))

with tab2:
    options = [c["label"] for c in criteres] + ["Note finale (sortie)"]
    if modele.bloc is not None:
        options.append("Bloc secondaire (sortie intermédiaire)")
    choix = st.selectbox("Variable", options)
    if choix == "Note finale (sortie)":
        var, marque = note, resultat
    elif choix.startswith("Bloc secondaire"):
        var, marque = modele.bloc, calcul["bloc"]
    else:
        c = next(c for c in criteres if c["label"] == choix)
        var, marque = entrees[c["cle"]], valeurs[c["cle"]]
    fig, ax = plt.subplots(figsize=(7, 3))
    style_axes(fig, ax)
    for terme, col in zip(var.terms, COULEURS[len(var.terms)]):
        ax.plot(var.universe, var[terme].mf, label=terme, color=col, linewidth=2)
        ax.fill_between(var.universe, var[terme].mf, color=col, alpha=0.12)
    ax.axvline(marque, color=ROUGE, linestyle="--", label="valeur actuelle")
    ax.legend(facecolor="#FFFFFF", labelcolor=TEXTE, ncol=2)
    st.pyplot(fig)

with tab3:
    st.caption("ET = min (t-norme) · implication de Mamdani = min · "
               "agrégation = max (t-conorme) · défuzzification = centre de gravité")
    st.markdown('<div class="titre-section">Sortie floue agrégée et centre de gravité</div>',
                unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(7, 3))
    style_axes(fig, ax)
    ax.fill_between(note.universe, calcul["agrege"], color=VERT, alpha=0.35)
    ax.plot(note.universe, calcul["agrege"], color=VERT, linewidth=2)
    ax.axvline(resultat, color=ROUGE, linestyle="--", label=f"centre de gravité = {resultat:.1f}")
    ax.set_ylim(0, 1.05)
    ax.legend(facecolor="#FFFFFF", labelcolor=TEXTE)
    st.pyplot(fig)

    st.markdown('<div class="titre-section">Règles activées (chevauchement des ensembles)</div>',
                unsafe_allow_html=True)
    st.caption(f"{len(calcul['activees'])} règles du SIF final se déclenchent ; les 8 plus fortes :")
    st.dataframe(pd.DataFrame(
        [{"Force": round(f, 2), "Règle": t} for f, t in calcul["activees"][:8]]
    ), hide_index=True)
    if calcul["activees_bloc"]:
        st.caption(f"{len(calcul['activees_bloc'])} règles du bloc secondaire se déclenchent ; "
                   "les 5 plus fortes :")
        st.dataframe(pd.DataFrame(
            [{"Force": round(f, 2), "Règle": t} for f, t in calcul["activees_bloc"][:5]]
        ), hide_index=True)

with tab4:
    st.caption("Architecture : les 4 critères principaux entrent dans le SIF final ; "
               "les critères secondaires passent d'abord par un SIF intermédiaire (bloc secondaire) "
               "dont la sortie est la 5e entrée du SIF final. "
               "Bases de règles complètes générées automatiquement.")
    for nom_sif, regles in modele.regles_texte().items():
        with st.expander(f"{nom_sif} : {len(regles)} règles"):
            st.code("\n".join(regles))