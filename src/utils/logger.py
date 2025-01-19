import logging
import logging.config
from pathlib import Path
import yaml
from typing import Optional

def setup_logging() -> None:
    """Configure le système de logging à partir du fichier logging.yaml"""
    logging_config_path = Path("config/logging.yaml")
    
    # Charger la configuration du logging
    with open(logging_config_path) as f:
        config = yaml.safe_load(f)
        
    # Configurer le logging
    logging.config.dictConfig(config)
    
    # Créer un logger pour cette configuration
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")

def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module spécifié
    
    Args:
        name: Nom du module (généralement __name__)
        
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)