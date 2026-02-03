
import json
import aiohttp
from typing import Dict, List, Any, Optional

class OpenAPIParser:
    """
    Utility to parse OpenAPI/Swagger specifications and extract operations.
    """
    
    @staticmethod
    async def parse_from_url(url: str) -> Dict[str, Any]:
        """Fetch and parse OpenAPI spec from URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to fetch spec from {url}: {response.status}")
                text = await response.text()
                try:
                    spec = json.loads(text)
                except json.JSONDecodeError:
                    # Try YAML if needed, but for now strict JSON or text
                    raise ValueError("Invalid JSON content")
                    
        return OpenAPIParser.parse_spec(spec)

    @staticmethod
    def parse_from_text(text: str) -> Dict[str, Any]:
        """Parse OpenAPI spec from JSON string."""
        spec = json.loads(text)
        return OpenAPIParser.parse_spec(spec)

    @staticmethod
    def parse_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract operations from the spec.
        Returns a simplified structure:
        {
            "title": "API Title",
            "version": "1.0",
            "server": "https://api.example.com",
            "operations": [
                {
                    "id": "operationId" or "METHOD /path",
                    "method": "GET",
                    "path": "/users",
                    "summary": "Get users",
                    "description": "...",
                    "params": [...],
                    "body_schema": {...} 
                }
            ]
        }
        """
        result = {
            "title": spec.get("info", {}).get("title", "Unknown API"),
            "version": spec.get("info", {}).get("version", ""),
            "server": spec.get("servers", [{}])[0].get("url", "") if "servers" in spec else "",
            "operations": []
        }
        
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                    
                op_id = details.get("operationId", f"{method.upper()} {path}")
                summary = details.get("summary", "")
                
                # Extract parameters
                params = []
                # Path-level params
                if "parameters" in methods:
                    params.extend(methods["parameters"])
                # Op-level params
                if "parameters" in details:
                    params.extend(details["parameters"])
                    
                # Normalize params
                normalized_params = []
                for p in params:
                    # Resolve refs if simpler, but ignoring generic ref resolution for now
                    if "$ref" in p: 
                        continue # Skip refs in MVP
                    normalized_params.append({
                        "name": p.get("name"),
                        "in": p.get("in"), # query, path, header
                        "required": p.get("required", False),
                        "description": p.get("description", "")
                    })
                    
                op = {
                    "id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "params": normalized_params,
                }
                result["operations"].append(op)
                
        return result
