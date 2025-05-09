# Implementation Plan: Non-Invasive Local File Logging System

## Overview

This plan outlines a comprehensive approach to replace the Neo4j-based telemetry system with a non-invasive local file logging system. The new system will maintain all the diagnostic capabilities of the current implementation while eliminating database mutations during logging operations.

## 1. Inventory of Affected Files

### Core Telemetry Files
- [ ] `/workspace/graphiti/graphiti_core/telemetry.py` - Primary telemetry implementation
- [ ] `/workspace/graphiti/graphiti_core/utils/neo4j_wrapper.py` - Logging driver implementation

### Files That Use Telemetry
- [ ] `/workspace/graphiti/mcp_server/graphiti_mcp_server.py` - Uses telemetry for episode tracking
- [ ] `/workspace/graphiti/graphiti_core/graphiti.py` - May reference telemetry for operations
- [ ] `/workspace/graphiti/graphiti_core/nodes.py` - Episode node operations that may use telemetry

### Configuration Files
- [ ] `/workspace/graphiti/tests/mcp_ingestion/logging_config.py` - Existing logging configuration

## 2. New Logging Architecture Design

### 2.1 Core Components

- [ ] **Structured Logger**: A wrapper around Python's standard logging that supports structured data
- [ ] **Episode Tracker**: A component that tracks episode processing status without Neo4j mutations
- [ ] **Timing Recorder**: A component that records timing information for processing stages
- [ ] **Log Formatter**: A JSON formatter for structured logs to enable easy parsing and analysis
- [ ] **Correlation ID Manager**: A utility to generate and track correlation IDs across operations

### 2.2 Architecture Diagram

```
┌─────────────────────┐     ┌─────────────────────┐
│  Graphiti Core      │     │  MCP Server         │
│  Operations         │     │  Operations         │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           ▼                           ▼
┌─────────────────────────────────────────────────┐
│               Telemetry Interface               │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │   Episode   │  │   Timing    │  │Correlation│ │
│  │   Tracker   │  │  Recorder   │  │ID Manager │ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬────┘ │
└─────────┼───────────────┼───────────────┼───────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────────────────────────────────────┐
│            Structured Logger                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ JSON        │  │ Console     │  │ Rotating │ │
│  │ Formatter   │  │ Handler     │  │ File     │ │
│  └─────────────┘  └─────────────┘  └──────────┘ │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                  Log Files                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ episode.log │  │ timing.log  │  │ error.log│ │
│  └─────────────┘  └─────────────┘  └──────────┘ │
└─────────────────────────────────────────────────┘
```

## 3. Implementation Steps

### 3.1 Create Enhanced Logging Configuration

- [ ] Create a new file: `/workspace/graphiti/graphiti_core/utils/enhanced_logging.py`

