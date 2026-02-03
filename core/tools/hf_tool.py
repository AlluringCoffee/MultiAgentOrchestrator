import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class HFTool:
    """
    Wrapper for Hugging Face Hub operations.
    Requires 'huggingface_hub' package installed.
    """
    
    @staticmethod
    def search_models(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            models = api.list_models(search=query, limit=limit, sort="downloads", direction=-1)
            results = []
            for m in models:
                results.append({
                    "id": m.modelId,
                    "likes": m.likes,
                    "downloads": m.downloads,
                    "pipeline": m.pipeline_tag
                })
            return results
        except ImportError:
            return [{"error": "huggingface_hub library not installed"}]
        except Exception as e:
            logger.error(f"HF Search Error: {e}")
            return [{"error": str(e)}]
            
    @staticmethod
    def download_model(repo_id: str, local_dir: str = None) -> Dict[str, Any]:
        try:
            from huggingface_hub import snapshot_download
            ignore_patterns = ["*.msgpack", "*.h5", "*.ot"] # Skip some large non-safetensor formats if desired
            path = snapshot_download(repo_id=repo_id, local_dir=local_dir, ignore_patterns=ignore_patterns)
            return {"success": True, "path": path}
        except Exception as e:
             return {"success": False, "error": str(e)}
