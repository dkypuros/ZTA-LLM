"""
Model Context Protocol (MCP) Server Implementation

Implements the MCP server as described in the paper, providing
secure tool routing with schema validation and local inference
integration.
"""

from .server import MCPServer
from .tool_registry import ToolRegistry, SecureTool
from .schema_validator import SchemaValidator, ValidationError
from .local_inference import LocalInferenceEngine

__all__ = [
    "MCPServer",
    "ToolRegistry", 
    "SecureTool",
    "SchemaValidator",
    "ValidationError",
    "LocalInferenceEngine"
]

__version__ = "1.0.0"