```python
"""
Enhanced logging configuration for Graphiti.

This module provides structured logging capabilities with JSON formatting,
correlation ID tracking, and other features needed for comprehensive telemetry.
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

# Configure log directory
LOG_DIR = os.environ.get("GRAPHITI_LOG_DIR", "/workspace/graphiti/logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
EPISODE_LOG_FILE = os.path.join(LOG_DIR, "episode.log")
TIMING_LOG_FILE = os.path.join(LOG_DIR, "timing.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")
GENERAL_LOG_FILE = os.path.join(LOG_DIR, "graphiti.log")

# Log levels
DEFAULT_LOG_LEVEL = logging.INFO

class StructuredLogRecord(logging.LogRecord):
    """Extended LogRecord that supports structured data."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correlation_id = None
        self.structured_data = {}


class StructuredLogger(logging.Logger):
    """Logger that supports structured data and correlation IDs."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Create a LogRecord with support for structured data."""
        record = StructuredLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra:
            for key, value in extra.items():
                if key == "structured_data" and isinstance(value, dict):
                    record.structured_data = value
                elif key == "correlation_id":
                    record.correlation_id = value
                elif key != "message":
                    setattr(record, key, value)
        return record
    
    def structured_log(self, level, msg, correlation_id=None, **structured_data):
        """Log a message with structured data."""
        if not self.isEnabledFor(level):
            return
            
        extra = {
            "correlation_id": correlation_id,
            "structured_data": structured_data
        }
        self._log(level, msg, (), extra=extra)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing."""
    
    def format(self, record):
        """Format the record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_data["correlation_id"] = record.correlation_id
            
        # Add structured data if available
        if hasattr(record, "structured_data") and record.structured_data:
            log_data["data"] = record.structured_data
            
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)


def get_logger(name, log_file=None):
    """Get a structured logger with the specified name."""
    # Register the StructuredLogger class
    logging.setLoggerClass(StructuredLogger)
    
    # Get the logger
    logger = logging.getLogger(name)
    logger.setLevel(DEFAULT_LOG_LEVEL)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    return logger


# Create specialized loggers
episode_logger = get_logger("graphiti.episode", EPISODE_LOG_FILE)
timing_logger = get_logger("graphiti.timing", TIMING_LOG_FILE)
error_logger = get_logger("graphiti.error", ERROR_LOG_FILE)
general_logger = get_logger("graphiti", GENERAL_LOG_FILE)


def generate_correlation_id():
    """Generate a unique correlation ID."""
    return f"corr-{uuid.uuid4().hex}"


class CorrelationIdContext:
    """Context manager for correlation IDs."""
    
    def __init__(self, correlation_id=None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_correlation_id = None
        
    def __enter__(self):
        self.previous_correlation_id = getattr(CorrelationIdContext, "_current_id", None)
        CorrelationIdContext._current_id = self.correlation_id
        return self.correlation_id
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        CorrelationIdContext._current_id = self.previous_correlation_id
        
    @staticmethod
    def get_current():
        """Get the current correlation ID."""
        return getattr(CorrelationIdContext, "_current_id", None)


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name, correlation_id=None, **context_data):
        self.operation_name = operation_name
        self.correlation_id = correlation_id or CorrelationIdContext.get_current()
        self.context_data = context_data
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        # Prepare timing data
        timing_data = {
            "operation": self.operation_name,
            "duration_ms": duration_ms,
            **self.context_data
        }
        
        # Log the timing
        if exc_type:
            # Operation failed
            timing_data["status"] = "failed"
            timing_data["error"] = str(exc_val)
            timing_logger.structured_log(
                logging.ERROR,
                f"{self.operation_name} failed after {duration_ms:.2f} ms",
                correlation_id=self.correlation_id,
                **timing_data
            )
        else:
            # Operation succeeded
            timing_data["status"] = "success"
            timing_logger.structured_log(
                logging.INFO,
                f"{self.operation_name} completed in {duration_ms:.2f} ms",
                correlation_id=self.correlation_id,
                **timing_data
            )
```

### 3.2 Create New Telemetry Implementation

- [ ] Create a new file: `/workspace/graphiti/graphiti_core/file_telemetry.py`

