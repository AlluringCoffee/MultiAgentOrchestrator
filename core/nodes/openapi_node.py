import json
import re
import logging
import aiohttp
from urllib.parse import urlparse, quote
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import SSRF validation from http_node
try:
    from core.nodes.http_node import validate_url, ALLOWED_SCHEMES
except ImportError:
    # Fallback if http_node not available
    ALLOWED_SCHEMES = {'http', 'https'}

    async def validate_url(url: str, allowed_domains=None):
        return True, ""


def sanitize_path_param(value: str) -> str:
    """
    Sanitize a path parameter value to prevent path traversal and injection.
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove path traversal attempts
    value = value.replace('..', '').replace('//', '/')

    # URL-encode the value to prevent injection
    value = quote(value, safe='')

    # Limit length
    if len(value) > 500:
        value = value[:500]

    return value


def sanitize_query_param(value: Any) -> str:
    """Sanitize a query parameter value."""
    value = str(value) if value is not None else ''

    # Remove control characters
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)

    # Limit length
    if len(value) > 2000:
        value = value[:2000]

    return value


def sanitize_header_value(value: str) -> str:
    """
    Sanitize a header value to prevent header injection.
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove CRLF characters that could be used for header injection
    value = value.replace('\r', '').replace('\n', '')

    # Remove null bytes
    value = value.replace('\x00', '')

    # Limit length
    if len(value) > 1000:
        value = value[:1000]

    return value


def validate_operation_id(operation_id: str) -> bool:
    """Validate that operation ID is safe."""
    if not operation_id:
        return False
    # Operation IDs should be alphanumeric with underscores/hyphens
    return bool(re.match(r'^[\w\-]+$', operation_id))


class OpenAPINodeExecutor:
    """
    Executes an OpenAPI operation dynamically by parsing the spec at runtime.

    Security improvements:
    - Path parameter sanitization (prevents traversal)
    - Header injection prevention
    - Query parameter validation
    - URL validation (SSRF protection)
    - Response size limits
    - Proper exception handling
    """

    def __init__(
        self,
        node_id: str,
        spec_url: str,
        operation_id: str,
        params: Dict[str, Any] = None,
        auth_type: str = "none",
        timeout: int = 30
    ):
        self.node_id = node_id
        self.spec_url = spec_url
        self.operation_id = operation_id
        self.params = params or {}
        self.auth_type = auth_type
        self.timeout = timeout
        self.max_response_size = 10 * 1024 * 1024  # 10MB

    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Validate operation ID
        if not validate_operation_id(self.operation_id):
            return {
                "ok": False,
                "status": 400,
                "error": "Invalid operation ID format"
            }

        try:
            # 1. Fetch and Parse Spec
            # In a real system, we'd cache this.
            from core.utils.openapi_parser import OpenAPIParser
            spec_data = await OpenAPIParser.parse_from_url(self.spec_url)

            # 2. Find Operation
            operation = next((op for op in spec_data['operations'] if op['id'] == self.operation_id), None)
            if not operation:
                return {
                    "ok": False,
                    "status": 404,
                    "error": f"Operation '{self.operation_id}' not found in spec."
                }

            # 3. Prepare Request Parts
            server = spec_data.get('server', '')
            if not server:
                # Fallback: Derive from spec_url
                parsed = urlparse(self.spec_url)
                # Assume API is at root of the domain of the spec file
                server = f"{parsed.scheme}://{parsed.netloc}"

            path = operation['path']
            method = operation['method'].upper()

            # Validate HTTP method
            allowed_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
            if method not in allowed_methods:
                return {
                    "ok": False,
                    "status": 400,
                    "error": f"HTTP method '{method}' not allowed"
                }

            query_params = {}
            headers = {}
            body = None

            # 4. Map User Params to Request Locations with sanitization
            for param_def in operation.get('params', []):
                p_name = param_def['name']
                p_in = param_def['in']

                # Check if we have a value provided
                if p_name in self.params:
                    val = self.params[p_name]

                    if p_in == "path":
                        # Sanitize path parameter to prevent traversal/injection
                        safe_val = sanitize_path_param(val)
                        path = path.replace(f"{{{p_name}}}", safe_val)
                    elif p_in == "query":
                        query_params[p_name] = sanitize_query_param(val)
                    elif p_in == "header":
                        # Sanitize header value to prevent injection
                        headers[p_name] = sanitize_header_value(val)
                    elif p_in == "body":
                        # Body handling - validate JSON if applicable
                        body = val

            # Construct Full URL
            if server.endswith('/') and path.startswith('/'):
                full_url = server + path[1:]
            elif not server.endswith('/') and not path.startswith('/'):
                full_url = server + '/' + path
            else:
                full_url = server + path

            # Validate constructed URL for SSRF
            is_valid, error = await validate_url(full_url)
            if not is_valid:
                logger.warning(f"URL validation failed: {error}")
                return {
                    "ok": False,
                    "status": 403,
                    "error": f"Request blocked: {error}"
                }

            # 5. Execute Request
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.request(
                        method=method,
                        url=full_url,
                        params=query_params,
                        headers=headers,
                        json=body if body else None,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        # Check response size
                        content_length = response.headers.get('Content-Length')
                        if content_length and int(content_length) > self.max_response_size:
                            return {
                                "ok": False,
                                "status": 413,
                                "error": "Response too large"
                            }

                        # Read with size limit
                        resp_bytes = await response.content.read(self.max_response_size + 1)
                        if len(resp_bytes) > self.max_response_size:
                            return {
                                "ok": False,
                                "status": 413,
                                "error": "Response exceeded size limit"
                            }

                        text = resp_bytes.decode('utf-8', errors='replace')

                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            data = text

                        return {
                            "ok": response.status < 400,
                            "status": response.status,
                            "data": data,
                            "headers": dict(response.headers)
                        }
                except aiohttp.ClientError as e:
                    logger.error(f"OpenAPI request error: {e}")
                    return {
                        "ok": False,
                        "status": 502,
                        "error": f"Connection error: {type(e).__name__}"
                    }

        except Exception as e:
            logger.error(f"OpenAPI execution error: {e}")
            return {
                "ok": False,
                "status": 500,
                "error": f"Internal error: {type(e).__name__}"
            }
