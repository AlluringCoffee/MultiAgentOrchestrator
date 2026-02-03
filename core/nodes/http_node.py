import asyncio
import aiohttp
import json
import logging
import re
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# SSRF Protection: Block requests to internal/private networks
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),       # Private Class A
    ipaddress.ip_network('172.16.0.0/12'),    # Private Class B
    ipaddress.ip_network('192.168.0.0/16'),   # Private Class C
    ipaddress.ip_network('127.0.0.0/8'),      # Loopback
    ipaddress.ip_network('169.254.0.0/16'),   # Link-local
    ipaddress.ip_network('::1/128'),          # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),         # IPv6 private
    ipaddress.ip_network('fe80::/10'),        # IPv6 link-local
]

# Blocked hostnames
BLOCKED_HOSTNAMES = {
    'localhost',
    'localhost.localdomain',
    '0.0.0.0',
    'metadata.google.internal',       # GCP metadata
    '169.254.169.254',                # AWS/Azure metadata
    'metadata.azure.com',
}

# Allowed protocols
ALLOWED_SCHEMES = {'http', 'https'}

# Maximum response size (10MB)
MAX_RESPONSE_SIZE = 10 * 1024 * 1024


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is in a private/blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


async def validate_url(url: str, allowed_domains: Set[str] = None) -> tuple[bool, str]:
    """
    Validate a URL for SSRF and other security issues.

    Returns:
        (is_valid, error_message)
    """
    if not url:
        return False, "Empty URL"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Check scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Protocol '{parsed.scheme}' not allowed. Use http or https."

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "No hostname in URL"

    hostname_lower = hostname.lower()

    # Block known internal hostnames
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Access to '{hostname}' is blocked for security"

    # Check for IP address
    if is_private_ip(hostname):
        return False, f"Access to private IP ranges is blocked"

    # Check domain whitelist if configured
    if allowed_domains:
        if not any(hostname_lower.endswith(domain.lower()) for domain in allowed_domains):
            return False, f"Domain '{hostname}' not in allowed list"

    # Block URLs with credentials
    if parsed.username or parsed.password:
        return False, "URLs with embedded credentials are not allowed"

    # Block suspicious port numbers (commonly used for internal services)
    blocked_ports = {22, 23, 25, 135, 137, 138, 139, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 27017}
    if parsed.port and parsed.port in blocked_ports:
        return False, f"Port {parsed.port} is blocked for security"

    return True, ""


def sanitize_interpolation_value(value: str) -> str:
    """Sanitize a value before string interpolation to prevent injection."""
    if not isinstance(value, str):
        value = str(value)

    # Remove or escape potentially dangerous characters for JSON/URL contexts
    # Remove null bytes and control characters
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)

    # Limit length
    max_length = 10000
    if len(value) > max_length:
        value = value[:max_length]

    return value


class HttpNode:
    """
    Universal HTTP client node.
    Supports variable interpolation from blackboard/inputs.

    Security improvements:
    - SSRF protection (blocks private IPs and internal hostnames)
    - URL validation and sanitization
    - Response size limits
    - Protocol restrictions (http/https only)
    - Optional domain whitelist
    - Proper exception handling
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.allowed_domains: Set[str] = set(config.get("allowed_domains", []))
        self.timeout = config.get("timeout", 30)
        self.max_response_size = config.get("max_response_size", MAX_RESPONSE_SIZE)

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        url = self.config.get("url")
        method = self.config.get("method", "GET").upper()
        headers = self.config.get("headers", {})
        body = self.config.get("body")

        if not url:
            return {"ok": False, "error": "No URL provided"}

        # Validate HTTP method
        allowed_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
        if method not in allowed_methods:
            return {"ok": False, "error": f"HTTP method '{method}' not allowed"}

        # Validate URL for SSRF
        is_valid, error = await validate_url(url, self.allowed_domains or None)
        if not is_valid:
            logger.warning(f"URL validation failed for {url}: {error}")
            return {"ok": False, "error": f"URL blocked: {error}"}

        # Variable Interpolation with sanitization
        if isinstance(body, str):
            input_value = sanitize_interpolation_value(inputs.get("text", ""))
            body = body.replace("{input}", input_value)
            if context and isinstance(context, str):
                context_value = sanitize_interpolation_value(context)
                body = body.replace("{context}", context_value)

        async with aiohttp.ClientSession() as session:
            try:
                # Prepare request arguments
                kwargs = {
                    "headers": headers,
                    "timeout": aiohttp.ClientTimeout(total=self.timeout)
                }

                if body:
                    if isinstance(body, dict):
                        kwargs["json"] = body
                    else:
                        kwargs["data"] = body

                async with session.request(method, url, **kwargs) as response:
                    status = response.status

                    # Check response size before reading
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_response_size:
                        return {"ok": False, "error": f"Response too large ({content_length} bytes)"}

                    # Read response with size limit
                    try:
                        resp_bytes = await response.content.read(self.max_response_size + 1)
                        if len(resp_bytes) > self.max_response_size:
                            return {"ok": False, "error": "Response exceeded size limit"}
                        resp_text = resp_bytes.decode('utf-8', errors='replace')
                    except Exception as e:
                        logger.error(f"Error reading response: {e}")
                        return {"ok": False, "error": "Error reading response"}

                    # Try to parse as JSON
                    try:
                        resp_data = json.loads(resp_text)
                        resp_text = json.dumps(resp_data, indent=2)
                    except json.JSONDecodeError:
                        resp_data = {"raw": resp_text}

                    if 200 <= status < 300:
                        return {
                            "ok": True,
                            "output": resp_text,
                            "data": {
                                "status": status,
                                "response": resp_data
                            }
                        }
                    else:
                        return {
                            "ok": False,
                            "error": f"HTTP {status}",
                            "data": {
                                "status": status,
                                "response": resp_data
                            }
                        }
            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error: {e}")
                return {"ok": False, "error": f"Connection error: {type(e).__name__}"}
            except asyncio.TimeoutError:
                return {"ok": False, "error": f"Request timed out after {self.timeout}s"}
            except Exception as e:
                logger.error(f"HTTP Request failed: {e}")
                return {"ok": False, "error": f"Request failed: {type(e).__name__}"}