```python
"""
File-based telemetry implementation for Graphiti.

This module replaces the Neo4j-based telemetry with a file-based implementation
that provides the same functionality without mutating the graph.
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from graphiti_core.utils.enhanced_logging import (
    CorrelationIdContext,
    TimingContext,
    episode_logger,
    error_logger,
    generate_correlation_id,
    timing_logger
)

# Re-export the enums from the original telemetry module
class EpisodeStatus(str, Enum):
    """Status of an episode in the processing pipeline."""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    """Stages of episode processing."""
    RECEIVED = "received"
    QUEUED = "queued"
    STARTED = "started"
    NODE_EXTRACTION = "node_extraction"
    EDGE_EXTRACTION = "edge_extraction"
    NODE_RESOLUTION = "node_resolution"
    EDGE_RESOLUTION = "edge_resolution"
    DATABASE_UPDATE = "database_update"
    COMMUNITY_UPDATE = "community_update"
    COMPLETED = "completed"
    FAILED = "failed"


class FileTelemetry:
    """File-based telemetry implementation."""
    
    def __init__(self, driver=None):
        """
        Initialize the telemetry system.
        
        The driver parameter is accepted for backward compatibility
        but is not used in this implementation.
        """
        # Store correlation IDs for episodes
        self.correlation_ids = {}
    
    def get_correlation_id(self, episode_uuid: str) -> str:
        """Get or create a correlation ID for an episode."""
        if episode_uuid not in self.correlation_ids:
            self.correlation_ids[episode_uuid] = generate_correlation_id()
        return self.correlation_ids[episode_uuid]
    
    async def track_episode_status(
        self,
        episode_uuid: str,
        status: EpisodeStatus,
        stage: Optional[ProcessingStage] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track the status of an episode in the processing pipeline.
        
        Args:
            episode_uuid: UUID of the episode
            status: Current status of the episode
            stage: Current processing stage (if applicable)
            error_message: Error message (if applicable)
            metadata: Additional metadata to store
        """
        correlation_id = self.get_correlation_id(episode_uuid)
        
        # Prepare log data
        log_data = {
            "episode_uuid": episode_uuid,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if stage:
            log_data["stage"] = stage.value
            
        if error_message:
            log_data["error_message"] = error_message
            
        if metadata:
            # No need to serialize metadata as JSON strings
            log_data["metadata"] = metadata
        
        # Log the status change
        if status == EpisodeStatus.FAILED:
            episode_logger.structured_log(
                logging.ERROR,
                f"Episode {episode_uuid} failed at stage {stage.value if stage else 'unknown'}: {error_message}",
                correlation_id=correlation_id,
                **log_data
            )
            
            # Also log to the error log
            error_logger.structured_log(
                logging.ERROR,
                f"Episode {episode_uuid} failed at stage {stage.value if stage else 'unknown'}: {error_message}",
                correlation_id=correlation_id,
                **log_data
            )
        else:
            episode_logger.structured_log(
                logging.INFO,
                f"Episode {episode_uuid} status: {status.value}" + 
                (f", stage: {stage.value}" if stage else ""),
                correlation_id=correlation_id,
                **log_data
            )
    
    async def track_processing_time(
        self,
        episode_uuid: str,
        stage: ProcessingStage,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track the processing time for a stage of episode processing.
        
        Args:
            episode_uuid: UUID of the episode
            stage: Processing stage
            duration_ms: Duration in milliseconds
            metadata: Additional metadata to store
        """
        correlation_id = self.get_correlation_id(episode_uuid)
        
        # Prepare log data
        log_data = {
            "episode_uuid": episode_uuid,
            "stage": stage.value,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if metadata:
            # No need to serialize metadata as JSON strings
            log_data["metadata"] = metadata
        
        # Log the timing
        timing_logger.structured_log(
            logging.INFO,
            f"Episode {episode_uuid} stage {stage.value} completed in {duration_ms:.2f} ms",
            correlation_id=correlation_id,
            **log_data
        )
    
    async def get_queue_status(self, group_id: str) -> Dict[str, Any]:
        """
        Get the status of the processing queue for a group.
        
        This is a stub implementation that returns empty data,
        as queue status is not tracked in the file-based implementation.
        
        Args:
            group_id: Group ID to get queue status for
            
        Returns:
            Dictionary with queue status information
        """
        # This would typically query Neo4j for queue status
        # In the file-based implementation, we just return empty data
        return {
            "group_id": group_id,
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
    
    def timing_context(
        self,
        episode_uuid: str,
        stage: ProcessingStage,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimingContext:
        """
        Create a context manager for timing a stage of episode processing.
        
        Args:
            episode_uuid: UUID of the episode
            stage: Processing stage
            metadata: Additional metadata to store
            
        Returns:
            A context manager that will track the timing of the operation
        """
        correlation_id = self.get_correlation_id(episode_uuid)
        
        context_data = {
            "episode_uuid": episode_uuid,
            "stage": stage.value,
        }
        
        if metadata:
            context_data["metadata"] = metadata
            
        return TimingContext(
            operation_name=f"episode_{stage.value}",
            correlation_id=correlation_id,
            **context_data
        )


# Singleton instance for backward compatibility
_telemetry_instance = None

def get_telemetry(driver=None):
    """
    Get the telemetry instance.
    
    The driver parameter is accepted for backward compatibility
    but is not used in this implementation.
    
    Args:
        driver: Neo4j driver (ignored in this implementation)
        
    Returns:
        The telemetry instance
    """
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = FileTelemetry(driver)
    return _telemetry_instance
```

### 3.3 Update MCP Server to Use File Telemetry

- [ ] Modify `/workspace/graphiti/mcp_server/graphiti_mcp_server.py`

```python
# Replace import
# from graphiti_core.telemetry import get_telemetry, EpisodeStatus, ProcessingStage
from graphiti_core.file_telemetry import get_telemetry, EpisodeStatus, ProcessingStage
```

### 3.4 Create Compatibility Layer for Transition Period

- [ ] Create a new file: `/workspace/graphiti/graphiti_core/telemetry_compat.py`

```python
"""
Compatibility layer for transitioning from Neo4j-based telemetry to file-based telemetry.

This module provides a compatibility layer that allows code to continue using
the original telemetry module while actually using the new file-based implementation.
"""

import warnings
from typing import Any, Dict, Optional

from graphiti_core.file_telemetry import (
    EpisodeStatus,
    FileTelemetry,
    ProcessingStage,
    get_telemetry as get_file_telemetry
)

# Issue a deprecation warning
warnings.warn(
    "The Neo4j-based telemetry module is deprecated and will be removed in a future version. "
    "Use graphiti_core.file_telemetry instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export the enums
__all__ = ["EpisodeStatus", "ProcessingStage", "Telemetry", "get_telemetry"]


class Telemetry(FileTelemetry):
    """
    Compatibility wrapper for the FileTelemetry class.
    
    This class inherits from FileTelemetry but provides the same interface
    as the original Neo4j-based Telemetry class.
    """
    
    def __init__(self, driver=None):
        """Initialize with the same signature as the original."""
        super().__init__(driver)
        
        if driver is not None:
            warnings.warn(
                "The driver parameter is ignored in the file-based telemetry implementation.",
                DeprecationWarning,
                stacklevel=2
            )


def get_telemetry(driver=None):
    """
    Get the telemetry instance with the same signature as the original.
    
    Args:
        driver: Neo4j driver (ignored in this implementation)
        
    Returns:
        The telemetry instance
    """
    return get_file_telemetry(driver)
```

### 3.5 Update Original Telemetry Module to Use Compatibility Layer

- [ ] Modify `/workspace/graphiti/graphiti_core/telemetry.py`

```python
"""
Telemetry module for Graphiti system.

This module has been replaced by the file_telemetry module.
It now imports from telemetry_compat to maintain backward compatibility.
"""

# Import everything from the compatibility layer
from graphiti_core.telemetry_compat import (
    EpisodeStatus,
    ProcessingStage,
    Telemetry,
    get_telemetry
)

# Re-export everything
__all__ = ["EpisodeStatus", "ProcessingStage", "Telemetry", "get_telemetry"]
```

### 3.6 Create Log Analysis Utilities

- [ ] Create a new file: `/workspace/graphiti/graphiti_core/utils/log_analysis.py`

```python
"""
Utilities for analyzing logs.

This module provides utilities for analyzing the logs produced by the
file-based telemetry implementation.
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

# Log file paths
LOG_DIR = os.environ.get("GRAPHITI_LOG_DIR", "/workspace/graphiti/logs")
EPISODE_LOG_FILE = os.path.join(LOG_DIR, "episode.log")
TIMING_LOG_FILE = os.path.join(LOG_DIR, "timing.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")


def parse_log_file(log_file: str) -> List[Dict]:
    """
    Parse a log file into a list of log entries.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        List of log entries as dictionaries
    """
    entries = []
    
    with open(log_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except json.JSONDecodeError:
                # Skip invalid lines
                continue
                
    return entries


def get_episode_status_history(episode_uuid: str) -> List[Dict]:
    """
    Get the status history for an episode.
    
    Args:
        episode_uuid: UUID of the episode
        
    Returns:
        List of status changes in chronological order
    """
    entries = parse_log_file(EPISODE_LOG_FILE)
    
    # Filter entries for the specified episode
    episode_entries = [
        entry for entry in entries
        if entry.get("data", {}).get("episode_uuid") == episode_uuid
    ]
    
    # Sort by timestamp
    episode_entries.sort(key=lambda e: e.get("timestamp", ""))
    
    return episode_entries


def get_episode_timing_data(episode_uuid: str) -> List[Dict]:
    """
    Get the timing data for an episode.
    
    Args:
        episode_uuid: UUID of the episode
        
    Returns:
        List of timing entries in chronological order
    """
    entries = parse_log_file(TIMING_LOG_FILE)
    
    # Filter entries for the specified episode
    episode_entries = [
        entry for entry in entries
        if entry.get("data", {}).get("episode_uuid") == episode_uuid
    ]
    
    # Sort by timestamp
    episode_entries.sort(key=lambda e: e.get("timestamp", ""))
    
    return episode_entries


def get_episode_errors(episode_uuid: str) -> List[Dict]:
    """
    Get the errors for an episode.
    
    Args:
        episode_uuid: UUID of the episode
        
    Returns:
        List of error entries in chronological order
    """
    entries = parse_log_file(ERROR_LOG_FILE)
    
    # Filter entries for the specified episode
    episode_entries = [
        entry for entry in entries
        if entry.get("data", {}).get("episode_uuid") == episode_uuid
    ]
    
    # Sort by timestamp
    episode_entries.sort(key=lambda e: e.get("timestamp", ""))
    
    return episode_entries


def get_episodes_by_status(status: str, time_range: Optional[Tuple[datetime, datetime]] = None) -> List[str]:
    """
    Get episodes with the specified status.
    
    Args:
        status: Status to filter by
        time_range: Optional time range to filter by (start, end)
        
    Returns:
        List of episode UUIDs
    """
    entries = parse_log_file(EPISODE_LOG_FILE)
    
    # Filter entries by status
    status_entries = [
        entry for entry in entries
        if entry.get("data", {}).get("status") == status
    ]
    
    # Filter by time range if specified
    if time_range:
        start, end = time_range
        status_entries = [
            entry for entry in status_entries
            if start <= datetime.fromisoformat(entry.get("timestamp", "")) <= end
        ]
    
    # Get the latest status for each episode
    episode_status = {}
    for entry in status_entries:
        episode_uuid = entry.get("data", {}).get("episode_uuid")
        timestamp = entry.get("timestamp", "")
        
        if episode_uuid not in episode_status or timestamp > episode_status[episode_uuid][0]:
            episode_status[episode_uuid] = (timestamp, entry.get("data", {}).get("status"))
    
    # Return episodes with the specified status
    return [
        episode_uuid for episode_uuid, (_, current_status) in episode_status.items()
        if current_status == status
    ]


def get_processing_statistics(time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict:
    """
    Get processing statistics.
    
    Args:
        time_range: Optional time range to filter by (start, end)
        
    Returns:
        Dictionary with processing statistics
    """
    timing_entries = parse_log_file(TIMING_LOG_FILE)
    
    # Filter by time range if specified
    if time_range:
        start, end = time_range
        timing_entries = [
            entry for entry in timing_entries
            if start <= datetime.fromisoformat(entry.get("timestamp", "")) <= end
        ]
    
    # Calculate statistics
    stage_durations = defaultdict(list)
    for entry in timing_entries:
        stage = entry.get("data", {}).get("stage")
        duration_ms = entry.get("data", {}).get("duration_ms")
        
        if stage and duration_ms:
            stage_durations[stage].append(duration_ms)
    
    # Calculate average, min, max for each stage
    statistics = {}
    for stage, durations in stage_durations.items():
        statistics[stage] = {
            "count": len(durations),
            "average_ms": sum(durations) / len(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
            "max_ms": max(durations) if durations else 0,
        }
    
    return statistics
```

