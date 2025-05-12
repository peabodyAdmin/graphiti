#!/usr/bin/env python3
"""
Graphiti MCP Server - Exposes Graphiti functionality through the Model Context Protocol (MCP)
"""

import argparse
import asyncio
import logging
import os
import re
import sys
import traceback
from pathlib import Path
import uuid

# Add the parent directory to Python's module path so imports like 'mcp_server.xyz' work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypedDict, cast
from services.queue_inspection import get_queue_stats, get_job_by_index

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.edges import EntityEdge
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_NODE_DISTANCE,
    NODE_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from telemetry.config import TelemetryConfig
from telemetry.initialization import initialize_telemetry
from telemetry.shared import telemetry_client as shared_telemetry_client

# Load environment variables from the project root .env file
project_root = Path(__file__).parent.parent.absolute()
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

DEFAULT_LLM_MODEL = 'gpt-4.1-mini'
DEFAULT_EMBEDDER_MODEL = 'text-embedding-3-small'


class Requirement(BaseModel):
    """A Requirement represents a specific need, feature, or functionality that a product or service must fulfill.

    Always ensure an edge is created between the requirement and the project it belongs to, and clearly indicate on the
    edge that the requirement is a requirement.

    Instructions for identifying and extracting requirements:
    1. Look for explicit statements of needs or necessities ("We need X", "X is required", "X must have Y")
    2. Identify functional specifications that describe what the system should do
    3. Pay attention to non-functional requirements like performance, security, or usability criteria
    4. Extract constraints or limitations that must be adhered to
    5. Focus on clear, specific, and measurable requirements rather than vague wishes
    6. Capture the priority or importance if mentioned ("critical", "high priority", etc.)
    7. Include any dependencies between requirements when explicitly stated
    8. Preserve the original intent and scope of the requirement
    9. Categorize requirements appropriately based on their domain or function
    """

    project_name: str = Field(
        ...,
        description='The name of the project to which the requirement belongs.',
    )
    description: str = Field(
        ...,
        description='Description of the requirement. Only use information mentioned in the context to write this description.',
    )


class Preference(BaseModel):
    """A Preference represents a user's expressed like, dislike, or preference for something.

    Instructions for identifying and extracting preferences:
    1. Look for explicit statements of preference such as "I like/love/enjoy/prefer X" or "I don't like/hate/dislike X"
    2. Pay attention to comparative statements ("I prefer X over Y")
    3. Consider the emotional tone when users mention certain topics
    4. Extract only preferences that are clearly expressed, not assumptions
    5. Categorize the preference appropriately based on its domain (food, music, brands, etc.)
    6. Include relevant qualifiers (e.g., "likes spicy food" rather than just "likes food")
    7. Only extract preferences directly stated by the user, not preferences of others they mention
    8. Provide a concise but specific description that captures the nature of the preference
    """

    category: str = Field(
        ...,
        description="The category of the preference. (e.g., 'Brands', 'Food', 'Music')",
    )
    description: str = Field(
        ...,
        description='Brief description of the preference. Only use information mentioned in the context to write this description.',
    )


class Procedure(BaseModel):
    """A Procedure informing the agent what actions to take or how to perform in certain scenarios. Procedures are typically composed of several steps.

    Instructions for identifying and extracting procedures:
    1. Look for sequential instructions or steps ("First do X, then do Y")
    2. Identify explicit directives or commands ("Always do X when Y happens")
    3. Pay attention to conditional statements ("If X occurs, then do Y")
    4. Extract procedures that have clear beginning and end points
    5. Focus on actionable instructions rather than general information
    6. Preserve the original sequence and dependencies between steps
    7. Include any specified conditions or triggers for the procedure
    8. Capture any stated purpose or goal of the procedure
    9. Summarize complex procedures while maintaining critical details
    """

    description: str = Field(
        ...,
        description='Brief description of the procedure. Only use information mentioned in the context to write this description.',
    )


ENTITY_TYPES: dict[str, BaseModel] = {
    'Requirement': Requirement,  # type: ignore
    'Preference': Preference,  # type: ignore
    'Procedure': Procedure,  # type: ignore
}


# Type definitions for API responses
class ErrorResponse(TypedDict):
    error: str


class SuccessResponse(TypedDict):
    message: str


class NodeResult(TypedDict):
    uuid: str
    name: str
    summary: str
    labels: list[str]
    group_id: str
    created_at: str
    attributes: dict[str, Any]


class NodeSearchResponse(TypedDict):
    message: str
    nodes: list[NodeResult]


class FactSearchResponse(TypedDict):
    message: str
    facts: list[dict[str, Any]]


class EpisodeSearchResponse(TypedDict):
    message: str
    episodes: list[dict[str, Any]]


class StatusResponse(TypedDict):
    status: str
    message: str


class TelemetryResponse(TypedDict):
    data: Any
    message: str


def create_azure_credential_token_provider() -> Callable[[], str]:
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, 'https://cognitiveservices.azure.com/.default'
    )
    return token_provider


