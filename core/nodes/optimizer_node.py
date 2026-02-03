import json
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class OptimizerNode:
    """
    Workflow Optimizer Node.
    Analyzes current workflow state and suggests performance improvements or tiered upgrades.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        engine = context.get('engine')
        node = context.get('node')
        input_text = inputs.get('text') or inputs.get('query', '')
        context_str = context.get('context_str', '')
        
        if not engine or not node:
            return {"ok": False, "error": "Missing engine or node in context"}

        await engine.log(node.name, "⚙️ Analyzing workflow state and performance...")
        
        # Create a summary of the current workflow state
        wf_state = {
            "nodes": {
                nid: {
                    "name": n.name,
                    "status": n.status,
                    "error": n.error,
                    "output_len": len(n.output) if n.output else 0,
                    "tier": n.tier
                } for nid, n in engine.current_workflow.nodes.items() if n.id != node.id
            }
        }
        
        optimizer_prompt = f"""
You are the WORKFLOW OPTIMIZER. You have access to the current state of the orchestrator.
MISSION: {input_text}
CONTEXT: {context_str}

CURRENT WORKFLOW STATE:
{json.dumps(wf_state, indent=2)}

TASK:
1. Diagnose any failures or bottlenecks.
2. Suggest model upgrades for nodes that are struggling.
3. Provide a 'System Diagnostic Report' as your output.
4. If you detect a critical failure, suggest a 'Recovery Path'.

Use YOUR THINKING PROCESS to decide if any nodes should be upgraded to 'paid' tier or different models.
"""
        # Optimizer is an Agent-heavy node, we use the engine's provider logic
        provider = await engine._get_provider(node)
        if not provider:
             return {"ok": False, "error": "No provider for optimizer"}

        output = await provider.generate(
            system_prompt=node.persona,
            user_message=optimizer_prompt,
            model_override=node.model
        )
        
        # Process output (strip thinking etc. - engine handles this usually but we can do it here for isolation)
        output = engine._strip_thinking(output, node.name)
        
        await engine.log(node.name, "✅ Diagnostic report generated.")
        return {"ok": True, "output": output}