## 4. Data Structure for Logs

### 4.1 Episode Status Log Entry

```json
{
  "timestamp": "2023-05-09T12:34:56.789Z",
  "level": "INFO",
  "logger": "graphiti.episode",
  "message": "Episode abc123 status: processing, stage: node_extraction",
  "module": "file_telemetry",
  "function": "track_episode_status",
  "line": 123,
  "correlation_id": "corr-abcdef123456",
  "data": {
    "episode_uuid": "abc123",
    "status": "processing",
    "stage": "node_extraction",
    "timestamp": "2023-05-09T12:34:56.789Z",
    "metadata": {
      "node_count": 5,
      "source_type": "text"
    }
  }
}
```

### 4.2 Timing Log Entry

```json
{
  "timestamp": "2023-05-09T12:35:01.234Z",
  "level": "INFO",
  "logger": "graphiti.timing",
  "message": "Episode abc123 stage node_extraction completed in 123.45 ms",
  "module": "file_telemetry",
  "function": "track_processing_time",
  "line": 456,
  "correlation_id": "corr-abcdef123456",
  "data": {
    "episode_uuid": "abc123",
    "stage": "node_extraction",
    "duration_ms": 123.45,
    "timestamp": "2023-05-09T12:35:01.234Z",
    "metadata": {
      "node_count": 5,
      "memory_usage_mb": 256
    }
  }
}
```

### 4.3 Error Log Entry

```json
{
  "timestamp": "2023-05-09T12:35:10.567Z",
  "level": "ERROR",
  "logger": "graphiti.error",
  "message": "Episode abc123 failed at stage edge_extraction: Invalid relationship type",
  "module": "file_telemetry",
  "function": "track_episode_status",
  "line": 789,
  "correlation_id": "corr-abcdef123456",
  "data": {
    "episode_uuid": "abc123",
    "status": "failed",
    "stage": "edge_extraction",
    "error_message": "Invalid relationship type",
    "timestamp": "2023-05-09T12:35:10.567Z",
    "metadata": {
      "relationship_type": "INVALID_TYPE"
    }
  },
  "exception": {
    "type": "ValueError",
    "message": "Invalid relationship type: INVALID_TYPE",
    "traceback": "..."
  }
}
```

