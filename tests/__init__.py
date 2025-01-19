"""
Tests pour le PixelBot
"""

import os
import sys

# Ajouter le répertoire src au PYTHONPATH pour les tests
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, src_path)