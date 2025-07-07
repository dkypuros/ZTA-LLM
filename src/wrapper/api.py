"""
FastAPI application for Security Wrapper - Layer 1 Security
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import time

from .security_wrapper import SecurityWrapper, SecurityLevel

app = FastAPI(
    title="ZTA-LLM Security Wrapper",
    description="Layer 1 Application Security Controls",
    version="1.0.0"
)

# Initialize security wrapper
wrapper = SecurityWrapper()

class PromptRequest(BaseModel):
    prompt: str
    context: Optional[Dict] = None

class ProcessingResponse(BaseModel):
    status: str
    sanitized_prompt: Optional[str] = None
    reason: Optional[str] = None
    processing_time_ms: float

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "security-wrapper",
        "layer": "1",
        "timestamp": time.time()
    }

@app.post("/process", response_model=ProcessingResponse)
async def process_prompt(request: PromptRequest):
    """Process prompt through Layer 1 security controls"""
    try:
        result = wrapper.process_prompt(
            prompt=request.prompt,
            context=request.context
        )
        
        return ProcessingResponse(
            status=result["status"],
            sanitized_prompt=result.get("sanitized_prompt"),
            reason=result.get("reason"),
            processing_time_ms=result["processing_time_ms"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Security metrics endpoint"""
    return wrapper.get_stats()

@app.get("/config")
async def get_config():
    """Get current security configuration"""
    return {
        "security_level": wrapper.config.security_level.value,
        "secret_detection_enabled": wrapper.config.secret_detection_enabled,
        "path_aliasing_enabled": wrapper.config.path_aliasing_enabled,
        "prompt_padding_enabled": wrapper.config.prompt_padding_enabled
    }