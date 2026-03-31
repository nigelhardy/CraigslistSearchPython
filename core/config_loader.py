from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Manages loading and validation of YAML configuration files."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent
        self._cache: Dict[str, Any] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load and cache YAML configuration file."""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Use cache if available
        if filename in self._cache:
            logger.debug(f"Using cached config for {filename}")
            return self._cache[filename]
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            
            # Cache the loaded data
            self._cache[filename] = config_data
            logger.info(f"Loaded configuration from {config_path}")
            
            return config_data
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {config_path}: {e}")
            raise ValueError(f"Invalid YAML in {filename}: {e}")
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            raise
    
    def reload_config(self, filename: str) -> Dict[str, Any]:
        """Force reload of configuration file."""
        if filename in self._cache:
            del self._cache[filename]
        return self.load_yaml(filename)
    
    def validate_search_config(self, config_data: Dict[str, Any]) -> bool:
        """Validate search configuration structure."""
        required_keys = ['searches', 'scoring', 'output']
        
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"Missing required configuration section: {key}")
        
        # Validate searches
        for search_id, search_config in config_data['searches'].items():
            required_search_keys = ['name', 'query', 'categories', 'cities']
            for req_key in required_search_keys:
                if req_key not in search_config:
                    raise ValueError(f"Search '{search_id}' missing required key: {req_key}")
        
        return True
    
    def get_config_path(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir