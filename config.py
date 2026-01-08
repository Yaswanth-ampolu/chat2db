"""
Configuration Management

Handles API keys, database connections, and other configuration.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration manager."""

    def __init__(self):
        self.config_dir = Path.home() / ".chat2sql"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
        self._config: Dict[str, Any] = self._load_config()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(exist_ok=True, parents=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Check environment variables first
        env_value = os.getenv(key.upper())
        if env_value:
            return env_value

        # Then check config file
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value
        self._save_config()

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.

        Args:
            provider: Provider name ('google', 'openai', 'anthropic')

        Returns:
            API key or None
        """
        provider = provider.lower()

        # Environment variable mapping
        env_vars = {
            "google": "GOOGLE_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        env_var = env_vars.get(provider)
        if env_var:
            api_key = os.getenv(env_var)
            if api_key:
                return api_key

        # Check config file
        return self._config.get(f"{provider}_api_key")

    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Save API key for a provider.

        Args:
            provider: Provider name
            api_key: API key to save
        """
        provider = provider.lower()
        self._config[f"{provider}_api_key"] = api_key
        self._save_config()

    def get_db_connection(self) -> Optional[Dict[str, str]]:
        """
        Get database connection parameters.

        Returns:
            Dictionary of connection parameters or None
        """
        return self._config.get("db_connection")

    def set_db_connection(self, params: Dict[str, str]) -> None:
        """
        Save database connection parameters.

        Args:
            params: Connection parameters
        """
        self._config["db_connection"] = params
        self._save_config()

    def get_last_provider(self) -> Optional[str]:
        """Get last used provider."""
        return self._config.get("last_provider")

    def set_last_provider(self, provider: str) -> None:
        """Save last used provider."""
        self._config["last_provider"] = provider
        self._save_config()

    def get_last_model(self, provider: str) -> Optional[str]:
        """Get last used model for a provider."""
        return self._config.get(f"last_model_{provider}")

    def set_last_model(self, provider: str, model: str) -> None:
        """Save last used model for a provider."""
        self._config[f"last_model_{provider}"] = model
        self._save_config()


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get global config instance.

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
