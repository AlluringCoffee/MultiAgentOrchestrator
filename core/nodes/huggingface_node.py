import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class HuggingfaceNode:
    """
    Handles HuggingFace model/dataset operations.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        engine = context.get('engine')
        node = context.get('node')
        if not engine: return {"ok": False, "error": "No engine"}

        await engine.log(node.name, "🤗 Executing HuggingFace Action...")
        try:
            from core.tools.hf_tool import HFTool
            
            repo_id = self.config.get("repo_id")
            if not repo_id:
                return {"ok": False, "error": "No repo_id provided"}

            res = HFTool.download_model(repo_id, local_dir=f"./models/{repo_id.replace('/', '_')}")
            
            if res.get("success"):
                return {"ok": True, "output": f"Downloaded {repo_id} to {res.get('path')}"}
            else:
                return {"ok": False, "error": f"Download Failed: {res.get('error')}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
