# 🍳 Guide de recettes

Transforme un dossier de recettes en PDF (et en photos) en un **guide interactif** :
une seule page web avec des cartes illustrées, une recherche dans le contenu des
recettes, des favoris et des notes. Le guide se consulte sur Mac, iPad ou iPhone,
sans Internet ni serveur.

## Ce que fait le guide

- **Cartes de recettes** : une miniature (la plus grande photo de la recette), le
  titre nettoyé et la source en badge (Ricardo, Kraft, etc.).
- **Catégories et sous-catégories** : chaque dossier devient une catégorie et chaque
  sous-dossier une sous-catégorie.
- **Recherche** dans les titres **et** dans le texte des recettes. Elle ignore les
  accents (« boeuf » trouve « bœuf ») et tolère les fautes de frappe.
- **Recettes scannées** : le texte est lu automatiquement (OCR) et les pages
  scannées de côté sont redressées.
- **🥕 Mode Frigo** : tu indiques ce que tu as (poulet, brocoli, riz…) et les
  recettes qui en utilisent le plus apparaissent en premier.
- **🎲 « Qu'est-ce qu'on mange ? »** : une recette au hasard, dans la catégorie
  choisie ou parmi toutes.
- **⭐ Favoris et 📝 notes** pour chaque recette. Ils suivent la recette même si tu
  la renommes ou la déplaces.
- **Lecture plein écran** : les pages de la recette s'affichent directement dans le
  guide, ce qui marche aussi dans les visionneuses HTML sur iPad. Sur Mac, il y a en
  plus « Ouvrir le PDF » et « Voir en ligne ».

## Installation (Mac)

### Étape 1 — Installer Python (une seule fois)

Le guide utilise Python, fourni par Apple avec les **outils de ligne de
commande** (pas besoin de VS Code ni de Xcode au complet).

1. Ouvre le **Terminal** (Cmd + Espace, tape « Terminal », Entrée).
2. Copie cette ligne, colle-la dans le Terminal et appuie sur Entrée :
   ```bash
   xcode-select --install
   ```
3. Une fenêtre s'ouvre : clique **Installer**, accepte la licence et attends la
   fin (5 à 15 minutes selon ta connexion).
   - Si le Terminal répond « already installed », c'est que c'est déjà fait. 👍
4. Vérifie que tout est en place :
   ```bash
   python3 --version
   ```
   Tu dois voir quelque chose comme `Python 3.9.6`.

### Étape 2 — Télécharger le guide

Dans le Terminal, copie et colle cette ligne, puis appuie sur Entrée :

```bash
cd ~/Documents && curl -L https://github.com/Loic830/guide-recette/archive/refs/heads/main.zip -o guide.zip && unzip -q guide.zip && mv guide-recette-main "Guide recettes" && rm guide.zip && open "Guide recettes"
```

Elle télécharge le guide, le place dans **Documents → Guide recettes** et ouvre
le dossier dans le Finder. Téléchargé de cette façon, le fichier « Rafraîchir le
guide » n'est pas bloqué par macOS : aucun avertissement de sécurité.

> ⚠️ S'il existe déjà un dossier « Guide recettes » dans Documents, renomme-le
> d'abord, sinon la commande s'arrête.
>
> 💡 Pour que le guide soit aussi sur ton iPad ou ton iPhone, active
> **iCloud Drive → Dossiers Bureau et Documents** dans les Réglages Système
> (section de ton compte Apple).

<details>
<summary>Autre méthode : télécharger le ZIP depuis GitHub (sans Terminal)</summary>

1. Sur la page GitHub, bouton vert **Code → Download ZIP**, puis décompresse-le
   et place le dossier où tu veux (par exemple dans Documents).