# Server configuration classes
# The configuration system has a hierarchy:
# - GraphitiConfig is the top-level configuration
#   - LLMConfig handles all OpenAI/LLM related settings
#   - EmbedderConfig manages embedding settings
#   - Neo4jConfig manages database connection details
#   - Various other settings like group_id and feature flags
# Configuration values are loaded from:
# 1. Default values in the class definitions
# 2. Environment variables (loaded via load_dotenv())
# 3. Command line arguments (which override environment variables)
class GraphitiLLMConfig(BaseModel):
    """Configuration for the LLM client.

    Centralizes all LLM-specific configuration parameters including API keys and model selection.
    """

    api_key: str | None = None
    model: str = DEFAULT_LLM_MODEL
    temperature: float = 0.0
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_use_managed_identity: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiLLMConfig':
        """Create LLM configuration from environment variables."""
        # Get model from environment, or use default if not set or empty
        model_env = os.environ.get('MODEL_NAME', '')
        model = model_env if model_env.strip() else DEFAULT_LLM_MODEL

        azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', None)
        azure_openai_api_version = os.environ.get('AZURE_OPENAI_API_VERSION', None)
        azure_openai_deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', None)
        azure_openai_use_managed_identity = (
            os.environ.get('AZURE_OPENAI_USE_MANAGED_IDENTITY', 'false').lower() == 'true'
        )

        if azure_openai_endpoint is None:
            # Setup for OpenAI API
            # Log if empty model was provided
            if model_env == '':
                logger.debug(
                    f'MODEL_NAME environment variable not set, using default: {DEFAULT_LLM_MODEL}'
                )
            elif not model_env.strip():
                logger.warning(
                    f'Empty MODEL_NAME environment variable, using default: {DEFAULT_LLM_MODEL}'
                )

            return cls(
                api_key=os.environ.get('OPENAI_API_KEY'),
                model=model,
                temperature=float(os.environ.get('LLM_TEMPERATURE', '0.0')),
            )
        else:
            # Setup for Azure OpenAI API
            # Log if empty deployment name was provided
            if azure_openai_deployment_name is None:
                logger.error('AZURE_OPENAI_DEPLOYMENT_NAME environment variable not set')

                raise ValueError('AZURE_OPENAI_DEPLOYMENT_NAME environment variable not set')
            if not azure_openai_use_managed_identity:
                # api key
                api_key = os.environ.get('OPENAI_API_KEY', None)
            else:
                # Managed identity
                api_key = None

            return cls(
                azure_openai_use_managed_identity=azure_openai_use_managed_identity,
                azure_openai_endpoint=azure_openai_endpoint,
                api_key=api_key,
                azure_openai_api_version=azure_openai_api_version,
                azure_openai_deployment_name=azure_openai_deployment_name,
                temperature=float(os.environ.get('LLM_TEMPERATURE', '0.0')),
            )

    @classmethod
    def from_cli_and_env(cls, args: argparse.Namespace) -> 'GraphitiLLMConfig':
        """Create LLM configuration from CLI arguments, falling back to environment variables."""
        # Start with environment-based config
        config = cls.from_env()

        # CLI arguments override environment variables when provided
        if hasattr(args, 'model') and args.model:
            # Only use CLI model if it's not empty
            if args.model.strip():
                config.model = args.model
            else:
                # Log that empty model was provided and default is used
                logger.warning(f'Empty model name provided, using default: {DEFAULT_LLM_MODEL}')

        if hasattr(args, 'temperature') and args.temperature is not None:
            config.temperature = args.temperature

        return config

    def create_client(self) -> LLMClient | None:
        """Create an LLM client based on this configuration.

        Returns:
            LLMClient instance if able, None otherwise
        """

        if self.azure_openai_endpoint is not None:
            # Azure OpenAI API setup
            if self.azure_openai_use_managed_identity:
                # Use managed identity for authentication
                token_provider = create_azure_credential_token_provider()
                return AsyncAzureOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    azure_deployment=self.azure_openai_deployment_name,
                    api_version=self.azure_openai_api_version,
                    azure_ad_token_provider=token_provider,
                )
            elif self.api_key:
                # Use API key for authentication
                return AsyncAzureOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    azure_deployment=self.azure_openai_deployment_name,
                    api_version=self.azure_openai_api_version,
                    api_key=self.api_key,
                )
            else:
                logger.error('OPENAI_API_KEY must be set when using Azure OpenAI API')
                return None

        if not self.api_key:
            return None

        llm_client_config = LLMConfig(api_key=self.api_key, model=self.model)

        # Set temperature
        llm_client_config.temperature = self.temperature

        return OpenAIClient(config=llm_client_config)

    def create_cross_encoder_client(self) -> CrossEncoderClient | None:
        """Create a cross-encoder client based on this configuration."""
        if self.azure_openai_endpoint is not None:
            client = self.create_client()
            return OpenAIRerankerClient(client=client)
        else:
            llm_client_config = LLMConfig(api_key=self.api_key, model=self.model)
            return OpenAIRerankerClient(config=llm_client_config)


