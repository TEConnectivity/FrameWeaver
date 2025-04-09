import sys
import os
import pytest

# Ajouter le dossier src/app au sys.path pour les imports relatifs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src/app')))

from main import frame_buffer

@pytest.fixture(autouse=True)
def clear_frame_buffer():
    """
    Vide le frame_buffer avant chaque test pour garantir un état propre.
    """
    frame_buffer.clear()
    yield
