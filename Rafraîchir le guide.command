#!/bin/bash
# Double-clique sur ce fichier pour mettre à jour Guide.html
# après avoir ajouté, retiré ou renommé des recettes.

cd "$(dirname "$0")" || exit 1
ENV_DIR="$HOME/Library/Application Support/GuideRecettes/venv"
PY="$ENV_DIR/bin/python3"

clear
echo "🍳  Mise à jour du guide de recettes"
echo "────────────────────────────────────"

if [ ! -x "$PY" ] || ! "$PY" -c "import pymupdf, PIL" 2>/dev/null; then
  echo "Première utilisation : installation des outils (1 à 3 minutes)…"
  if ! /usr/bin/python3 -c "import sys" 2>/dev/null; then
    echo ""
    echo "⚠️  macOS doit d'abord installer les « outils de ligne de commande »."
    echo "   Une fenêtre va s'ouvrir : clique sur « Installer », attends la fin,"
    echo "   puis double-clique de nouveau sur « Rafraîchir le guide »."
    xcode-select --install 2>/dev/null
    read -r -p "Appuie sur Entrée pour fermer…" _
    exit 1
  fi
  mkdir -p "$(dirname "$ENV_DIR")"
  /usr/bin/python3 -m venv "$ENV_DIR" || { echo "❌ Impossible de créer l'environnement Python."; read -r _; exit 1; }
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r ".guide/requirements.txt" || { echo "❌ Installation impossible (connexion Internet ?)."; read -r _; exit 1; }
  echo "✅ Outils installés."
  echo ""
fi

"$PY" ".guide/build_guide.py" "$(pwd)"
STATUS=$?
echo ""
if [ $STATUS -eq 0 ]; then
  open "Guide.html"
  echo "Tu peux fermer cette fenêtre."
else
  echo "❌ Une erreur est survenue (voir ci-dessus)."
  read -r -p "Appuie sur Entrée pour fermer…" _
fi
