import json
import logging
import re
from typing import Dict, Any, Optional
from core.workflow import NodeType

logger = logging.getLogger(__name__)

class WorkflowGenerator:
    """
    Generates workflow structures from natural language prompts using an LLM.
    """

    def __init__(self):
        # We will retrieve the provider dynamically to avoid circular imports or init issues
        pass

    async def generate_workflow(self, prompt: str, parent_node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a partial or full workflow based on the prompt.
        
        Args:
            prompt: User's intent (e.g., "Create a debate team")
            parent_node_id: ID of the node to attach to (if any)
            
        Returns:
            Dict containing "nodes" and "edges" keys.
        """
        try:
            from providers import ProviderRegistry, _register_providers
            
            # Ensure providers are loaded
            if not ProviderRegistry._providers:
                _register_providers()
                
            # Prefer a smart model for generation
            # Try finding Google (Gemini) first, then Anthropic, then OpenAI, then Ollama
            provider_type = "ollama"
            model_name = "mistral" # Default fallback
            
            # Simple heuristic to find a "smart" provider
            # In a real app, this might be configured explicitly
            from core.config_manager import ProviderConfigManager
            config_manager = ProviderConfigManager()
            providers = config_manager.get_all()
            
            smart_provider = None
            for p in providers:
                if p.enabled:
                    if p.type == "google" or p.type == "anthropic" or p.type == "openai":
                        smart_provider = p
                        break
                    # Fallback to a local model if it's all we have
                    if p.type == "ollama":
                        smart_provider = p

            if smart_provider:
                try:
                    provider = ProviderRegistry.create(smart_provider.type, smart_provider.model_dump())
                    await provider.initialize()
                except Exception as e:
                    logger.error(f"Failed to init smart provider {smart_provider.id}: {e}")
                    # Fallback to mock/default
                    return self._get_fallback_response(prompt)
            else:
                 # No providers?
                 return self._get_fallback_response(prompt)

            # Construct System Prompt
            system_prompt = f"""
You are an AI Architect for the "Multi-Agent Orchestrator" system.
Your goal is to convert user requests into a valid, high-quality JSON workflow structure.

### Node Types Available (NodeType):
- "input": User entry point. Persona is usually empty.
- "output": Final destination. Saves results. persona=""
- "agent": General LLM task worker. Requires strong "persona".
- "auditor": Validates output against "agreement_rules".
- "router": Routes traffic based on content logic.
- "character": Storyteller with consistency and "backstory".
- "director": Approver. Requires "persona", "requires_approval": true.
- "optimizer": Self-healing component. Manages models/state.
- "script": Python worker. POWERFUL. Has access to `cli.execute("cmd")`, `git.clone(...)`, `hf.download(...)` and `files` helpers. Use this for ALL coding tasks.
- "memory": Vector storage. "provider_config": {{"action": "store"|"retrieve"}}.
- "github": Git operations. "provider_config": {{"action": "status"|"clone"|"commit"|"log"|"push", "repo_url": "...", "message": "..."}}.
- "huggingface": HF Hub access. "provider_config": {{"action": "search"|"download", "query": "...", "repo_id": "..."}}.

### Output JSON Schema:
{{
  "nodes": {{
    "node_id": {{ 
      "name": "Display Name", 
      "type": "NodeType", 
      "persona": "Detailed system prompt",
      "x": 0, "y": 0,
      "provider": "google_ai"|"ollama"|"openai",
      "model": "model-name",
      "provider_config": {{ ... }},
      "script_code": "..." (for script nodes)
    }}
  }},
  "edges": [
    {{ "source": "node_id_1", "target": "node_id_2", "label": "logic label", "feedback": false, "condition": "approve"|"reject"|"" }}
  ]
}}

### Placement & Spacing Rules:
1. **Hierarchical Flow**: Layout nodes from Left to Right.
2. **Spacing**: Use X steps of 350 and Y steps of 200 to prevent overlap.
3. **Alignment**: Start at (50, 50). All input/entry nodes should be at X=50.
4. **God Mode Integration**: If the prompt involves coding or data, use `script`, `github`, or `huggingface` nodes.
5. **Human-in-the-loop**: Use `director` nodes for critical decision points.

### Constraints:
1. RETURN ONLY VALID JSON. 
2. Descriptive Node IDs only (e.g. "repo_cloner", "security_auditor").
3. Always connect nodes logically based on the user's workflow intent.
4. If 'parent_node_id' ({parent_node_id}) is provided, link it to the first node of your generated group.
"""

            user_message = f"User Request: {prompt}"
            if parent_node_id:
                user_message += f"\nContext: Attach resulting workflow to existing node '{parent_node_id}'."

            logger.info(f"Generating workflow with provider {smart_provider.type}...")
            response = await provider.generate(
                system_prompt=system_prompt,
                user_message=user_message
            )
            
            logger.debug(f"Raw LLM Response: {response}")
            
            # Cleanup and Parse
            return self._parse_json(response)

        except Exception as e:
            logger.error(f"Top-level Generation failed: {e}")
            return self._get_fallback_response(prompt)

    async def suggest_edges(self, nodes: List[Dict[str, Any]], user_intent: str = "") -> List[Dict[str, Any]]:
        """
        Analyzes a set of nodes and suggests logical connections (edges).
        """
        try:
            from providers import ProviderRegistry, _register_providers
            _register_providers()

            # Find a smart provider
            from core.config_manager import ProviderConfigManager
            cm = ProviderConfigManager()
            providers = cm.get_all()
            smart_provider = next((p for p in providers if p.enabled and p.type in ["google", "anthropic", "openai", "ollama"]), None)

            if not smart_provider:
                return []

            provider = ProviderRegistry.create(smart_provider.type, smart_provider.model_dump())
            await provider.initialize()

            node_summary = "\n".join([f"- ID: {n['id']}, Name: {n['name']}, Type: {n['type']}, Persona: {n.get('persona', '')[:100]}..." for n in nodes])

            prompt = f"""
You are the WORKFLOW ARCHITECT.
I have the following nodes in my orchestrator:
{node_summary}

USER INTENT: {user_intent}

TASK:
Propose the most logical connections (edges) between these nodes. 
Return ONLY a JSON array of edge objects.

JSON Format:
[
  {{ "source": "node_id_1", "target": "node_id_2", "label": "logic label", "feedback": false }}
]

Constraints:
1. Only use the provided Node IDs.
2. Return ONLY the JSON array.
"""
            response = await provider.generate(
                system_prompt="You are a JSON-only architect assistant.",
                user_message=prompt
            )

            # Cleanup and Parse
            import json
            match = re.search(r'(\[.*\])', response, re.DOTALL)
            if match:
                 return json.loads(match.group(1))
            return []

        except Exception as e:
            logger.error(f"Edge suggestion failed: {e}")
            return []

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Extracts and parses JSON from LLM response."""
        try:
            # Try finding JSON block
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                # Maybe the whole text is JSON?
                return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}. Text: {text}")
            return self._get_fallback_response("JSON Parse Error")

    def _get_fallback_response(self, prompt: str) -> Dict[str, Any]:
        """Returns a basic node if generation fails."""
        return {
            "nodes": {
                "gen_fallback_1": {
                    "name": "Generated Agent",
                    "type": "agent",
                    "persona": f"I am a fallback agent created because the Generator failed to connect. Prompt: {prompt}",
                    "x": 0,
                    "y": 0
                },
                "gen_fallback_2": {
                     "name": "Helper Agent",
                     "type": "agent",
                     "persona": "I am here to assist.",
                     "x": 300,
                     "y": 0
                }
            },
            "edges": [
                { "source": "gen_fallback_1", "target": "gen_fallback_2", "label": "assists" }
            ]
        }
