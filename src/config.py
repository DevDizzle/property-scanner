"""Configuration loader for Property Scanner."""
import os
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"

def load_config() -> dict:
    """Load config from YAML file, with env var overrides."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found at {CONFIG_PATH}. "
            "Copy config.example.yaml to config.yaml and add your keys."
        )
    
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    
    # Environment variable overrides
    env_overrides = {
        "RENTCAST_API_KEY": ("apis", "rentcast", "api_key"),
        "SCRAPINGBEE_API_KEY": ("apis", "scrapingbee", "api_key"),
        "SENDGRID_API_KEY": ("delivery", "sendgrid_api_key"),
        "GCP_PROJECT_ID": ("gcp", "project_id"),
    }
    
    for env_var, path in env_overrides.items():
        val = os.environ.get(env_var)
        if val:
            obj = config
            for key in path[:-1]:
                obj = obj[key]
            obj[path[-1]] = val
    
    return config

# Singleton
_config = None

def get_config() -> dict:
    global _config
    if _config is None:
        _config = load_config()
    return _config
