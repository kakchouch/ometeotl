'''
# tools/run_pytest.py
# ============================================================
# Launches pytest and creates a timestamped log in a dedicated folder.
# ============================================================
'''
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    """
    Run pytest with any command-line arguments passed, and log the
    output to a timestamped file.
    """

    # EXPLICIT MODIFICATION:
    # Create a dedicated folder for pytest logs
    log_dir = Path("logs/pytest")
    log_dir.mkdir(parents=True, exist_ok=True)

    # EXPLICIT MODIFICATION:
    # Explicit, timestamped, readable and sortable name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"pytest_run_{timestamp}.log"

    # If the user passes arguments, pass them to pytest.
    # Example:
    # python tools/run_pytest.py -x -v
    pytest_args = sys.argv[1:]

    # EXPLICIT MODIFICATION:
    # Force the call via the same Python interpreter
    command = [sys.executable, "-m", "pytest", "-v", *pytest_args]

    with log_file.open("w", encoding="utf-8") as f:
        # Useful header for reviewing the log later
        f.write("=== PYTEST RUN LOG ===\n")
        f.write(f"Timestamp : {timestamp}\n")
        f.write(f"Command   : {' '.join(command)}\n")
        f.write("=" * 60 + "\n\n")

        # Launching pytest
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            check=False,
        )

        # Write complete log
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
