# tools/run_pytest.py
# ============================================================
# Lance pytest et enregistre automatiquement un log horodaté.
#
# MODIFICATION EXPLICITE :
# - création automatique du dossier logs/pytest
# - nom de fichier explicite avec date et heure
# - enregistrement de toute la sortie pytest
# - affichage du chemin du log à la fin
# ============================================================

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    """
    Lance pytest avec les arguments éventuellement passés en ligne
    de commande, et journalise la sortie dans un fichier horodaté.
    """

    # MODIFICATION EXPLICITE :
    # on crée un dossier dédié aux logs pytest
    log_dir = Path("logs/pytest")
    log_dir.mkdir(parents=True, exist_ok=True)

    # MODIFICATION EXPLICITE :
    # nom explicite, horodaté, lisible et triable
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"pytest_run_{timestamp}.log"

    # Si l'utilisateur passe des arguments, on les propage à pytest.
    # Exemple :
    # python tools/run_pytest.py -x -v
    pytest_args = sys.argv[1:]

    # MODIFICATION EXPLICITE :
    # on force l'appel via le même interpréteur Python
    command = [sys.executable, "-m", "pytest", *pytest_args]

    with log_file.open("w", encoding="utf-8") as f:
        # En-tête utile pour relire le log plus tard
        f.write("=== PYTEST RUN LOG ===\n")
        f.write(f"Timestamp : {timestamp}\n")
        f.write(f"Command   : {' '.join(command)}\n")
        f.write("=" * 60 + "\n\n")

        # Lancement de pytest
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )

        # Écriture du log complet
        f.write(process.stdout)
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"Return code: {process.returncode}\n")

    # On réaffiche aussi la sortie dans le terminal pour le confort
    print(process.stdout)
    print(f"\nLog enregistré dans : {log_file}")

    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())