class GraphitiEmbedderConfig(BaseModel):
    """Configuration for the embedder client.

    Centralizes all embedding-related configuration parameters.
    """

    model: str = DEFAULT_EMBEDDER_MODEL
    api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_use_managed_identity: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiEmbedderConfig':
        """Create embedder configuration from environment variables."""

        # Get model from environment, or use default if not set or empty
        model_env = os.environ.get('EMBEDDER_MODEL_NAME', '')
        model = model_env if model_env.strip() else DEFAULT_EMBEDDER_MODEL

        azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', None)
        azure_openai_api_version = os.environ.get('AZURE_OPENAI_EMBEDDING_API_VERSION', None)
        azure_openai_deployment_name = os.environ.get(
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', None
        )
        azure_openai_use_managed_identity = (
            os.environ.get('AZURE_OPENAI_USE_MANAGED_IDENTITY', 'false').lower() == 'true'
        )
        if azure_openai_endpoint is not None:
            # Setup for Azure OpenAI API
            # Log if empty deployment name was provided
            azure_openai_deployment_name = os.environ.get(
                'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', None
            )
            if azure_openai_deployment_name is None:
                logger.error('AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME environment variable not set')

                raise ValueError(
                    'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME environment variable not set'
                )

            if not azure_openai_use_managed_identity:
                # api key
                api_key = os.environ.get('OPENAI_API_KEY', None)
            else:
                # Managed identity
                api_key = None

            return cls(
                azure_openai_use_managed_identity=azure_openai_use_managed_identity,
                azure_openai_endpoint=azure_openai_endpoint,
                api_key=api_key,
                azure_openai_api_version=azure_openai_api_version,
                azure_openai_deployment_name=azure_openai_deployment_name,
            )
        else:
            return cls(
                model=model,
                api_key=os.environ.get('OPENAI_API_KEY'),
            )

    def create_client(self) -> EmbedderClient | None:
        if self.azure_openai_endpoint is not None:
            # Azure OpenAI API setup
            if self.azure_openai_use_managed_identity:
                # Use managed identity for authentication
                token_provider = create_azure_credential_token_provider()
                return AsyncAzureOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    azure_deployment=self.azure_openai_deployment_name,
                    api_version=self.azure_openai_api_version,
                    azure_ad_token_provider=token_provider,
                )
            elif self.api_key:
                # Use API key for authentication
                return AsyncAzureOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    azure_deployment=self.azure_openai_deployment_name,
                    api_version=self.azure_openai_api_version,
                    api_key=self.api_key,
                )
            else:
                logger.error('OPENAI_API_KEY must be set when using Azure OpenAI API')
                return None
        else:
            # OpenAI API setup
            if not self.api_key:
                return None

            embedder_config = OpenAIEmbedderConfig(api_key=self.api_key, model=self.model)

            return OpenAIEmbedder(config=embedder_config)


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j database connection."""

    uri: str = 'bolt://localhost:7687'
    user: str = 'neo4j'
    password: str = 'password'

    @classmethod
    def from_env(cls) -> 'Neo4jConfig':
        """Create Neo4j configuration from environment variables."""
        return cls(
            uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.environ.get('NEO4J_USER', 'neo4j'),
            password=os.environ.get('NEO4J_PASSWORD', 'password'),
        )


class GraphitiConfig(BaseModel):
    """Configuration for Graphiti client.

    Centralizes all configuration parameters for the Graphiti client.
    """

    llm: GraphitiLLMConfig = Field(default_factory=GraphitiLLMConfig)
    embedder: GraphitiEmbedderConfig = Field(default_factory=GraphitiEmbedderConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    group_id: str | None = None
    use_custom_entities: bool = False
    destroy_graph: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiConfig':
        """Create a configuration instance from environment variables."""
        return cls(
            llm=GraphitiLLMConfig.from_env(),
            embedder=GraphitiEmbedderConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
            telemetry=TelemetryConfig.from_env(),
            group_id=os.environ.get('GROUP_ID'),
            use_custom_entities=os.environ.get('USE_CUSTOM_ENTITIES', 'false').lower() == 'true',
            destroy_graph=os.environ.get('DESTROY_GRAPH', 'false').lower() == 'true',
        )

    @classmethod
    def from_cli_and_env(cls, args: argparse.Namespace) -> 'GraphitiConfig':
        """Create configuration from CLI arguments, falling back to environment variables."""
        config = cls.from_env()

        # Override with CLI arguments if provided
        if args.neo4j_uri:
            config.neo4j.uri = args.neo4j_uri
        if args.neo4j_user:
            config.neo4j.user = args.neo4j_user
        if args.neo4j_password:
            config.neo4j.password = args.neo4j_password
        if args.openai_api_key:
            config.llm.api_key = args.openai_api_key
        if args.model_name:
            config.llm.model = args.model_name
        if args.temperature is not None:
            config.llm.temperature = args.temperature
        if args.group_id:
            config.group_id = args.group_id
        if args.use_custom_entities:
            config.use_custom_entities = args.use_custom_entities
        if args.destroy_graph:
            config.destroy_graph = args.destroy_graph
        # We could add CLI arguments for telemetry here in the future

        return config


class MCPConfig(BaseModel):
    """Configuration for MCP server."""

    transport: str = 'sse'  # Default to SSE transport

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> 'MCPConfig':
        """Create MCP configuration from CLI arguments."""
        return cls(transport=args.transport)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Create global config instance - will be properly initialized later
config = GraphitiConfig()

# Initialize global MCP config and telemetry client
mcp_config = MCPConfig()
telemetry_client = None

# MCP server instructions
GRAPHITI_MCP_INSTRUCTIONS = """
Welcome to Graphiti MCP - a memory service for AI agents built on a knowledge graph. Graphiti performs well
with dynamic data such as user interactions, changing enterprise data, and external information.

Graphiti transforms information into a richly connected knowledge network, allowing you to 
capture relationships between concepts, entities, and information. The system organizes data as episodes 
(content snippets), nodes (entities), and facts (relationships between entities), creating a dynamic, 
queryable memory store that evolves with new information. Graphiti supports multiple data formats, including 
structured JSON data, enabling seamless integration with existing data pipelines and systems.

Facts contain temporal metadata, allowing you to track the time of creation and whether a fact is invalid 
(superseded by new information).

Key capabilities:
1. Add episodes (text, messages, or JSON) to the knowledge graph with the add_episode tool
2. Search for nodes (entities) in the graph using natural language queries with search_nodes
3. Find relevant facts (relationships between entities) with search_facts
4. Retrieve specific entity edges or episodes by UUID
5. Manage the knowledge graph with tools like delete_episode, delete_entity_edge, and clear_graph

The server connects to a database for persistent storage and uses language models for certain operations. 
Each piece of information is organized by group_id, allowing you to maintain separate knowledge domains.

When adding information, provide descriptive names and detailed content to improve search quality. 
When searching, use specific queries and consider filtering by group_id for more relevant results.

