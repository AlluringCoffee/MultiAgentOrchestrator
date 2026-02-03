import uuid
from typing import List, Dict, Any
from .workflow import NodeType, NodeStatus

class TemplateLibrary:
    """
    Registry of high-value workflow templates.
    """
    
    @staticmethod
    def get_templates() -> List[Dict[str, Any]]:
        return [
            TemplateLibrary.social_media_manager(),
            TemplateLibrary.deep_research_analyst(),
            TemplateLibrary.customer_support_triage()
        ]

    @staticmethod
    def _create_node(name: str, type: NodeType, x: int, y: int, persona: str = None, provider_config: Dict = None) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "type": type,
            "x": x,
            "y": y,
            "status": NodeStatus.IDLE,
            "persona": persona or "",
            "provider_config": provider_config or {}
        }
        
    @staticmethod
    def _connect(source_id: str, target_id: str) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4())[:8],
            "source": source_id,
            "target": target_id,
            "type": "default"
        }

    @staticmethod
    def social_media_manager() -> Dict[str, Any]:
        nodes = []
        edges = []
        
        # 1. Input
        inp = TemplateLibrary._create_node("Topic Input", NodeType.INPUT, 100, 300)
        nodes.append(inp)
        
        # 2. Researcher
        res = TemplateLibrary._create_node("Trend Researcher", NodeType.AGENT, 400, 200, 
            persona="You are a viral trend researcher. Analyze the given topic for current sentiment, popular angles, and engagement opportunities on Twitter and LinkedIn. Output a list of key points.")
        nodes.append(res)
        
        # 3. Writer
        writer = TemplateLibrary._create_node("Content Drafter", NodeType.AGENT, 700, 200,
            persona="You are a professional social media manager. Based on the research, draft 3 tweets and 1 LinkedIn post. Use engaging hooks and appropriate hashtags.")
        nodes.append(writer)
        
        # 4. Critic
        critic = TemplateLibrary._create_node("Viral Critic", NodeType.AUDITOR, 1000, 300,
            persona="You are a strict editor. Review the drafts for tone, clarity, and viral potential. Reject if they sound robotic or generic. Approve if they are punchy and human.")
        nodes.append(critic)
        
        # Output
        out = TemplateLibrary._create_node("Final Content", NodeType.OUTPUT, 1300, 300)
        nodes.append(out)
        
        # Connections
        edges.append(TemplateLibrary._connect(inp["id"], res["id"]))
        edges.append(TemplateLibrary._connect(res["id"], writer["id"]))
        edges.append(TemplateLibrary._connect(writer["id"], critic["id"]))
        edges.append(TemplateLibrary._connect(critic["id"], out["id"]))
        
        # Feedback Loop (Critic -> Writer)
        fb_edge = TemplateLibrary._connect(critic["id"], writer["id"])
        fb_edge["type"] = "feedback"
        fb_edge["label"] = "Revise"
        edges.append(fb_edge)

        return {
            "id": "social_media_manager",
            "name": "Social Media Manager",
            "description": "Research trends, draft content, and refine with an automated critic loop.",
            "nodes": {n["id"]: n for n in nodes},
            "edges": edges
        }

    @staticmethod
    def deep_research_analyst() -> Dict[str, Any]:
        nodes = []
        edges = []
        
        inp = TemplateLibrary._create_node("Research Query", NodeType.INPUT, 50, 300)
        nodes.append(inp)
        
        strat = TemplateLibrary._create_node("Strategist", NodeType.AGENT, 350, 300,
            persona="You are a lead researcher. Break down the user's query into 3 specific, mutually exclusive sub-questions that need to be answered to provide a comprehensive report.")
        nodes.append(strat)
        
        # Parallel Searchers
        search1 = TemplateLibrary._create_node("Searcher A", NodeType.GOOGLE, 700, 100,
            persona="Research Assistant") 
        nodes.append(search1)
        
        search2 = TemplateLibrary._create_node("Searcher B", NodeType.AGENT, 700, 300,
             persona="You are a Wikipedia researcher. Look up facts and history about the topic.")
        nodes.append(search2)
        
        search3 = TemplateLibrary._create_node("Searcher C", NodeType.AGENT, 700, 500,
             persona="You are a context analyzer. Use your internal knowledge to provide historical context and theoretical framework for the query.")
        nodes.append(search3)
        
        synth = TemplateLibrary._create_node("Synthesizer", NodeType.AGENT, 1100, 300,
             persona="You are a report writer. Compile the findings from all sources into a cohesive Markdown report with citations. rigorous and academic tone.")
        nodes.append(synth)
        
        out = TemplateLibrary._create_node("Final Report", NodeType.OUTPUT, 1400, 300)
        nodes.append(out)
        
        edges.append(TemplateLibrary._connect(inp["id"], strat["id"]))
        edges.append(TemplateLibrary._connect(strat["id"], search1["id"]))
        edges.append(TemplateLibrary._connect(strat["id"], search2["id"]))
        edges.append(TemplateLibrary._connect(strat["id"], search3["id"]))
        edges.append(TemplateLibrary._connect(search1["id"], synth["id"]))
        edges.append(TemplateLibrary._connect(search2["id"], synth["id"]))
        edges.append(TemplateLibrary._connect(search3["id"], synth["id"]))
        edges.append(TemplateLibrary._connect(synth["id"], out["id"]))

        return {
            "id": "deep_research",
            "name": "Deep Research Analyst",
            "description": "Parallel research processing: Strategist splits query, agents gather data, synthesizer compiles report.",
            "nodes": {n["id"]: n for n in nodes},
            "edges": edges
        }

    @staticmethod
    def customer_support_triage() -> Dict[str, Any]:
        nodes = []
        edges = []
        
        inp = TemplateLibrary._create_node("Ticket Data", NodeType.INPUT, 100, 300)
        nodes.append(inp)
        
        classifier = TemplateLibrary._create_node("Triage Agent", NodeType.ROUTER, 400, 300,
            persona="Analyze the incoming support ticket. Route to 'billing' if payment related, 'technical' if bug related, or 'general' otherwise.")
        nodes.append(classifier)
        
        # Branches
        billing = TemplateLibrary._create_node("Billing Support", NodeType.AGENT, 800, 100,
            persona="You are billing support. Handle refund requests and invoice questions politely. Verify policy compliance.")
        nodes.append(billing)
        
        tech = TemplateLibrary._create_node("Tech Support", NodeType.AGENT, 800, 300,
            persona="You are Tier 2 Technical Support. Debug the issue, ask for logs if needed, and provide step-by-step solutions.")
        nodes.append(tech)
        
        general = TemplateLibrary._create_node("General Inquiry", NodeType.AGENT, 800, 500,
            persona="You are Customer Care. Answer general questions about the product, hours, and location.")
        nodes.append(general)
        
        qc = TemplateLibrary._create_node("QA Check", NodeType.AUDITOR, 1200, 300,
            persona="Review the draft response. Ensure it is polite, empathetic, and grammatically correct.")
        nodes.append(qc)
        
        # Output
        out = TemplateLibrary._create_node("Send Email", NodeType.OUTPUT, 1500, 300)
        nodes.append(out)
        
        # Connections
        edges.append(TemplateLibrary._connect(inp["id"], classifier["id"]))
        
        # Router Connections
        e1 = TemplateLibrary._connect(classifier["id"], billing["id"])
        e1["label"] = "Billing"
        e1["condition"] = "billing" # Simplified router logic match
        edges.append(e1)
        
        e2 = TemplateLibrary._connect(classifier["id"], tech["id"])
        e2["label"] = "Technical"
        e2["condition"] = "technical"
        edges.append(e2)
        
        e3 = TemplateLibrary._connect(classifier["id"], general["id"])
        e3["label"] = "General"
        e3["condition"] = "general"
        edges.append(e3)
        
        # Merit loop
        edges.append(TemplateLibrary._connect(billing["id"], qc["id"]))
        edges.append(TemplateLibrary._connect(tech["id"], qc["id"]))
        edges.append(TemplateLibrary._connect(general["id"], qc["id"]))
        
        edges.append(TemplateLibrary._connect(qc["id"], out["id"]))
        
        return {
            "id": "support_triage",
            "name": "Customer Support Triage",
            "description": "Smart routing of tickets to specialized agents (Billing, Tech, General) with QA review.",
            "nodes": {n["id"]: n for n in nodes},
            "edges": edges
        }