## 5. Backward Compatibility Considerations

### 5.1 Compatibility Layer

- [ ] The `telemetry_compat.py` module provides a compatibility layer that allows existing code to continue using the original telemetry module.
- [ ] The `get_telemetry` function maintains the same signature, accepting a driver parameter that is ignored.
- [ ] The `Telemetry` class inherits from `FileTelemetry` but provides the same interface as the original.
- [ ] Deprecation warnings are issued to encourage migration to the new API.

### 5.2 Method Signatures

- [ ] All methods in the `FileTelemetry` class have the same signatures as their counterparts in the original `Telemetry` class.
- [ ] The `track_episode_status` and `track_processing_time` methods are async to match the original.
- [ ] The `get_correlation_id` method works the same way as the original.

### 5.3 Enum Compatibility

- [ ] The `EpisodeStatus` and `ProcessingStage` enums are identical to the original.
- [ ] They are re-exported from the compatibility layer to maintain backward compatibility.

## 6. Testing Approach

### 6.1 Unit Tests

- [ ] Create unit tests for the enhanced logging module:
  - [ ] Test JSON formatting
  - [ ] Test correlation ID tracking
  - [ ] Test structured logging

- [ ] Create unit tests for the file telemetry module:
  - [ ] Test episode status tracking
  - [ ] Test processing time tracking
  - [ ] Test correlation ID generation

### 6.2 Integration Tests

- [ ] Create integration tests that verify the telemetry system works with the MCP server:
  - [ ] Test episode creation and tracking
  - [ ] Test processing stage timing
  - [ ] Test error handling and logging

### 6.3 Log Analysis Tests

- [ ] Create tests for the log analysis utilities:
  - [ ] Test parsing log files
  - [ ] Test retrieving episode status history
  - [ ] Test calculating processing statistics

### 6.4 Manual Testing

- [ ] Manually verify that logs are created in the expected format
- [ ] Verify that all telemetry data is captured correctly
- [ ] Verify that no Neo4j mutations occur during logging

## 7. Implementation Phases

### Phase 1: Core Logging Infrastructure

- [ ] Implement enhanced_logging.py
- [ ] Implement file_telemetry.py
- [ ] Create basic unit tests

### Phase 2: Compatibility Layer

- [ ] Implement telemetry_compat.py
- [ ] Update telemetry.py to use the compatibility layer
- [ ] Test backward compatibility

### Phase 3: MCP Server Integration

- [ ] Update MCP server to use file telemetry
- [ ] Test end-to-end functionality
- [ ] Verify no Neo4j mutations

### Phase 4: Log Analysis Tools

- [ ] Implement log_analysis.py
- [ ] Create documentation for log analysis
- [ ] Test log analysis utilities

## 8. Bug Resolution

### Bug 01: Metadata Serialization Failure

This plan resolves Bug 01 by:
- [ ] Eliminating the need to serialize metadata as JSON strings
- [ ] Using a structured logging approach that handles complex data types natively
- [ ] Storing metadata directly in log files without Neo4j property constraints

### Bug 03: Telemetry Driver Session Error

This plan resolves Bug 03 by:
- [ ] Removing the dependency on the Neo4j driver for telemetry
- [ ] Eliminating the LoggingAsyncDriver session method issue
- [ ] Using file-based logging that doesn't require database sessions

### Other Logging-Related Bugs

This plan also addresses:
- [ ] Silent relationship type failures (Bug 04) by removing the dependency on Neo4j relationship types for telemetry
- [ ] Queue worker monitoring deficiency (Bug 05) by providing better logging of worker status
- [ ] Error propagation issues (Bug 09) by ensuring all errors are properly logged with context

## 9. Conclusion

This implementation plan provides a comprehensive approach to replacing the Neo4j-based telemetry system with a non-invasive file logging system. The new system maintains all the diagnostic capabilities of the current implementation while eliminating database mutations during logging operations.

The plan includes:
- [ ] A structured logging system that supports correlation IDs and complex data
- [ ] A file-based telemetry implementation that matches the original API
- [ ] A compatibility layer for backward compatibility
- [ ] Log analysis utilities for extracting insights from logs
- [ ] A phased implementation approach
- [ ] Comprehensive testing to ensure correctness

By following this plan, we can resolve the identified bugs and improve the overall reliability and maintainability of the system.