import json
import base64
import warnings

# Suppress the pkg_resources deprecation warning from old protobuf versions
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")


def format_body(body: bytes, content_type: str = "") -> str:
    """
    Format body content based on content type.
    Returns a human-readable string representation.
    
    Args:
        body: Raw body bytes
        content_type: MIME type from headers (e.g., 'application/json')
    
    Returns:
        Formatted string representation of the body
    """
    if not body:
        return ""
    
    content_type = content_type.lower()
    
    # Try protobuf first if content type matches
    if "protobuf" in content_type:
        return _format_protobuf(body)
    
    # Try to decode as text
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        # Binary data - return base64
        return f"<binary data, base64: {base64.b64encode(body).decode()}>"
    
    # Format JSON
    if "json" in content_type or text.strip().startswith(("{", "[")):
        return _format_json(text)
    
    # Format XML
    if "xml" in content_type or text.strip().startswith("<"):
        return _format_xml(text)
    
    # Plain text
    return text


def _format_json(text: str) -> str:
    """Pretty print JSON"""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return text


def _format_xml(text: str) -> str:
    """Pretty print XML"""
    try:
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(text)
        return dom.toprettyxml(indent="  ")
    except Exception:
        return text


def _format_protobuf(body: bytes) -> str:
    """Decode protobuf to JSON-like format"""
    try:
        import blackboxprotobuf
        decoded, message_type = blackboxprotobuf.protobuf_to_json(body)
        # Pretty print the JSON output
        data = json.loads(decoded)
        return f"<protobuf decoded>\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    except ImportError:
        # blackboxprotobuf not installed
        return f"<protobuf - install blackboxprotobuf to decode>\n{base64.b64encode(body).decode()}"
    except Exception as e:
        # Failed to decode
        return f"<protobuf decode failed: {e}>\n{base64.b64encode(body).decode()}"
