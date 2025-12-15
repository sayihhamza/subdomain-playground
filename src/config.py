"""
Configuration management for subdomain takeover detection
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager"""

    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_file: Optional custom config file path
        """
        self.config_file = Path(config_file) if config_file else self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()

        # Load additional configs
        config_dir = self.config_file.parent
        self.config_dir = config_dir

        # Use enhanced providers if available
        enhanced_providers = config_dir / 'providers_enhanced.yaml'
        if enhanced_providers.exists():
            self.providers = self._load_yaml(enhanced_providers)
        else:
            self.providers = self._load_yaml(config_dir / 'providers.yaml')

        self.tool_config = self._load_yaml(config_dir / 'tool_config.yaml')

        # Tool paths
        self.tool_paths = {
            'subfinder': self.get_tool_path('subfinder'),
            'dnsx': self.get_tool_path('dnsx'),
            'httpx': self.get_tool_path('httpx'),
            'subzy': self.get_tool_path('subzy'),
            'nuclei': self.get_tool_path('nuclei')
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration file"""
        if not self.config_file.exists():
            # Return default config
            return self._get_default_config()

        return self._load_yaml(self.config_file)

    def _load_yaml(self, filepath: Path) -> Dict[str, Any]:
        """Load YAML file"""
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load {filepath}: {e}")
            return {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'general': {
                'threads': 50,
                'timeout': 10,
                'rate_limit': 100
            },
            'paths': {
                'bin_dir': './bin',
                'output_dir': './output',
                'log_dir': './output/logs'
            },
            'tools': {
                'subfinder': {'enabled': True, 'timeout': 300},
                'dnsx': {'enabled': True, 'resolvers': []},
                'httpx': {'enabled': True, 'follow_redirects': True, 'tech_detect': True},
                'subzy': {'enabled': True, 'timeout': 10},
                'nuclei': {'enabled': True, 'templates': 'takeovers'}
            }
        }

    def get_tool_path(self, tool_name: str) -> Path:
        """Get binary path for a tool - checks environment variables first"""
        # Check environment variable first (e.g., DNSX_PATH, HTTPX_PATH)
        env_var = f"{tool_name.upper()}_PATH"
        env_path = os.getenv(env_var)

        if env_path:
            return Path(env_path)

        # Fall back to config directory
        bin_dir = Path(self.config['paths']['bin_dir'])
        return bin_dir / tool_name

    def get_vulnerable_providers(self) -> Dict[str, Any]:
        """Get vulnerable provider patterns"""
        return self.providers.get('providers', {})

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation)

        Args:
            key: Configuration key (e.g., 'general.threads')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default
