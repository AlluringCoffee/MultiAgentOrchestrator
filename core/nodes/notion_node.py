
import json
import aiohttp
from typing import Dict, Any, Optional

class NotionNode:
    """
    Managed Connector for Notion API.
    """
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(
        self,
        node_id: str,
        api_key: str,
        operation: str, # 'query_database', 'create_page', 'get_page', 'append_block'
        resource_id: str, # database_id or page_id
        params: Dict[str, Any] = None,
        body: Dict[str, Any] = None,
        timeout: int = 30
    ):
        self.node_id = node_id
        self.api_key = api_key
        self.operation = operation
        self.resource_id = resource_id
        self.params = params or {}
        self.body = body or {}
        self.timeout = timeout
        
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        if not self.api_key:
             return {"ok": False, "status": 401, "error": "Missing Notion API Key"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        url = ""
        method = "GET"
        data = None
        
        try:
            if self.operation == "query_database":
                # POST https://api.notion.com/v1/databases/{database_id}/query
                url = f"{self.BASE_URL}/databases/{self.resource_id}/query"
                method = "POST"
                data = self.body # Filter/Sort criteria
                
            elif self.operation == "get_page":
                # GET https://api.notion.com/v1/pages/{page_id}
                url = f"{self.BASE_URL}/pages/{self.resource_id}"
                method = "GET"
                
            elif self.operation == "create_page":
                # POST https://api.notion.com/v1/pages
                url = f"{self.BASE_URL}/pages"
                method = "POST"
                # Need 'parent' in body
                data = self.body
                
            elif self.operation == "append_block":
                # PATCH https://api.notion.com/v1/blocks/{block_id}/children
                url = f"{self.BASE_URL}/blocks/{self.resource_id}/children"
                method = "PATCH"
                data = self.body # { "children": [...] }
            
            else:
                return {"ok": False, "status": 400, "error": f"Unknown operation: {self.operation}"}
                
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                ) as response:
                    text = await response.text()
                    try:
                        resp_data = json.loads(text)
                    except:
                        resp_data = text
                        
                    return {
                        "ok": response.ok,
                        "status": response.status,
                        "data": resp_data
                    }
                    
        except Exception as e:
            return {
                "ok": False,
                "status": 500,
                "error": str(e)
            }
