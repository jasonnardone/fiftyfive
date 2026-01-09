"""Configuration loader with YAML parsing and environment variable substitution"""

import os
import re
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

from src.models.config import Config


class ConfigLoader:
    """Loads and validates configuration from YAML files"""

    def __init__(self):
        """Initialize config loader"""
        # Load environment variables from .env file
        load_dotenv(override=True)

    def load(self, config_path: str) -> Config:
        """Load configuration from YAML file

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Validated Config object

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If configuration is invalid
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Read YAML file
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # Substitute environment variables
        config_dict = self._substitute_env_vars(raw_config)

        # Validate with Pydantic
        try:
            config = Config(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}") from e

        return config

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in config

        Supports ${VAR_NAME} and ${VAR_NAME:default} syntax

        Args:
            obj: Configuration object (dict, list, str, etc.)

        Returns:
            Object with environment variables substituted
        """
        if isinstance(obj, dict):
            return {key: self._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_string(obj)
        else:
            return obj

    def _substitute_string(self, value: str) -> str:
        """Substitute environment variables in string

        Args:
            value: String potentially containing ${VAR} references

        Returns:
            String with variables substituted
        """
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)

            # Get from environment
            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                raise ValueError(
                    f"Environment variable ${{{var_name}}} not found and no default provided"
                )

        return re.sub(pattern, replacer, value)


def load_config(config_path: str) -> Config:
    """Convenience function to load configuration

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Validated Config object
    """
    loader = ConfigLoader()
    return loader.load(config_path)
