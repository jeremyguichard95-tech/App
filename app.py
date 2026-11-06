import streamlit as st

st.set_page_config(
    page_title="Sandwich Empire",
    page_icon="🥪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# À remplacer par l'adresse GitHub Pages de ton dépôt après activation de Pages.
GAME_URL = "https://jeremyguichard95-tech.github.io/App/"

st.markdown(
    """
    <style>
      [data-testid="stHeader"] {display: none;}
      [data-testid="stToolbar"] {display: none;}
      .block-container {padding-top: .7rem; padding-bottom: .5rem; max-width: 100%;}
      footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥪 Sandwich Empire")
st.caption("Jeu de gestion — conseillé en mode paysage sur iPhone.")

if "VOTRE-PSEUDO" in GAME_URL or "VOTRE-DEPOT" in GAME_URL:
    st.warning(
        "Il reste à configurer l'adresse GitHub Pages dans app.py. "
        "Remplace VOTRE-PSEUDO et VOTRE-DEPOT par ton identifiant GitHub et le nom du dépôt."
    )
else:
    st.iframe(GAME_URL, height=820, width="stretch", alt="Jeu Sandwich Empire")
    st.markdown(f"[Ouvrir le jeu directement dans Safari]({GAME_URL})")
