import sys
import os
import pytest

# Ajouter le dossier src/app au sys.path pour les imports relatifs
sys.path.insert(0, os.path.abspath(path=os.path.join(os.path.dirname(__file__), '..', 'src/app')))

# Put the interpreter at the right place to resolve imports
os.chdir(os.path.dirname(__file__))

from main import frame_buffer, exit_event

@pytest.fixture(autouse=True)
def clear_frame_buffer():
    """
    Vide le frame_buffer avant chaque test pour garantir un état propre.
    """
    frame_buffer.clear()
    yield

@pytest.fixture(autouse=True)
def exit_event_unset():
    """
    Vide le frame_buffer avant chaque test pour garantir un état propre.
    """
    exit_event.clear()
    yield

