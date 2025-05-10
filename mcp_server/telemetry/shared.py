"""
Shared telemetry client module to avoid circular dependencies.
"""

# Global telemetry client that will be set by the main server
# and accessed by diagnostic tools
telemetry_client = None