For optimal performance, ensure the database is properly configured and accessible, and valid 
API keys are provided for any language model operations.
"""

# MCP server instance
mcp = FastMCP(
    'graphiti',
    instructions=GRAPHITI_MCP_INSTRUCTIONS,
)

# Initialize Graphiti client
graphiti_client: Graphiti | None = None


async def initialize_graphiti():
    """Initialize the Graphiti client with the configured settings."""
    global graphiti_client, config, telemetry_client

    try:
        # Create LLM client if possible
        llm_client = config.llm.create_client()
        if not llm_client and config.use_custom_entities:
            # If custom entities are enabled, we must have an LLM client
            raise ValueError('OPENAI_API_KEY must be set when custom entities are enabled')

        # Validate Neo4j configuration
        if not config.neo4j.uri or not config.neo4j.user or not config.neo4j.password:
            raise ValueError('NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set')

        embedder_client = config.embedder.create_client()
        cross_encoder_client = config.llm.create_cross_encoder_client()
        
        # Initialize telemetry client
        telemetry_client = await initialize_telemetry(
            config.telemetry,
            main_uri=config.neo4j.uri,
            main_user=config.neo4j.user,
            main_password=config.neo4j.password
        )
        
        # Set the shared telemetry client for diagnostic tools
        global shared_telemetry_client
        shared_telemetry_client = telemetry_client

        # Initialize Graphiti client
        graphiti_client = Graphiti(
            uri=config.neo4j.uri,
            user=config.neo4j.user,
            password=config.neo4j.password,
            llm_client=llm_client,
            embedder=embedder_client,
            cross_encoder=cross_encoder_client,
        )

        # Destroy graph if requested
        if config.destroy_graph:
            logger.info('Destroying graph...')
            await clear_data(graphiti_client.driver)

        # Initialize the graph database with Graphiti's indices
        await graphiti_client.build_indices_and_constraints()
        logger.info('Graphiti client initialized successfully')

        # Log configuration details for transparency
        if llm_client:
            logger.info(f'Using OpenAI model: {config.llm.model}')
            logger.info(f'Using temperature: {config.llm.temperature}')
        else:
            logger.info('No LLM client configured - entity extraction will be limited')

        logger.info(f'Using group_id: {config.group_id}')
        logger.info(
            f'Custom entity extraction: {"enabled" if config.use_custom_entities else "disabled"}'
        )
        
        # Initialize queue inspection tools with references to the queues
        import services.queue_inspection as queue_inspection
        queue_inspection.episode_queues = episode_queues
        queue_inspection.telemetry_client = telemetry_client
        logger.info('Queue inspection tools initialized')

    except Exception as e:
        logger.error(f'Failed to initialize Graphiti: {str(e)}')
        raise


def format_fact_result(edge: EntityEdge) -> dict[str, Any]:
    """Format an entity edge into a readable result.

    Since EntityEdge is a Pydantic BaseModel, we can use its built-in serialization capabilities.

    Args:
        edge: The EntityEdge to format

    Returns:
        A dictionary representation of the edge with serialized dates and excluded embeddings
    """
    return edge.model_dump(
        mode='json',
        exclude={
            'fact_embedding',
        },
    )


# Dictionary to store queues for each group_id
# Each queue is a list of tasks to be processed sequentially
episode_queues: dict[str, asyncio.Queue] = {}

# Global telemetry client instance
telemetry_client = None
# Dictionary to track if a worker is running for each group_id
queue_workers: dict[str, bool] = {}


async def process_episode_queue(group_id: str):
    """Process episodes for a specific group_id sequentially.

    This function runs as a long-lived task that processes episodes
    from the queue one at a time.
    """
    global queue_workers

    logger.info(f'Starting episode queue worker for group_id: {group_id}')
    queue_workers[group_id] = True

    try:
        while True:
            # Get the next episode data from the queue
            # This will wait if the queue is empty
            episode_data = await episode_queues[group_id].get()

            try:
                # Process the episode using our telemetry-enabled processor
                from services.episode_processor import process_episode_queue as process_with_telemetry
                
                # Pass the full graphiti_client object
                # This is needed because the add_episode methods exist on the Graphiti class, not on clients
                
                # Process the episode with telemetry
                await process_with_telemetry(
                    clients=graphiti_client,
                    telemetry_client=telemetry_client,
                    group_id=group_id,
                    episode_data=episode_data
                )
            except Exception as e:
                logger.error(f'Error processing queued episode for group_id {group_id}: {str(e)}')
                logger.error(traceback.format_exc())
            finally:
                # Mark the task as done regardless of success/failure
                episode_queues[group_id].task_done()
    except asyncio.CancelledError:
        logger.info(f'Episode queue worker for group_id {group_id} was cancelled')
    except Exception as e:
        logger.error(f'Unexpected error in queue worker for group_id {group_id}: {str(e)}')
        logger.error(traceback.format_exc())
    finally:
        queue_workers[group_id] = False
        logger.info(f'Stopped episode queue worker for group_id: {group_id}')


@mcp.tool()
async def add_episode(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
) -> SuccessResponse | ErrorResponse:
    """Add an episode to the Graphiti knowledge graph. This is the primary way to add information to the graph.

    This function returns immediately and processes the episode addition in the background.
    Episodes for the same group_id are processed sequentially to avoid race conditions.

    Args:
        name (str): Name of the episode
        episode_body (str): The content of the episode. When source='json', this must be a properly escaped JSON string,
                           not a raw Python dictionary. The JSON data will be automatically processed
                           to extract entities and relationships.
        group_id (str, optional): A unique ID for this graph. If not provided, uses the default group_id from CLI
                                 or a generated one.
        source (str, optional): Source type, must be one of:
                               - 'text': For plain text content (default)
                               - 'json': For structured data
                               - 'message': For conversation-style content
        source_description (str, optional): Description of the source
        uuid (str, optional): Optional UUID for the episode

    Examples:
        # Adding plain text content
        add_episode(
            name="Company News",
            episode_body="Acme Corp announced a new product line today.",
            source="text",
            source_description="news article",
            group_id="some_arbitrary_string"
        )

        # Adding structured JSON data
        # NOTE: episode_body must be a properly escaped JSON string. Note the triple backslashes
        add_episode(
            name="Customer Profile",
            episode_body="{\\\"company\\\": {\\\"name\\\": \\\"Acme Technologies\\\"}, \\\"products\\\": [{\\\"id\\\": \\\"P001\\\", \\\"name\\\": \\\"CloudSync\\\"}, {\\\"id\\\": \\\"P002\\\", \\\"name\\\": \\\"DataMiner\\\"}]}",
            source="json",
            source_description="CRM data"
        )

        # Adding message-style content
        add_episode(
            name="Customer Conversation",
            episode_body="user: What's your return policy?\nassistant: You can return items within 30 days.",
            source="message",
            source_description="chat transcript",
            group_id="some_arbitrary_string"
        )

    Notes:
        When using source='json':
        - The JSON must be a properly escaped string, not a raw Python dictionary
        - The JSON will be automatically processed to extract entities and relationships
        - Complex nested structures are supported (arrays, nested objects, mixed data types), but keep nesting to a minimum
        - Entities will be created from appropriate JSON properties
        - Relationships between entities will be established based on the JSON structure
    """
    global graphiti_client, episode_queues, queue_workers

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # Map string source to EpisodeType enum
        source_type = EpisodeType.text
        if source.lower() == 'message':
            source_type = EpisodeType.message
        elif source.lower() == 'json':
            source_type = EpisodeType.json

        # Use the provided group_id or fall back to the default from config
        effective_group_id = group_id if group_id is not None else config.group_id

        # Cast group_id to str to satisfy type checker
        # The Graphiti client expects a str for group_id, not Optional[str]
        group_id_str = str(effective_group_id) if effective_group_id is not None else ''

        # We've already checked that graphiti_client is not None above
        # This assert statement helps type checkers understand that graphiti_client is defined
        assert graphiti_client is not None, 'graphiti_client should not be None here'

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Prepare the episode data for the queue
        episode_data = {
            "name": name,
            "episode_body": episode_body,
            "source": source_type,
            "source_description": source_description,
            "uuid": uuid,
            "reference_time": datetime.now(timezone.utc),
            "entity_types": ENTITY_TYPES if config.use_custom_entities else {},
            "update_communities": True  # We'll still build communities after the episode
        }

        # Initialize queue for this group_id if it doesn't exist
        if group_id_str not in episode_queues:
            episode_queues[group_id_str] = asyncio.Queue()

        # Add the episode data to the queue
        await episode_queues[group_id_str].put(episode_data)

        # Start a worker for this queue if one isn't already running
        if not queue_workers.get(group_id_str, False):
            asyncio.create_task(process_episode_queue(group_id_str))

        # Return immediately with a success message
        return {
            'message': f"Episode '{name}' queued for processing (position: {episode_queues[group_id_str].qsize()})"
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error queuing episode task: {error_msg}')
        return {'error': f'Error queuing episode task: {error_msg}'}


@mcp.tool()
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    center_node_uuid: str | None = None,
    entity: str = '',  # cursor seems to break with None
) -> NodeSearchResponse | ErrorResponse:
    """Search the Graphiti knowledge graph for relevant node summaries.
    These contain a summary of all of a node's relationships with other nodes.

    Note: entity is a single entity type to filter results (permitted: "Preference", "Procedure").

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_nodes: Maximum number of nodes to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
        entity: Optional single entity type to filter results (permitted: "Preference", "Procedure")
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # Use the provided group_ids or fall back to the default from config if none provided
        effective_group_ids = (
            group_ids if group_ids is not None else [config.group_id] if config.group_id else []
        )

        # Configure the search
        if center_node_uuid is not None:
            search_config = NODE_HYBRID_SEARCH_NODE_DISTANCE.model_copy(deep=True)
        else:
            search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        search_config.limit = max_nodes

        filters = SearchFilters()
        if entity != '':
            filters.node_labels = [entity]

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Perform the search using the _search method
        search_results = await client._search(
            query=query,
            config=search_config,
            group_ids=effective_group_ids,
            center_node_uuid=center_node_uuid,
            search_filter=filters,
        )

        if not search_results.nodes:
            return NodeSearchResponse(message='No relevant nodes found', nodes=[])

        # Format the node results
        formatted_nodes: list[NodeResult] = [
            {
                'uuid': node.uuid,
                'name': node.name,
                'summary': node.summary if hasattr(node, 'summary') else '',
                'labels': node.labels if hasattr(node, 'labels') else [],
                'group_id': node.group_id,
                'created_at': node.created_at.isoformat(),
                'attributes': node.attributes if hasattr(node, 'attributes') else {},
            }
            for node in search_results.nodes
        ]

        return NodeSearchResponse(message='Nodes retrieved successfully', nodes=formatted_nodes)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching nodes: {error_msg}')
        return ErrorResponse(error=f'Error searching nodes: {error_msg}')


