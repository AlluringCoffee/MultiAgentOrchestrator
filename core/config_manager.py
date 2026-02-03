import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ProviderConfig(BaseModel):
    id: str
    name: str
    type: str  # ollama, opencode, groq, google_ai, cli_bridge
    config: Dict[str, Any]
    models: List[str] = []
    enabled: bool = True
    last_health_check: Optional[str] = None
    status: str = "unknown"  # online, offline, unknown

class ProviderConfigManager:
    def __init__(self, config_path: str = "providers.json"):
        self.config_path = os.path.abspath(config_path)
        self.providers: Dict[str, ProviderConfig] = {}
        self._load_config()

    def _load_config(self):
        """Load providers from JSON file or initialize with defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for p_id, p_data in data.items():
                        self.providers[p_id] = ProviderConfig(**p_data)
                logger.info(f"Loaded {len(self.providers)} providers from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load providers config: {e}")
                self._initialize_defaults()
        else:
            self._initialize_defaults()

    def _initialize_defaults(self):
        """Set up initial default providers."""
        logger.info("Initializing default providers...")
        defaults = {
            "ollama": ProviderConfig(
                id="ollama",
                name="Ollama (Local)",
                type="ollama",
                config={"base_url": "http://localhost:11434"},
                models=["llama3", "mistral", "phi3"]
            ),
            "opencode_wsl": ProviderConfig(
                id="opencode_wsl",
                name="OpenCode (WSL)",
                type="opencode",
                config={"cli_command": "wsl -d Ubuntu -e /home/alluring/.opencode/bin/opencode"},
                models=["kimi-k2-thinking", "qwen2.5-coder-7b", "deepseek-v3"]
            ),
            "groq_free": ProviderConfig(
                id="groq_free",
                name="Groq (Free Tier)",
                type="groq",
                config={"api_key": ""},
                models=["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
            )
        }
        self.providers = defaults
        self.save_config()

    def save_config(self):
        """Save current providers to JSON file."""
        try:
            data = {p_id: p.model_dump() for p_id, p in self.providers.items()}
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.debug(f"Saved providers config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save providers config: {e}")

    def get_all(self) -> List[ProviderConfig]:
        return list(self.providers.values())

    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        return self.providers.get(provider_id)

    def add_provider(self, config: ProviderConfig):
        self.providers[config.id] = config
        self.save_config()

    def update_provider(self, provider_id: str, updates: Dict[str, Any]):
        if provider_id in self.providers:
            existing = self.providers[provider_id].model_dump()
            existing.update(updates)
            self.providers[provider_id] = ProviderConfig(**existing)
            self.save_config()
            return True
        return False

    def delete_provider(self, provider_id: str):
        if provider_id in self.providers:
            del self.providers[provider_id]
            self.save_config()
            return True
        return False

    def update_status(self, provider_id: str, status: str, available: bool):
        if provider_id in self.providers:
            self.providers[provider_id].status = status
            self.providers[provider_id].last_health_check = datetime.now().isoformat()
            # Note: available is derived at runtime usually, but we store status
            return True
        return False
