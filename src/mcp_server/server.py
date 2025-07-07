"""
MCP Server Implementation for Secure Tool Routing

Implements the Model Context Protocol server with comprehensive
schema validation and security controls as described in the paper.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .tool_registry import ToolRegistry, SecureTool, ToolExecutionResult
from .schema_validator import SchemaValidator, ValidationError
from .local_inference import LocalInferenceEngine


class MCPMethod(Enum):
    """MCP protocol methods."""
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"


class MCPRequest(BaseModel):
    """MCP request structure."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    """MCP response structure."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP error structure."""
    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    host: str = "0.0.0.0"
    port: int = 8081
    max_request_size: int = 1048576  # 1MB
    request_timeout: float = 30.0
    enable_local_inference: bool = True
    local_inference_endpoint: str = "http://vllm-server:8000"
    tool_execution_timeout: float = 30.0
    schema_validation_strict: bool = True
    enable_audit_logging: bool = True


class MCPServer:
    """
    Secure MCP Server implementation.
    
    Provides secure tool routing with comprehensive validation
    and integration with local inference engines.
    """
    
    def __init__(self, config: MCPServerConfig = None):
        self.config = config or MCPServerConfig()
        self.tool_registry = ToolRegistry()
        self.schema_validator = SchemaValidator()
        self.local_inference = None
        
        if self.config.enable_local_inference:
            self.local_inference = LocalInferenceEngine(
                endpoint=self.config.local_inference_endpoint
            )
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="ZTA-LLM MCP Server",
            description="Secure Model Context Protocol Server",
            version="1.0.0"
        )
        
        # Add CORS middleware with restrictions
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:8080"],  # Only security wrapper
            allow_credentials=True,
            allow_methods=["POST"],  # Only POST for MCP
            allow_headers=["*"],
        )
        
        self._setup_routes()
        self._setup_middleware()
        
        # Statistics tracking
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "validation_errors": 0,
            "tool_executions": 0,
            "avg_response_time_ms": 0.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_routes(self):
        """Setup MCP protocol routes."""
        
        @self.app.post("/mcp/v1")
        async def handle_mcp_request(request: Request):
            """Main MCP request handler."""
            start_time = time.time()
            
            try:
                # Parse request body
                body = await request.body()
                request_data = json.loads(body)
                
                # Validate MCP request structure
                mcp_request = MCPRequest(**request_data)
                
                # Update statistics
                self._stats["total_requests"] += 1
                
                # Route to appropriate handler
                result = await self._route_request(mcp_request, request)
                
                # Create response
                response = MCPResponse(
                    id=mcp_request.id,
                    result=result
                )
                
                self._stats["successful_requests"] += 1
                
                return response.dict()
                
            except ValidationError as e:
                self._stats["validation_errors"] += 1
                self._stats["failed_requests"] += 1
                
                error_response = MCPResponse(
                    id=request_data.get("id") if "request_data" in locals() else None,
                    error=MCPError(
                        code=-32602,  # Invalid params
                        message="Validation error",
                        data=str(e)
                    ).dict()
                )
                
                return JSONResponse(
                    status_code=400,
                    content=error_response.dict()
                )
                
            except Exception as e:
                self._stats["failed_requests"] += 1
                self.logger.error(f"Unexpected error: {e}")
                
                error_response = MCPResponse(
                    id=request_data.get("id") if "request_data" in locals() else None,
                    error=MCPError(
                        code=-32603,  # Internal error
                        message="Internal server error",
                        data=str(e) if self.config.schema_validation_strict else None
                    ).dict()
                )
                
                return JSONResponse(
                    status_code=500,
                    content=error_response.dict()
                )
            
            finally:
                # Update timing statistics
                processing_time = (time.time() - start_time) * 1000
                self._update_timing_stats(processing_time)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "stats": self._stats,
                "local_inference": False
            }
            
            if self.local_inference:
                health_status["local_inference"] = await self.local_inference.health_check()
            
            return health_status
        
        @self.app.get("/metrics")
        async def metrics():
            """Prometheus-style metrics endpoint."""
            return {
                "mcp_requests_total": self._stats["total_requests"],
                "mcp_requests_successful": self._stats["successful_requests"], 
                "mcp_requests_failed": self._stats["failed_requests"],
                "mcp_validation_errors": self._stats["validation_errors"],
                "mcp_tool_executions": self._stats["tool_executions"],
                "mcp_avg_response_time_ms": self._stats["avg_response_time_ms"],
                "mcp_tools_registered": self.tool_registry.get_tool_count()
            }
    
    def _setup_middleware(self):
        """Setup security middleware."""
        
        @self.app.middleware("http")
        async def security_middleware(request: Request, call_next):
            """Security middleware for additional validation."""
            
            # Check request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.config.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large"}
                )
            
            # Add security headers
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["X-ZTA-MCP-Version"] = "1.0.0"
            
            return response
    
    async def _route_request(self, mcp_request: MCPRequest, request: Request) -> Dict[str, Any]:
        """Route MCP request to appropriate handler."""
        
        method = MCPMethod(mcp_request.method)
        
        if method == MCPMethod.TOOLS_LIST:
            return await self._handle_tools_list(mcp_request)
        elif method == MCPMethod.TOOLS_CALL:
            return await self._handle_tools_call(mcp_request, request)
        elif method == MCPMethod.RESOURCES_LIST:
            return await self._handle_resources_list(mcp_request)
        elif method == MCPMethod.RESOURCES_READ:
            return await self._handle_resources_read(mcp_request)
        elif method == MCPMethod.PROMPTS_LIST:
            return await self._handle_prompts_list(mcp_request)
        elif method == MCPMethod.PROMPTS_GET:
            return await self._handle_prompts_get(mcp_request)
        else:
            raise ValidationError(f"Unknown method: {mcp_request.method}")
    
    async def _handle_tools_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.tool_registry.list_tools()
        
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "security_level": tool.security_level.value
                }
                for tool in tools
            ]
        }
    
    async def _handle_tools_call(self, request: MCPRequest, http_request: Request) -> Dict[str, Any]:
        """Handle tools/call request with security validation."""
        
        # Validate required parameters
        if "name" not in request.params:
            raise ValidationError("Tool name is required")
        
        tool_name = request.params["name"]
        tool_arguments = request.params.get("arguments", {})
        
        # Validate tool exists and is safe
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValidationError(f"Tool not found: {tool_name}")
        
        # Schema validation
        self.schema_validator.validate_tool_input(tool, tool_arguments)
        
        # Check if tool requires local inference
        if tool.requires_local_inference and not self.local_inference:
            raise ValidationError("Tool requires local inference but it's not available")
        
        # Execute tool with timeout
        try:
            self._stats["tool_executions"] += 1
            
            execution_result = await asyncio.wait_for(
                self.tool_registry.execute_tool(
                    tool_name,
                    tool_arguments,
                    local_inference=self.local_inference
                ),
                timeout=self.config.tool_execution_timeout
            )
            
            # Validate output
            self.schema_validator.validate_tool_output(tool, execution_result.result)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": execution_result.result
                    }
                ],
                "isError": execution_result.is_error,
                "execution_time_ms": execution_result.execution_time_ms,
                "security_validated": True
            }
            
        except asyncio.TimeoutError:
            raise ValidationError(f"Tool execution timeout: {tool_name}")
    
    async def _handle_resources_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle resources/list request."""
        # In a real implementation, this would list available resources
        return {"resources": []}
    
    async def _handle_resources_read(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle resources/read request."""
        # In a real implementation, this would read a specific resource
        raise ValidationError("Resource reading not implemented in demo")
    
    async def _handle_prompts_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle prompts/list request."""
        # In a real implementation, this would list available prompts
        return {"prompts": []}
    
    async def _handle_prompts_get(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle prompts/get request."""
        # In a real implementation, this would get a specific prompt
        raise ValidationError("Prompt retrieval not implemented in demo")
    
    def _update_timing_stats(self, processing_time_ms: float):
        """Update timing statistics."""
        current_avg = self._stats["avg_response_time_ms"]
        total_requests = self._stats["total_requests"]
        
        if total_requests > 0:
            self._stats["avg_response_time_ms"] = (
                (current_avg * (total_requests - 1) + processing_time_ms) / total_requests
            )
    
    def register_tool(self, tool: SecureTool):
        """Register a new tool with the server."""
        self.tool_registry.register_tool(tool)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            **self._stats,
            "tools_registered": self.tool_registry.get_tool_count(),
            "local_inference_enabled": self.config.enable_local_inference
        }
    
    async def start(self):
        """Start the MCP server."""
        import uvicorn
        
        await uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )