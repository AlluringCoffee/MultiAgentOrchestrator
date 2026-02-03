import aiohttp
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ComfyNode")

class ComfyNode:
    """
    Connects to a running ComfyUI instance to execute workflows.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.base_url = config.get("base_url", "http://127.0.0.1:8188")
        self.client_id = str(uuid.uuid4())
        
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Executes a ComfyUI workflow.
        Two modes:
        1. 'prompt': Text-to-Image (uses a default workflow template).
        2. 'workflow': Full JSON workflow injection.
        """
        mode = self.config.get("mode", "prompt")
        
        try:
            if mode == "prompt":
                prompt_text = inputs.get("prompt") or self.config.get("prompt")
                if not prompt_text:
                    return {"ok": False, "error": "ComfyUI: No prompt provided"}
                
                workflow = self._build_default_workflow(prompt_text)
                
            elif mode == "workflow":
                workflow_json = inputs.get("workflow_json") or self.config.get("workflow_json")
                if isinstance(workflow_json, str):
                    workflow = json.loads(workflow_json)
                else:
                    workflow = workflow_json
                    
                if not workflow:
                    return {"ok": False, "error": "ComfyUI: No workflow JSON provided"}
            else:
                 return {"ok": False, "error": f"Unknown mode: {mode}"}

            # execute
            images = await self._queue_prompt(workflow)
            return {"ok": True, "data": {"images": images}}
            
        except Exception as e:
            logger.error(f"ComfyUI Error: {e}")
            return {"ok": False, "error": str(e)}

    def _build_default_workflow(self, prompt_text: str) -> Dict[str, Any]:
        """
        Constructs a minimal text-to-image workflow.
        Note: ComfyUI API expects the full node graph format, not the UI export format.
        For simplicity, we assume a standard ID structure (3=KSampler, 6=CLIPTextEncode, etc.)
        This is brittle without a known template, but sufficient for a prototype.
        """
        # Minimalist Prompt-only structure (requires standard ComfyUI default graph to work reliably)
        # Ideally, we should load a template from disk.
        # For now, let's inject prompt into Node 6 (Positive Prompt) if we assume default.
        # Use a simplified template dict here.
        
        template = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": 5,
                    "steps": 20
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.ckpt"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": 512,
                    "width": 512
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt_text 
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "text, watermark" 
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                }
            }
        }
        return template

    async def _queue_prompt(self, workflow: Dict) -> List[str]:
        """
        Submits prompt to ComfyUI and waits for execution.
        """
        p = {"prompt": workflow, "client_id": self.client_id}
        
        async with aiohttp.ClientSession() as session:
            # 1. Queue Prompt
            async with session.post(f"{self.base_url}/prompt", json=p) as resp:
                if not resp.ok:
                    raise Exception(f"Failed to queue prompt: {await resp.text()}")
                resp_json = await resp.json()
                prompt_id = resp_json['prompt_id']
                
            # 2. Open WebSocket to listen for completion
            ws_url = self.base_url.replace("http", "ws") + f"/ws?clientId={self.client_id}"
            
            async with session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        message = json.loads(msg.data)
                        
                        if message['type'] == 'executing':
                            data = message['data']
                            if data['node'] is None and data['prompt_id'] == prompt_id:
                                # Execution complete
                                break
            
            # 3. Retrieve History to get Output Images
            async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
                history = await resp.json()
                output_images = []
                
                outputs = history[prompt_id]['outputs']
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        for image in node_output['images']:
                            # specific to default output node
                            img_url = f"{self.base_url}/view?filename={image['filename']}&subfolder={image['subfolder']}&type={image['type']}"
                            output_images.append(img_url)
                            
        return output_images
