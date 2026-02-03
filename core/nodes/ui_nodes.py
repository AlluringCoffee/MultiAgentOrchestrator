import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class A2UINode:
    """
    Agent-to-UI Node.
    Converts structured input/LLM output into a UI schema for the frontend.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.component_type = config.get("component_type", "card") # card, form, buttons, chart

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        text = inputs.get("text", "")
        data = inputs.get("data", {})
        
        # If the input is already a JSON string that looks like a UI schema, use it.
        # Otherwise, wrap the input into a standard component structure.
        
        ui_schema = {
            "node_id": self.node_id,
            "type": self.component_type,
            "title": self.config.get("title", "Agent Action"),
            "content": text,
            "timestamp": context.get("timestamp") if context else None,
            "payload": data
        }
        
        # Specific component logic
        if self.component_type == "form":
            ui_schema["fields"] = self.config.get("fields", [])
        elif self.component_type == "buttons":
            ui_schema["actions"] = self.config.get("actions", [])
        elif self.component_type == "chart":
            ui_schema["chart_data"] = data.get("chart_data", [])
            ui_schema["chart_type"] = self.config.get("chart_type", "bar")

        return {
            "ok": True,
            "output": f"UI Component ({self.component_type}) generated",
            "data": ui_schema,
            "ui_event": "a2ui_update" # Sentinel for WorkflowEngine to broadcast
        }
