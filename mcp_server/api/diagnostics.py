"""
API endpoints for diagnostic telemetry data.
"""

from typing import Dict, List, Any, Optional, TypedDict, cast

from fastapi import APIRouter, Depends

from mcp_server.telemetry.neo4j_client import TelemetryNeo4jClient
from mcp_server.telemetry.shared import telemetry_client
from mcp_server.telemetry.diagnostic_queries import (
    EPISODE_HISTORY_QUERY,
    ERROR_PATTERNS_QUERY,
    EPISODES_WITH_ERROR_TYPE_QUERY,
    STEP_FAILURES_QUERY,
    PROCESSING_STATS_QUERY,
    STEP_TIMING_QUERY,
    RECENT_ERRORS_QUERY
)

# MCP will be imported in graphiti_mcp_server.py and passed to this module
mcp = None

# Tool response types
class DiagnosticResponse(TypedDict):
    data: Any
    message: str

class ErrorResponse(TypedDict):
    error: str

router = APIRouter()

def setup_mcp_tools(mcp_instance):
    """Register MCP tools.
    
    Args:
        mcp_instance: The MCP server instance to register tools with
    """
    global mcp
    mcp = mcp_instance
    
    # Register tools if MCP is available
    if mcp:
        mcp.tool()(get_episode_trace_tool)
        mcp.tool()(get_error_patterns_tool)
        mcp.tool()(get_episodes_with_error_tool)
        mcp.tool()(get_telemetry_stats_tool)
        mcp.tool()(get_recent_errors_tool)

def format_episode_trace(result):
    """Format the episode trace data for better readability."""
    if not result:
        return {"error": "Episode not found"}
    
    episode_data = result[0].get('log', {})
    steps = []
    
    for record in result:
        step = record.get('step')
        error = record.get('error')
        
        if step:
            step_data = {
                "step_name": step.get("step_name"),
                "status": step.get("status"),
                "start_time": step.get("start_time"),
                "end_time": step.get("end_time"),
                "data": step.get("data", {})
            }
            
            if error:
                step_data["error"] = {
                    "error_type": error.get("error_type"),
                    "error_message": error.get("error_message"),
                    "stack_trace": error.get("stack_trace"),
                    "resolution_status": error.get("resolution_status")
                }
            
            steps.append(step_data)
    
    return {
        "episode": episode_data,
        "steps": steps
    }

# MCP tool for getting episode trace
async def get_episode_trace_tool(episode_id: str) -> DiagnosticResponse | ErrorResponse:
    """Get the full processing trace for an episode.
    
    This tool provides detailed information about all processing steps and errors that occurred
    during the processing of a specific episode.
    
    Args:
        episode_id: The unique ID of the episode to get trace information for
        
    Returns:
        Detailed processing trace with steps and errors
    """
    # Access telemetry client from shared module
    from mcp_server.telemetry.shared import telemetry_client
    
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        result = await telemetry_client.run_query(EPISODE_HISTORY_QUERY, {"episode_id": episode_id})
        trace_data = format_episode_trace(result)
        return {"data": trace_data, "message": f"Successfully retrieved trace for episode {episode_id}"}
    except Exception as e:
        return {"error": f"Failed to retrieve episode trace: {str(e)}"}

# MCP tool for getting error patterns
async def get_error_patterns_tool() -> DiagnosticResponse | ErrorResponse:
    """Get patterns of errors across episodes.
    
    This tool analyzes all telemetry data to identify common error patterns
    across multiple episodes, helping to identify systematic issues.
    
    Returns:
        Summary of error patterns with counts of affected episodes
    """
    # Access telemetry client from shared module
    from mcp_server.telemetry.shared import telemetry_client
    
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        result = await telemetry_client.run_query(ERROR_PATTERNS_QUERY)
        return {"data": result, "message": "Successfully retrieved error patterns"}
    except Exception as e:
        return {"error": f"Failed to retrieve error patterns: {str(e)}"}

# MCP tool for getting episodes with a specific error
async def get_episodes_with_error_tool(error_type: str) -> DiagnosticResponse | ErrorResponse:
    """Get all episodes affected by a specific error type.
    
    This tool allows you to find all episodes that experienced a particular type of error,
    helping to understand the impact and scope of specific issues.
    
    Args:
        error_type: The type of error to search for (e.g., "DatabaseConnectionError")
        
    Returns:
        List of episodes affected by the specified error type
    """
    # Access telemetry client from shared module
    from mcp_server.telemetry.shared import telemetry_client
    
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        result = await telemetry_client.run_query(EPISODES_WITH_ERROR_TYPE_QUERY, {"error_type": error_type})
        return {"data": result, "message": f"Successfully retrieved episodes with error type: {error_type}"}
    except Exception as e:
        return {"error": f"Failed to retrieve episodes with error: {str(e)}"}

@router.get("/api/diagnostics/steps/{step_name}/failures")
async def get_step_failures(step_name: str, telemetry_client: TelemetryNeo4jClient = Depends(get_telemetry_client)):
    """Get episodes that failed in a specific processing step."""
    result = await telemetry_client.run_query(STEP_FAILURES_QUERY, {"step_name": step_name})
    return result

# MCP tool for getting overall processing statistics
async def get_telemetry_stats_tool() -> DiagnosticResponse | ErrorResponse:
    """Get overall episode processing statistics.
    
    This tool provides summary statistics about all episode processing activities,
    including success rates, failure counts, and average processing times.
    
    Returns:
        Summary statistics about episode processing
    """
    # Access telemetry client from shared module
    from mcp_server.telemetry.shared import telemetry_client
    
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        result = await telemetry_client.run_query(PROCESSING_STATS_QUERY)
        stats = result[0] if result else {"no_data": True}
        return {"data": stats, "message": "Successfully retrieved processing statistics"}
    except Exception as e:
        return {"error": f"Failed to retrieve processing statistics: {str(e)}"}

@router.get("/api/diagnostics/stats/step-timing")
async def get_step_timing(telemetry_client: TelemetryNeo4jClient = Depends(get_telemetry_client)):
    """Get processing time distribution by step."""
    result = await telemetry_client.run_query(STEP_TIMING_QUERY)
    return result

# MCP tool for getting recent errors
async def get_recent_errors_tool() -> DiagnosticResponse | ErrorResponse:
    """Get the most recent errors from episode processing.
    
    This tool returns the 20 most recent errors that occurred during episode processing,
    providing a quick view of recent issues.
    
    Returns:
        List of recent errors with associated episode information
    """
    # Access telemetry client from shared module
    from mcp_server.telemetry.shared import telemetry_client
    
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        result = await telemetry_client.run_query(RECENT_ERRORS_QUERY)
        return {"data": result, "message": "Successfully retrieved recent errors"}
    except Exception as e:
        return {"error": f"Failed to retrieve recent errors: {str(e)}"}
