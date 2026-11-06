# Sandwich Empire — navigateur + Streamlit

Ce dépôt contient deux parties complémentaires :

- `main.py` : le jeu Pygame adapté à la boucle asynchrone Pygbag.
- `.github/workflows/deploy-game.yml` : compile le jeu dans GitHub Actions et publie `build/web` sur GitHub Pages à chaque mise à jour de `main`.
- `app.py` : portail Streamlit qui intègre le jeu publié sur GitHub Pages.
- `requirements.txt` : dépendance du portail Streamlit uniquement. Pygbag est installé par le workflow GitHub Actions.

## Configuration à faire une seule fois

1. Remplacer `VOTRE-PSEUDO` et `VOTRE-DEPOT` dans `app.py` par l'identifiant GitHub et le nom du dépôt.
2. Dans GitHub, ouvrir **Settings → Pages** et choisir **GitHub Actions** comme source de publication si demandé.
3. Dans **Settings → Actions → General**, vérifier que les permissions du workflow autorisent les actions Pages. Le workflow utilise les permissions `pages: write` et `id-token: write`.
4. Dans **Actions**, lancer `Build and deploy Sandwich Empire (Pygbag)` avec **Run workflow**, ou pousser un commit sur `main`.
5. Attendre que les deux jobs `build` et `deploy` soient verts. L'adresse du jeu sera `https://VOTRE-PSEUDO.github.io/VOTRE-DEPOT/`.
6. Sur Streamlit Community Cloud, déployer `app.py` depuis ce dépôt, branche `main`, avec `requirements.txt` à la racine.

## Important

- GitHub Pages gratuit nécessite généralement un dépôt public. Le code du jeu sera donc visible publiquement. Ne publie pas de secrets ni de données privées dans ce dépôt.
- Le portail Streamlit ne fait pas tourner Pygame : il affiche dans une iframe la version navigateur compilée et hébergée par GitHub Pages.
- Les sauvegardes web sont prévues dans le stockage local du navigateur. Elles sont propres au navigateur/appareil et ne se synchronisent pas automatiquement.
- Le premier portage conserve une surface de jeu 1180 × 740. Pour le confort sur iPhone, commence en mode paysage. Une optimisation tactile et responsive plus poussée pourra être faite après le premier test réel.
- Aucune image externe n'est requise : le jeu dessine déjà ses illustrations de sandwichs et icônes en Python, et dispose d'un rendu de secours si aucun asset personnalisé n'est présent.