@mcp.tool()
async def search_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse:
    """Search the Graphiti knowledge graph for relevant facts.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_facts: Maximum number of facts to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
    """
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # Use the provided group_ids or fall back to the default from config if none provided
        effective_group_ids = (
            group_ids if group_ids is not None else [config.group_id] if config.group_id else []
        )

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        relevant_edges = await client.search(
            group_ids=effective_group_ids,
            query=query,
            num_results=max_facts,
            center_node_uuid=center_node_uuid,
        )

        if not relevant_edges:
            return {'message': 'No relevant facts found', 'facts': []}

        facts = [format_fact_result(edge) for edge in relevant_edges]
        return {'message': 'Facts retrieved successfully', 'facts': facts}
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching facts: {error_msg}')
        return {'error': f'Error searching facts: {error_msg}'}


@mcp.tool()
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an entity edge from the Graphiti knowledge graph.

    Args:
        uuid: UUID of the entity edge to delete
    """
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the entity edge by UUID
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
        # Delete the edge using its delete method
        await entity_edge.delete(client.driver)
        return {'message': f'Entity edge with UUID {uuid} deleted successfully'}
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting entity edge: {error_msg}')
        return {'error': f'Error deleting entity edge: {error_msg}'}


@mcp.tool()
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an episode from the Graphiti knowledge graph.

    Args:
        uuid: UUID of the episode to delete
    """
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the episodic node by UUID - EpisodicNode is already imported at the top
        episodic_node = await EpisodicNode.get_by_uuid(client.driver, uuid)
        # Delete the node using its delete method
        await episodic_node.delete(client.driver)
        return {'message': f'Episode with UUID {uuid} deleted successfully'}
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting episode: {error_msg}')
        return {'error': f'Error deleting episode: {error_msg}'}


