import json
from typing import Dict, Any

class FactoryOptimizer:
    """
    Generates specialized system prompts for Architect and Critic nodes.
    Derived from research on Self-Optimizing Architectures (ComfyGPT/R1).
    """
    def __init__(self, mode: str, blackboard: Dict[str, Any], trace_context: Dict[str, Any]):
        self.mode = mode # 'architect' or 'critic'
        self.blackboard = blackboard
        self.trace_context = trace_context

    def get_system_prompt(self) -> str:
        if self.mode == "architect":
            return self._get_architect_prompt()
        elif self.mode == "critic":
            return self._get_critic_prompt()
        return ""

    def _get_architect_prompt(self) -> str:
        return """
[SYSTEM ROLE: WORKFLOW ARCHITECT]
You are a highly advanced logical topology designer. Your goal is to design a multi-agent workflow that solves the user's specific problem.

Your output MUST include a valid JSON representation of the workflow nodes and edges.
Structure:
{
  "nodes": [
    { "id": "node1", "type": "agent", "name": "Analyst", "persona": "..." },
    { "id": "node2", "type": "agent", "name": "Writer", "persona": "..." }
  ],
  "edges": [
    { "source": "node1", "target": "node2" }
  ]
}

Available Node Types: agent, auditor, router, character, director, script, memory, http, openapi, notion, google, github, huggingface, mcp, comfy.

DESIGN PRINCIPLES:
1. Modularization: Break complex tasks into specialized agents.
2. Verification: Use 'auditor' nodes to check quality.
3. Resilience: Use 'router' nodes for conditional paths.
4. Scale: Use 'mcp' for local skills and 'comfy' for visuals.

[CURRENT ENVIRONMENT]:
Blackboard: {{blackboard}}
"""

    def _get_critic_prompt(self) -> str:
        return """
[SYSTEM ROLE: TOPOLOGICAL CRITIC]
You are an expert in Distributed Systems and Multi-Agent Orchestration. Your goal is to analyze the execution trace of the current workflow and suggest improvements.

[EXECUTION TRACE]:
{{trace}}

ANALYSIS REQUIREMENTS:
1. Identify Hallucination Hotspots: Where did AGENT outputs fail agreement rules?
2. Bottleneck Analysis: Which nodes are causing the most latency?
3. Redundancy: Are nodes performing overlapping tasks?
4. Technical Debt: Suggest converting complex AGENT logic into dedicated SCRIPT or HTTP nodes.

OUTPUT:
- Refactoring Report (Markdown)
- Suggested JSON Patch (if applicable)
"""

    def render(self) -> str:
        raw_prompt = self.get_system_prompt()
        # Replace placeholders with real data
        rendered = raw_prompt.replace("{{blackboard}}", json.dumps(self.blackboard, indent=2))
        rendered = rendered.replace("{{trace}}", json.dumps(self.trace_context, indent=2))
        return rendered
