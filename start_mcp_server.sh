#!/bin/bash

# Important: Any text output to stdout will break JSON communication with Claude
# So we redirect all our informational output to stderr instead

# Set up paths
PROJECT_DIR="/Users/robhitchens/Documents/projects/peabawdy/graphiti"
MCP_DIR="$PROJECT_DIR/mcp_server"
VENV_DIR="$PROJECT_DIR/.venv"
UV_PATH="/Users/robhitchens/.local/bin/uv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..." >&2
  "$UV_PATH" venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies from requirements.txt..." >&2
"$UV_PATH" pip install -r "$MCP_DIR/requirements.txt" >&2

# Make sure python-dotenv is installed
echo "Installing python-dotenv specifically..." >&2
"$UV_PATH" pip install python-dotenv >&2

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run the MCP server - no echo here to avoid breaking JSON
python3 "$MCP_DIR/graphiti_mcp_server.py" --transport stdio
