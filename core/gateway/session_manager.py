import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionBridge:
    """
    Manages mappings between external platform users and workflow sessions.
    Enables multi-turn persistence across Telegram, Discord, etc.
    """
    def __init__(self, storage_path: str = "sessions.json"):
        self.storage_path = storage_path
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.sessions = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")

    def _save(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def get_session(self, platform: str, external_id: str) -> Optional[Dict[str, Any]]:
        key = f"{platform}:{external_id}"
        return self.sessions.get(key)

    def create_session(self, platform: str, external_id: str, workflow_id: str, initial_data: Dict[str, Any] = None):
        key = f"{platform}:{external_id}"
        self.sessions[key] = {
            "platform": platform,
            "external_id": external_id,
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "metadata": initial_data or {},
            "history": []
        }
        self._save()
        return self.sessions[key]

    def update_session(self, platform: str, external_id: str, message: str, is_user: bool = True):
        key = f"{platform}:{external_id}"
        if key in self.sessions:
            self.sessions[key]["last_active"] = datetime.now().isoformat()
            self.sessions[key]["history"].append({
                "role": "user" if is_user else "assistant",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            # Keep history manageable
            if len(self.sessions[key]["history"]) > 20:
                self.sessions[key]["history"] = self.sessions[key]["history"][-20:]
            self._save()

    def clear_session(self, platform: str, external_id: str):
        key = f"{platform}:{external_id}"
        if key in self.sessions:
            del self.sessions[key]
            self._save()