@mcp.tool()
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse:
    """Get an entity edge from the Graphiti knowledge graph by its UUID.

    Args:
        uuid: UUID of the entity edge to retrieve
    """
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the entity edge directly using the EntityEdge class method
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)

        # Use the format_fact_result function to serialize the edge
        # Return the Python dict directly - MCP will handle serialization
        return format_fact_result(entity_edge)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting entity edge: {error_msg}')
        return {'error': f'Error getting entity edge: {error_msg}'}


@mcp.tool()
async def get_episodes(
    group_id: str | None = None, last_n: int = 10
) -> list[dict[str, Any]] | EpisodeSearchResponse | ErrorResponse:
    """Get the most recent episodes for a specific group.

    Args:
        group_id: ID of the group to retrieve episodes from. If not provided, uses the default group_id.
        last_n: Number of most recent episodes to retrieve (default: 10)
    """
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # Use the provided group_id or fall back to the default from config
        effective_group_id = group_id if group_id is not None else config.group_id

        if not isinstance(effective_group_id, str):
            return {'error': 'Group ID must be a string'}

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        episodes = await client.retrieve_episodes(
            group_ids=[effective_group_id], last_n=last_n, reference_time=datetime.now(timezone.utc)
        )

        if not episodes:
            return {'message': f'No episodes found for group {effective_group_id}', 'episodes': []}

        # Use Pydantic's model_dump method for EpisodicNode serialization
        formatted_episodes = [
            # Use mode='json' to handle datetime serialization
            episode.model_dump(mode='json')
            for episode in episodes
        ]

        # Return the Python list directly - MCP will handle serialization
        return formatted_episodes
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting episodes: {error_msg}')
        return {'error': f'Error getting episodes: {error_msg}'}


@mcp.tool()
async def clear_graph() -> SuccessResponse | ErrorResponse:
    """Clear all data from the Graphiti knowledge graph and rebuild indices."""
    global graphiti_client

    if graphiti_client is None:
        return {'error': 'Graphiti client not initialized'}

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # clear_data is already imported at the top
        await clear_data(client.driver)
        await client.build_indices_and_constraints()
        return {'message': 'Graph cleared successfully and indices rebuilt'}
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error clearing graph: {error_msg}')
        return {'error': f'Error clearing graph: {error_msg}'}


@mcp.resource('http://graphiti/status')
async def get_status() -> StatusResponse:
    """Get the status of the Graphiti MCP server and Neo4j connection."""
    global graphiti_client

    if graphiti_client is None:
        return {'status': 'error', 'message': 'Graphiti client not initialized'}

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Test Neo4j connection
        await client.driver.verify_connectivity()
        return {'status': 'ok', 'message': 'Graphiti MCP server is running and connected to Neo4j'}
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error checking Neo4j connection: {error_msg}')
        return {
            'status': 'error',
            'message': f'Graphiti MCP server is running but Neo4j connection failed: {error_msg}',
        }


async def initialize_server() -> tuple[FastMCP, MCPConfig]:
    """Parse CLI arguments and initialize the Graphiti server configuration.
    
    Returns:
        tuple: (FastMCP instance, MCPConfig instance)
    """
    global mcp, config, telemetry_client, mcp_config

    parser = argparse.ArgumentParser(description='Graphiti MCP Server')

    # Neo4j connection settings
    parser.add_argument('--neo4j-uri', help='Neo4j URI')
    parser.add_argument('--neo4j-user', help='Neo4j username')
    parser.add_argument('--neo4j-password', help='Neo4j password')

    # OpenAI API settings
    parser.add_argument('--openai-api-key', help='OpenAI API key for LLM access')
    parser.add_argument('--model-name', help='Model to use for extraction (e.g. gpt-4)')
    parser.add_argument(
        '--temperature', type=float, help='Temperature for model generation (e.g. 0.7)'
    )

    # Feature flags and configuration
    parser.add_argument('--group-id', help='Group ID for knowledge graph partitioning')
    parser.add_argument(
        '--use-custom-entities',
        action='store_true',
        help='Enable custom entity extraction for domain-specific entities',
    )
    parser.add_argument(
        '--destroy-graph', action='store_true', help='Clear the graph on startup (dangerous!)'
    )
    
    # Telemetry settings
    parser.add_argument(
        '--enable-telemetry',
        action='store_true',
        help='Enable telemetry data collection',
        default=True
    )

    # MCP transport configuration
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse'],
        default='sse',
        help='Transport mechanism for MCP (stdio or sse)',
    )

    args = parser.parse_args()

    # Initialize configuration from environment variables and CLI arguments
    config = GraphitiConfig.from_cli_and_env(args)
    mcp_config = MCPConfig.from_cli(args)

    # Initialize MCP server with appropriate transport
    transport = mcp_config.transport
    if transport == 'stdio':
        mcp = FastMCP()
    else:  # Default to SSE (Server-Sent Events)
        mcp = FastMCP('sse')

    return mcp, mcp_config


