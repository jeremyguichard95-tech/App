# Sandwich Empire — version navigateur (Pygbag)

Cette version remplace le lancement Streamlit par Pygbag, qui exécute Pygame dans le navigateur via WebAssembly.

## Structure

- `main.py` : jeu Pygame adapté à la boucle asynchrone du navigateur.
- `requirements.txt` : dépendances pour préparer/tester le projet en local.
- `assets/` : à ajouter si tu as des images personnalisées ; le jeu génère déjà des illustrations de secours.

## Préparation sur un ordinateur

Dans un terminal, depuis le dossier du projet :

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pygbag .
```

Ouvre ensuite `http://localhost:8000` dans un navigateur. Le premier chargement peut être long.

## Publication

Après validation locale, construire le site statique :

```bash
python -m pygbag --build .
```

Le site généré se trouve dans `build/web/`. Il faut publier **le contenu** de ce dossier sur un hébergement statique compatible HTTPS (par exemple GitHub Pages). Ne pas déployer cette version sur Streamlit Community Cloud.

## Sauvegardes

Dans le navigateur, les sauvegardes manuelle et automatique sont stockées dans `localStorage` du navigateur. Elles sont propres à cet appareil et à ce navigateur : elles ne se synchronisent pas automatiquement entre iPhone et ordinateur. Effacer les données du site peut les supprimer.

## À savoir pour iPhone

Le portage technique ne suffit pas à rendre l'interface confortable sur un petit écran : le jeu utilise une surface fixe de 1180 × 740 et des coordonnées de boutons conçues pour ordinateur. Le premier test doit se faire en mode paysage. Une vraie expérience mobile demandera ensuite une refonte responsive des écrans, tailles de texte, panneaux et commandes tactiles.
