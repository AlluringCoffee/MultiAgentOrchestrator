import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TelegramTrigger:
    """
    Handles communication with Telegram Bot API.
    Can be used as a trigger (incoming) or a node (outgoing).
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.token = config.get("bot_token")
        self.default_chat_id = config.get("chat_id")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def execute(self, inputs: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """Send a message to Telegram."""
        if not self.token:
            return {"ok": False, "error": "No Bot Token provided"}

        text = inputs.get("text") or context or "No content provided"
        chat_id = inputs.get("chat_id") or self.default_chat_id

        if not chat_id:
            return {"ok": False, "error": "No Chat ID provided"}

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            try:
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        return {"ok": True, "output": text, "message_id": result["result"]["message_id"]}
                    else:
                        return {"ok": False, "error": result.get("description")}
            except Exception as e:
                return {"ok": False, "error": str(e)}

class DiscordTrigger:
    """
    Handles communication with Discord via Webhooks or Bot API.
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.webhook_url = config.get("webhook_url")
        self.bot_token = config.get("bot_token")
        self.channel_id = config.get("channel_id")

    async def execute(self, inputs: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """Send a message to Discord."""
        text = inputs.get("text") or context or "No content provided"
        
        # Priority 1: Webhook
        if self.webhook_url:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(self.webhook_url, json={"content": text}) as resp:
                        if resp.status in [200, 204]:
                            return {"ok": True, "output": text}
                        else:
                            return {"ok": False, "error": f"Discord Webhook error: {resp.status}"}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        
        # Priority 2: Bot API
        elif self.bot_token and self.channel_id:
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
            headers = {"Authorization": f"Bot {self.bot_token}"}
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, headers=headers, json={"content": text}) as resp:
                        result = await resp.json()
                        if resp.status == 200:
                            return {"ok": True, "output": text}
                        else:
                            return {"ok": False, "error": result.get("message", "Unknown error")}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        
        return {"ok": False, "error": "Neither Webhook URL nor Bot Token/Channel ID provided"}