async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    global mcp, telemetry_client, mcp_config

    # Initialize server and Graphiti
    logger.info('Initializing Graphiti MCP Server...')
    mcp, mcp_config = await initialize_server()
    await initialize_graphiti()
    
    # Register all MCP tools
    logger.info('Registering MCP tools')
    
    # Core knowledge graph tools
    mcp.tool()(add_episode)
    mcp.tool()(search_nodes)
    mcp.tool()(search_facts)
    mcp.tool()(get_entity_edge)
    mcp.tool()(delete_entity_edge)
    mcp.tool()(delete_episode)
    mcp.tool()(get_episodes)
    mcp.tool()(clear_graph)
    mcp.tool()(get_status)
    
    # Always register telemetry diagnostic tools (they'll return appropriate errors if telemetry is disabled)
    logger.info('Registering telemetry diagnostic tools')
    mcp.tool()(telemetry_episode_trace)
    mcp.tool()(telemetry_error_patterns)
    mcp.tool()(telemetry_episodes_with_error)
    mcp.tool()(telemetry_stats)
    mcp.tool()(telemetry_recent_errors)
    
    # Register queue inspection tools
    logger.info('Registering queue inspection tools')
    mcp.tool()(get_queue_stats)
    mcp.tool()(get_job_by_index)

    # Get transport config from mcp_config, don't rely on settings object
    transport = mcp_config.transport
    logger.info(f'Starting MCP server with transport: {transport}')
    try:
        if transport == 'stdio':
            logger.info('About to start stdio transport')
            await mcp.run_stdio_async()
        elif transport == 'sse':
            logger.info(
                f'Running MCP server with SSE transport'
            )
            await mcp.run_sse_async()
    except Exception as e:
        logger.error(f'Error starting MCP server: {e}')
        # Print stack trace to help debug the issue
        import traceback
        logger.error(traceback.format_exc())


@mcp.tool()
async def telemetry_episode_trace(episode_id: str, content_group_id: str = None) -> TelemetryResponse | ErrorResponse:
    """Get the full processing trace for an episode.
    
    This tool provides detailed information about all processing steps and errors that occurred
    during the processing of a specific episode.
    
    Args:
        episode_id: The unique ID of the episode to get trace information for. This can be:
                    - A Neo4j node ID (UUID format like '1105c001-9aca-44df-b787-08a8d10a5d70')
                    - An episode title or name stored in the episode_id property
                    - An element ID in format '4:1105c001-9aca-44df-b787-08a8d10a5d70:121'
        content_group_id: Optional content group_id to search for related content. 
                          If not provided, will use the client_group_id from telemetry.
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        logger.info(f"Looking up telemetry for episode identifier: {episode_id}")
        
        # Determine if this is a Neo4j internal ID and handle appropriately
        is_uuid_format = bool(re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', episode_id))
        
        if is_uuid_format or ':' in episode_id:
            # Direct Neo4j ID lookup using the graph database ID
            logger.info(f"Attempting Neo4j direct ID lookup for: {episode_id}")
            query = """
            MATCH (l) WHERE l.group_id = 'graphiti_logs'
            RETURN l as episode, id(l) as node_id
            """
            
            # Execute query directly since we need all nodes to filter manually
            all_nodes = await telemetry_client.run_query(query)
            
            # Find matching node by ID
            matched_node = None
            uuid_part = episode_id.split(':')[1] if ':' in episode_id else episode_id
            
            if all_nodes:
                logger.info(f"Found {len(all_nodes)} telemetry records, searching for UUID part: {uuid_part}")
                for node in all_nodes:
                    node_id_str = str(node.get('node_id', ''))
                    if node_id_str == uuid_part or uuid_part in node_id_str:
                        matched_node = node.get('episode')
                        logger.info(f"Found matching node by ID: {matched_node}")
                        break
            
            if matched_node:
                # Format the episode data
                episode_info = {'episode': {}}
                # Convert node to dict and handle datetime objects
                for key, value in matched_node.items():
                    if isinstance(value, datetime):
                        episode_info['episode'][key] = value.isoformat()
                    else:
                        episode_info['episode'][key] = value
                        
                # Get the actual episode_id for related content
                actual_episode_id = matched_node.get('episode_id', episode_id)
            else:
                return {"error": f"No telemetry data found matching ID {episode_id}"}
        else:
            # Standard lookup by episode_id property
            episode_info = await telemetry_client.get_episode_info(episode_id)
            actual_episode_id = episode_id
        
        if not episode_info or not episode_info.get('episode'):
            return {"error": f"No telemetry data found for episode {episode_id}"}
        
        # Find related content if processing was successful
        if episode_info.get("episode", {}).get("status") == "completed":
            related_content = await telemetry_client.find_related_content(
                actual_episode_id, 
                content_group_id=content_group_id
            )
            episode_info["related_content"] = related_content
        
        return {
            "data": episode_info, 
            "message": f"Retrieved telemetry trace for episode: {episode_id}"
        }
    except Exception as e:
        logger.error(f"Error retrieving episode trace: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Failed to retrieve episode trace: {str(e)}"}


@mcp.tool()
async def telemetry_error_patterns() -> TelemetryResponse | ErrorResponse:
    """Get patterns of errors across episodes.
    
    This tool analyzes all telemetry data to identify common error patterns
    across multiple episodes, helping to identify systematic issues.
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        from telemetry.diagnostic_queries import ERROR_PATTERNS_QUERY
        
        result = await telemetry_client.run_query(ERROR_PATTERNS_QUERY)
        return {"data": result, "message": "Successfully retrieved error patterns"}
    except Exception as e:
        return {"error": f"Failed to retrieve error patterns: {str(e)}"}