2. **La toute première fois** que tu double-cliques sur « Rafraîchir le guide »,
   macOS bloque le fichier (« Apple n'a pas pu vérifier… »). Appuie sur
   **OK / Terminé** (pas « Placer dans la corbeille »), puis va dans
   **Réglages Système → Confidentialité et sécurité**, descends jusqu'à
   « Rafraîchir le guide » et clique **Ouvrir quand même**. Le script retire alors
   lui-même le blocage : les fois suivantes, un simple double-clic suffit.

</details>

### Étape 3 — Ajouter tes recettes et lancer le guide

1. Range tes recettes (PDF ou photos) dans des dossiers. Ceux qui sont fournis
   (Déjeuners, Desserts, Soupers) sont des exemples : renomme-les, supprime-les ou
   ajoutes-en d'autres.
2. Double-clique sur **« Rafraîchir le guide »**.
   - **La première fois**, il installe ses outils (1 à 3 minutes, connexion
     Internet requise).
3. `Guide.html` s'ouvre dans ton navigateur. 🎉

> Si le double-clic ne fait rien, ouvre le Terminal et tape `chmod +x ` (avec
> l'espace), glisse le fichier « Rafraîchir le guide » dans la fenêtre, puis appuie
> sur Entrée.

## Utilisation au quotidien

| Je veux… | Je fais… |
|---|---|
| Ajouter une recette | Je glisse le PDF (ou une photo) dans le bon dossier, puis je double-clique sur « Rafraîchir le guide ». |
| Créer une catégorie | Je crée un dossier. |
| Créer une sous-catégorie | Je crée un dossier dans une catégorie (ex. `Desserts/Biscuits`). |
| Changer la miniature | Je mets une image **du même nom** à côté du PDF (`Chili.pdf` et `Chili.jpg`). |
| Consulter sur iPad ou iPhone | Le dossier étant dans iCloud Drive, j'ouvre `Guide.html` avec une visionneuse HTML. |

Le rafraîchissement ne traite que les fichiers nouveaux ou modifiés : c'est
instantané quand rien n'a changé.

### Bon à savoir

- Les fichiers posés directement à la racine (hors d'un dossier) sont ignorés.
- Le titre vient du nom de fichier. `Poulet au beurre | RICARDO.pdf` donne le titre
  « Poulet au beurre » avec le badge « Ricardo ». Les formes `Titre - Source.pdf`
  sont aussi reconnues.
- Les favoris et les notes sont enregistrés **dans le navigateur de chaque
  appareil**. Ceux de l'iPad ne sont pas partagés avec le Mac.
- Le guide contient les images des pages, donc il fait quelques Mo (environ
  10 à 15 Mo pour 70 recettes).

## Windows ou Linux

Le guide fonctionne partout, mais le bouton « Rafraîchir » est fait pour Mac.
Ailleurs, il faut Python 3 puis :

```bash
pip install pymupdf pillow
python3 .guide/build_guide.py
```

Pour lire les recettes scannées, installe aussi
[Tesseract](https://github.com/tesseract-ocr/tesseract) avec le français
(`tesseract-ocr-fra`). Sur Mac, c'est le moteur de reconnaissance de texte
d'Apple qui est utilisé automatiquement.

## Contenu du dépôt

```
Rafraîchir le guide.command   ← le bouton à double-cliquer (Mac)
.guide/
  build_guide.py              ← lit les recettes et génère Guide.html
  template.html               ← l'interface du guide
  requirements.txt
Déjeuners/ Desserts/ Soupers/ ← dossiers d'exemple (à remplacer par les tiens)
```

Le fichier `.gitignore` exclut tes recettes, `Guide.html` et le cache : seul
l'outil est partagé sur GitHub.

## Personnaliser

- **Sources reconnues** : complète la liste `SOURCES` en haut de
  `.guide/build_guide.py`.
- **Couleurs et polices** : variables CSS au début de `.guide/template.html`.
- Après une modification, double-clique sur « Rafraîchir le guide ». Si tu as
  changé le traitement des PDF, supprime d'abord `.guide/cache.json` pour que tout
  soit retraité.
