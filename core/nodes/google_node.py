
import json
import base64
import aiohttp
from typing import Dict, Any, Optional

class GoogleNode:
    """
    Managed Connector for Google Workspace APIs (Gmail, Calendar).
    Assumes a valid OAuth Access Token is provided.
    """
    
    def __init__(
        self,
        node_id: str,
        api_token: str,
        service: str, # 'gmail', 'calendar'
        operation: str, # 'send_email', 'list_messages', 'list_events', 'create_event'
        params: Dict[str, Any] = None,
        body: Dict[str, Any] = None,
        timeout: int = 30
    ):
        self.node_id = node_id
        self.api_token = api_token
        self.service = service
        self.operation = operation
        self.params = params or {}
        self.body = body or {}
        self.timeout = timeout
        
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        if not self.api_token:
             return {"ok": False, "status": 401, "error": "Missing Google Access Token"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        url = ""
        method = "GET"
        data = None
        
        try:
            # ============ GMAIL ============
            if self.service == "gmail":
                base_url = "https://gmail.googleapis.com/gmail/v1/users/me"
                
                if self.operation == "list_messages":
                    # GET /messages
                    url = f"{base_url}/messages"
                    method = "GET"
                    
                elif self.operation == "send_email":
                    # POST /messages/send
                    url = f"{base_url}/messages/send"
                    method = "POST"
                    
                    # Construct Raw Email
                    to = self.body.get("to")
                    subject = self.body.get("subject", "(No Subject)")
                    message_text = self.body.get("body", "")
                    
                    if not to:
                        return {"ok": False, "status": 400, "error": "Gmail: 'to' field required"}

                    # Simple MIME construction
                    email_content = f"To: {to}\r\nSubject: {subject}\r\n\r\n{message_text}"
                    raw = base64.urlsafe_b64encode(email_content.encode('utf-8')).decode('utf-8')
                    data = {"raw": raw}
            
            # ============ CALENDAR ============
            elif self.service == "calendar":
                base_url = "https://www.googleapis.com/calendar/v3"
                calendar_id = self.params.get("calendar_id", "primary")
                
                if self.operation == "list_events":
                    # GET /calendars/{calendarId}/events
                    url = f"{base_url}/calendars/{calendar_id}/events"
                    method = "GET"
                    
                elif self.operation == "create_event":
                    # POST /calendars/{calendarId}/events
                    url = f"{base_url}/calendars/{calendar_id}/events"
                    method = "POST"
                    
                    # Default body checks
                    summary = self.body.get("summary")
                    start_time = self.body.get("start_time") # ISO strings
                    end_time = self.body.get("end_time")
                    
                    if not summary or not start_time:
                         return {"ok": False, "status": 400, "error": "Calendar: 'summary' and 'start_time' required"}
                         
                    # Use provided body or construct one
                    data = self.body
            
            else:
                 return {"ok": False, "status": 400, "error": f"Unknown service: {self.service}"}

            
            # Execute
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