@mcp.tool()
async def telemetry_episodes_with_error(error_type: str) -> TelemetryResponse | ErrorResponse:
    """Get all episodes affected by a specific error type.
    
    This tool allows you to find all episodes that experienced a particular type of error,
    helping to understand the impact and scope of specific issues.
    
    Args:
        error_type: The type of error to search for (e.g., "DatabaseConnectionError")
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        from telemetry.diagnostic_queries import EPISODES_WITH_ERROR_TYPE_QUERY
        
        result = await telemetry_client.run_query(EPISODES_WITH_ERROR_TYPE_QUERY, {"error_type": error_type})
        return {"data": result, "message": f"Successfully retrieved episodes with error type: {error_type}"}
    except Exception as e:
        return {"error": f"Failed to retrieve episodes with error: {str(e)}"}


@mcp.tool()
async def telemetry_stats() -> TelemetryResponse | ErrorResponse:
    """Get overall episode processing statistics.
    
    This tool provides summary statistics about all episode processing activities,
    including success rates, failure counts, and average processing times.
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        # Use the improved telemetry client method instead of raw query
        stats = await telemetry_client.get_telemetry_stats()
        if not stats:
            stats = {
                "total_episodes": 0,
                "completed": 0,
                "failed": 0,
                "in_progress": 0,
                "avg_processing_time_ms": 0,
                "total_errors": 0,
                "success_rate": 0,
                "no_data": True
            }
        return {"data": stats, "message": "Successfully retrieved processing statistics"}
    except Exception as e:
        logger.error(f"Failed to retrieve telemetry stats: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Failed to retrieve processing statistics: {str(e)}"}


@mcp.tool()
async def telemetry_recent_errors() -> TelemetryResponse | ErrorResponse:
    """Get the most recent errors from episode processing.
    
    This tool returns the 20 most recent errors that occurred during episode processing,
    providing a quick view of recent issues.
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
        
    try:
        from telemetry.diagnostic_queries import RECENT_ERRORS_QUERY
        
        result = await telemetry_client.run_query(RECENT_ERRORS_QUERY)
        return {"data": result, "message": "Successfully retrieved recent errors"}
    except Exception as e:
        return {"error": f"Failed to retrieve recent errors: {str(e)}"}


@mcp.tool()
async def telemetry_lookup_by_content_uuid(content_uuid: str) -> TelemetryResponse | ErrorResponse:
    """Find telemetry records related to a specific content node by its UUID.
    
    This tool provides a direct bridge between content in the knowledge graph and
    the telemetry system that tracks how that content was processed. It's especially
    useful for finding the processing history of specific content items.
    
    Args:
        content_uuid: The UUID of the content node to find telemetry for
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
    
    try:
        logger.info(f"Looking up telemetry for content UUID: {content_uuid}")
        # Use the enhanced lookup method to find telemetry records
        results = await telemetry_client.lookup_telemetry_for_content_uuid(content_uuid)
        
        if "error" in results:
            return {"error": results["error"]}
            
        return {
            "data": results, 
            "message": f"Found {results.get('matches_found', 0)} telemetry records for content {results.get('content_info', {}).get('name')}"
        }
    except Exception as e:
        logger.error(f"Error looking up telemetry for content UUID: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Failed to lookup telemetry: {str(e)}"}


@mcp.tool()
async def telemetry_search(search_term: str, limit: int = 5, client_group_id: str = None) -> TelemetryResponse | ErrorResponse:
    """Search for telemetry records by name or ID fragments.
    
    This tool allows finding telemetry records using partial names, IDs, or fuzzy matches,
    making it easier to locate processing information for specific episodes.
    
    Args:
        search_term: Text to search for - can be a partial name, ID, or fragment
        limit: Maximum number of results to return (default: 5)
        client_group_id: Optional client group_id to filter results to a specific content group
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
    
    try:
        # Search for matching telemetry records
        matches = await telemetry_client.find_episode_by_name_or_id(
            search_term, 
            limit=limit,
            client_group_id=client_group_id
        )
        
        if not matches:
            return {
                "data": [],
                "message": f"No telemetry records found matching '{search_term}'"
            }
            
        # Create a summary of each match for easier browsing
        match_summaries = []
        for match in matches:
            episode = match.get("episode", {})
            summary = {
                "episode_id": episode.get("episode_id", "Unknown"),
                "original_name": episode.get("original_name", "Unknown"),
                "status": episode.get("status", "Unknown"),
                "start_time": episode.get("start_time", ""),
                "processing_time_ms": episode.get("processing_time_ms", 0),
                "match_relevance": episode.get("match_relevance", "Unknown"),
                "client_group_id": episode.get("client_group_id", "Unknown"),
                "attempt_count": episode.get("attempt_count", 1),
                "error_count": match.get("outcome_summary", {}).get("error_count", 0)
            }
            match_summaries.append(summary)
        
        return {
            "data": match_summaries,
            "message": f"Found {len(matches)} telemetry records matching '{search_term}'"
        }
    except Exception as e:
        logger.error(f"Error searching telemetry records: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Failed to search telemetry records: {str(e)}"}


@mcp.tool()
async def telemetry_find_content(episode_id: str, content_group_id: str = None) -> TelemetryResponse | ErrorResponse:
    """Find content created from a telemetry episode.
    
    This tool helps bridge the gap between telemetry records and the actual content
    that was created as a result of successful processing.
    
    Args:
        episode_id: The ID of the telemetry episode to find content for
        content_group_id: Optional content group_id to search within. If not provided, 
                         will use the client_group_id from the telemetry record.
    """
    if not telemetry_client:
        return {"error": "Telemetry system is not enabled"}
    
    try:
        # Find related content
        related_content = await telemetry_client.find_related_content(
            episode_id,
            content_group_id=content_group_id
        )
        
        if not related_content.get("content_found", False):
            return {
                "data": related_content,
                "message": f"No content found for telemetry episode: {episode_id}. Reason: {related_content.get('reason', 'Unknown')}"
            }
            
        return {
            "data": related_content,
            "message": f"Found related content for telemetry episode: {episode_id}"
        }
    except Exception as e:
        logger.error(f"Error finding content for telemetry episode: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Failed to find content for telemetry episode: {str(e)}"}


def main():
    """Main function to run the Graphiti MCP server."""
    try:
        logger.info('Starting main function')
        asyncio.run(run_mcp_server())
        logger.info('Server completed normally')
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Error running server: {e}')
        # Print stack trace to help debug the issue
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
