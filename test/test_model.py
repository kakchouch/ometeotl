# test_models.py - Test basique de cohérence
import sys
sys.path.insert(0, '.')  # Pour imports relatifs en dev

from base import ModelObject  # Vérifie base
from objects import GenericObject  # Vérifie objets
from actors import Actor  # etc.

# Test instantiation
actor = Actor(id="test_actor")
assert actor.objecttype == "actor"  # Vérifie post_init
print("Tests OK")  # Succès si pas d'erreur d'import