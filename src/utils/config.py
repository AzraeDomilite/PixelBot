import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

class Config:
    """Classe de configuration du bot"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    def __getattr__(self, name: str) -> Any:
        """Permet d'accéder aux valeurs de configuration via des attributs"""
        if name in self._config:
            value = self._config[name]
            if isinstance(value, dict):
                return Config(value)
            return value
        raise AttributeError(f"Config has no attribute '{name}'")

    @classmethod
    def load(cls) -> 'Config':
        """Charge la configuration depuis les fichiers YAML et les variables d'environnement"""
        # Charger les variables d'environnement
        load_dotenv()
        
        # Charger la configuration principale
        config_path = Path("config/config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Remplacer les variables d'environnement
        config = cls._replace_env_vars(config)
        
        return cls(config)
    
    @staticmethod
    def _replace_env_vars(value: Any) -> Any:
        """Remplace les variables d'environnement dans la configuration"""
        if isinstance(value, dict):
            return {k: Config._replace_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [Config._replace_env_vars(v) for v in value]
        elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value

# Fonction utilitaire pour charger la configuration
def load_config() -> Config:
    """Charge et retourne la configuration du bot"""
    return Config.load()