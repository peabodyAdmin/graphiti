# Graphiti+ Implementation Plan

## Executive Summary

**Mission**: Integrate Aiden orchestration layer into the graphiti repository as a parallel extension (`aiden/` directory) while maintaining upstream compatibility and enabling single-deployment architecture.

**Key Insight**: Aiden and Graphiti nodes coexist in the **same Neo4j database** with lightweight property references, supporting a future where direct edges can connect conversations to memories.

**Status**: ✅ Architecture validated against Aiden docs
**Timeline**: 11 days (Phases 1-7)
**Risk Level**: Low (upstream compatibility preserved, clean separation)

---

## Phase 1: Repository Structure (Day 1)

### Goals
- Create aiden/ directory structure
- Copy Aiden documentation
- Set up Python package structure
- Verify no conflicts with existing code

### Tasks

**1.1: Create Directory Structure**
```bash
cd /Users/robhitchens/Documents/projects/peabawdy/graphiti

mkdir -p aiden/aiden_core/{models,storage,graphiti_client,events,orchestration}
mkdir -p aiden/aiden_core/storage/repositories
mkdir -p aiden/server/api/routers
mkdir -p aiden/server/workers
mkdir -p aiden/mcp_server/src
mkdir -p aiden/tests/{unit,integration}
mkdir -p aiden/docs
```

**1.2: Copy Documentation**
```bash
cp -r /Users/robhitchens/Documents/projects/peabawdy/AidenMemoryAgentChat/docs/* \
     aiden/docs/
```

**1.3: Create Python Package Files**
```bash
# aiden/pyproject.toml
# aiden/aiden_core/__init__.py
# aiden/server/__init__.py
# aiden/README.md
```

**1.4: Create CLAUDE.md**
```markdown
# Aiden: The Orchestration Layer for Graphiti+

Aiden extends Graphiti with:
- Process orchestration (Service, Tool, Process)
- Conversation management with alternatives
- User-scoped knowledge graphs (group_id = userId)
- Working memory assembly with compression

**Same database. Different node types. Unified knowledge graph.**

See docs/ for complete specifications.
```

### Success Criteria
- [ ] aiden/ directory structure complete
- [ ] Documentation copied
- [ ] No file conflicts with existing graphiti code
- [ ] Can run existing graphiti tests without failures

---

## Phase 2: Core Domain Models (Days 2-3)

### Goals
- Implement Aiden node types (Service, Tool, Process, etc.)
- Create Neo4j storage layer
- Implement GraphitiMemoryClient integration

### Tasks

**2.1: Create Domain Models** (`aiden/aiden_core/models/`)

```python
# service.py
class Service:
    id: str
    owner_id: str
    name: str
    type: ServiceType  # neo4j_graph, rest_api, llm_provider, mcp_server
    connection_schema: dict
    protocol: Protocol  # bolt, http, stdio, sse
    requires_secret: bool
    enabled: bool
    status: HealthStatus  # healthy, degraded, down
    shared: bool
    # ... timestamps, etc.

# tool.py  
class Tool:
    id: str
    owner_id: str
    service_id: str  # Property reference (not edge)
    connection_params: dict
    operation: dict  # Discriminated union by service type
    input_schema: dict
    output_schema: dict
    enabled: bool
    shared: bool

# process.py
class Process:
    id: str
    owner_id: str
    initial_context: list[str]
    steps: list[ProcessStep]
    output_template: str
    token_budget: int | None
    enabled: bool

# conversation.py
class Conversation:
    id: str
    user_id: str
    process_id: str | None  # UI hint (mutable)
    status: ConversationStatus  # active, archived
    active_entities: list[str]  # Entity UUIDs (property array)
    # ... timestamps, forking fields

# conversation_turn.py
class ConversationTurn:
    id: str
    conversation_id: str
    parent_turn_id: str | None
    sequence: int
    speaker: Speaker  # user, agent, system
    turn_type: TurnType  # message, tool_result, summary
    content: str  # Permanent storage
    alternatives: list[Alternative]
    timestamp: datetime

class Alternative:
    id: str
    episode_id: str | None  # Graphiti Episode UUID (async binding)
    process_id: str | None  # Execution truth (immutable)
    is_active: bool
    input_context: InputContext
    cache_status: CacheStatus  # valid, stale, generating
    created_at: datetime

class InputContext:
    parent_alternative_id: str | None

# working_memory.py
class WorkingMemory:
    conversation_id: str
    current_turn_id: str
    current_alternative_id: str
    immediate_path: list[PathEntry]  # [{turnId, alternativeId, episodeId}]
    summaries: list[str]
    active_entities: list[EntityReference]
    introspection_context: list[str]  # Introspection Episode UUIDs
    total_tokens: int

class EntityReference:
    entity_uuid: str
    name: str
    category: str
    relevance_score: float
    include_summary: bool
    include_facets: bool
    include_relationships: bool
```

**2.2: Create Neo4j Storage Layer** (`aiden/aiden_core/storage/`)

```python
# neo4j_driver.py
class AidenNeo4jDriver:
    """
    Neo4j driver for Aiden nodes.
    
    CRITICAL: Connects to SAME database as Graphiti!
    """
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = None
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    async def create_conversation(self, conversation: Conversation) -> Conversation:
        # CREATE (:Conversation {id, userId, activeEntities: [], ...})
        pass
    
    async def create_turn(self, turn: ConversationTurn) -> ConversationTurn:
        # CREATE (:ConversationTurn {id, conversationId, alternatives: [], ...})
        pass
    
    # ... CRUD operations for all Aiden node types

# repositories/conversation_repository.py
class ConversationRepository:
    def __init__(self, driver: AidenNeo4jDriver):
        self.driver = driver
    
    async def get_conversation_tree(self, conversation_id: str) -> dict:
        # Load conversation with all turns and alternatives
        pass
    
    async def get_active_path(
        self, 
        turn_id: str,
        alternative_id: str
    ) -> list[PathEntry]:
        # Traverse isActive alternatives back to root
        pass
```

**2.3: Create GraphitiMemoryClient** (`aiden/aiden_core/graphiti_client/`)

```python
# memory_client.py
class GraphitiMemoryClient:
    """
    Wrapper around graphiti_core for Aiden memory operations.
    
    SAME database. SAME connection. Different node types.
    """
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = None
    ):
        # Import from graphiti_core (local library, not HTTP!)
        from graphiti_core import Graphiti
        
        self.graphiti = Graphiti(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
            # NO separate database parameter!
        )
    
    async def create_episode(
        self,
        name: str,
        content: str,
        user_id: str,  # group_id = userId!
        source: str = "conversation"
    ) -> str:
        """Create Episode in Graphiti (same DB as Aiden nodes)."""
        episode = await self.graphiti.add_episode(
            name=name,
            episode_body=content,
            group_id=user_id,  # User-scoped!
            source=source
        )
        return episode.uuid
    
    async def get_user_entities(
        self,
        user_id: str,
        limit: int = 50
    ) -> list:
        """Get all entities for user across ALL conversations."""
        return await self.graphiti.search_nodes(
            query="",
            group_ids=[user_id],
            max_nodes=limit
        )
    
    async def semantic_search(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> list[dict]:
        """Semantic search across user's Episodes."""
        return await self.graphiti.search(
            query=query,
            group_ids=[user_id],
            limit=limit
        )
```

### Success Criteria
- [ ] All domain models defined with type hints
- [ ] AidenNeo4jDriver connects to same database as Graphiti
- [ ] GraphitiMemoryClient wraps graphiti_core library
- [ ] Unit tests for domain models pass
- [ ] Can create Aiden nodes alongside Graphiti nodes

---

## Phase 3: REST API Server (Days 4-5)

### Goals
- Create FastAPI application
- Implement API routers for all entities
- Set up async worker infrastructure
- Implement event publishing

### Tasks

**3.1: FastAPI Application** (`aiden/server/api/main.py`)

```python
from fastapi import FastAPI
from aiden.server.api.routers import (
    conversations,
    processes,
    tools,
    services
)

app = FastAPI(title="Aiden API")

app.include_router(conversations.router, prefix="/api/v1/conversations")
app.include_router(processes.router, prefix="/api/v1/processes")
app.include_router(tools.router, prefix="/api/v1/tools")
app.include_router(services.router, prefix="/api/v1/services")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**3.2: API Routers** (`aiden/server/api/routers/`)

```python
# conversations.py
@router.post("/{conversation_id}/turns", status_code=202)
async def create_turn(
    conversation_id: str,
    request: CreateTurnRequest,
    user_id: str = Depends(get_current_user)
):
    # 1. Create ConversationTurn + Alternative (episodeId=null)
    # 2. Publish TurnCreated event
    # 3. Return 202 Accepted with operationId
    pass

# processes.py
@router.post("/{process_id}/execute", status_code=202)
async def execute_process(
    process_id: str,
    request: ExecuteProcessRequest
):
    # 1. Validate Process and dependencies
    # 2. Publish ProcessExecutionRequested event
    # 3. Return 202 Accepted with operationId
    pass
```

**3.3: Background Workers** (`aiden/server/workers/`)

```python
# episode_ingestion_worker.py
class EpisodeIngestionWorker:
    """
    Consumes TurnCreated events.
    Creates Episodes in Graphiti (same DB!).
    Backfills Alternative.episodeId.
    """
    
    async def consume_turn_created(self, event: TurnCreatedEvent):
        # 1. Extract content from event
        # 2. Call graphiti_client.create_episode()
        # 3. Poll Graphiti for Episode by name "Turn:{alternativeId}"
        # 4. Update Alternative.episodeId = episode.uuid
        # 5. Publish EpisodeCreated event

# process_executor.py
class ProcessExecutor:
    """
    Executes ProcessSteps.
    Invokes Tools against Services.
    Manages job lifecycle.
    """
    
    async def execute_step(self, step: ProcessStep, context: dict):
        # 1. Resolve Tool
        # 2. Bind inputs from context
        # 3. Invoke Tool operation
        # 4. Capture output
        # 5. Update context
```

### Success Criteria
- [ ] FastAPI server starts successfully
- [ ] API endpoints return 202 for async operations
- [ ] Workers consume events from queue
- [ ] Episode ingestion backfills episodeId
- [ ] Integration tests pass

---

## Phase 4: MCP Server (Day 6)

### Goals
- Create Aiden MCP server
- Implement tools for process execution and conversation management
- Test MCP connectivity

### Tasks

**4.1: MCP Server Implementation** (`aiden/mcp_server/src/`)

```python
# aiden_mcp_server.py
from mcp.server import Server
from aiden.aiden_core.storage import AidenNeo4jDriver
from aiden.aiden_core.graphiti_client import GraphitiMemoryClient

server = Server("aiden-mcp-server")

@server.call_tool()
async def execute_process(
    process_id: str,
    inputs: dict
) -> str:
    """Execute a Process and return results."""
    # 1. Load Process
    # 2. Execute steps
    # 3. Return output
    pass

@server.call_tool()
async def create_conversation(
    title: str,
    process_id: str
) -> dict:
    """Create new conversation."""
    pass

@server.call_tool()
async def add_turn(
    conversation_id: str,
    content: str,
    speaker: str
) -> dict:
    """Add turn to conversation."""
    pass
```

### Success Criteria
- [ ] MCP server starts successfully
- [ ] Tools registered and callable
- [ ] Can execute processes via MCP
- [ ] Can manage conversations via MCP

---

## Phase 5: Deployment Configuration (Days 7-8)

### Goals
- Create Docker Compose for single-instance deployment
- Create Dockerfiles for Graphiti and Aiden services
- Set up development scripts
- Test full-stack deployment

### Tasks

**5.1: Docker Compose** (`deployment/docker-compose.yml`)

```yaml
services:
  neo4j:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt (single port for all!)
    volumes:
      - neo4j_data:/data
  
  graphiti-server:
    build:
      context: .
      dockerfile: Dockerfile.graphiti
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
    depends_on:
      - neo4j
    ports:
      - "8000:8000"
  
  aiden-server:
    build:
      context: .
      dockerfile: aiden/Dockerfile
    environment:
      NEO4J_URI: bolt://neo4j:7687  # SAME DATABASE!
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
    depends_on:
      - neo4j
      - graphiti-server
    ports:
      - "8001:8001"
  
  aiden-workers:
    build:
      context: .
      dockerfile: aiden/Dockerfile.worker
    environment:
      NEO4J_URI: bolt://neo4j:7687  # SAME DATABASE!
    depends_on:
      - neo4j
      - aiden-server

volumes:
  neo4j_data:
```

**5.2: Development Scripts** (`scripts/`)

```bash
# start-dev.sh - Full stack
#!/bin/bash
docker-compose -f deployment/docker-compose.yml up

# start-graphiti.sh - Graphiti only
#!/bin/bash
cd graphiti && ./start.sh

# start-aiden.sh - Aiden only  
#!/bin/bash
cd aiden && python -m aiden.server.api.main
```

### Success Criteria
- [ ] docker-compose up starts all services
- [ ] All services connect to same Neo4j instance
- [ ] Graphiti and Aiden nodes coexist in database
- [ ] Health checks pass for all services

---

## Phase 6: Integration Testing (Days 9-10)

### Goals
- Test Episode creation and binding
- Test Entity extraction and activeEntities
- Test WorkingMemory assembly
- Validate user-scoped knowledge graphs

### Test Cases

**Test 1: Episode Binding**
```python
async def test_episode_binding():
    # 1. Create conversation
    # 2. Add user turn
    # 3. Verify Turn created with episodeId=null
    # 4. Wait for worker to backfill
    # 5. Verify episodeId populated with Episode UUID
    # 6. Verify Episode exists in Graphiti with same content
```

**Test 2: Entity Extraction**
```python
async def test_entity_extraction():
    # 1. Create conversation
    # 2. Add turn mentioning entities
    # 3. Wait for Graphiti extraction
    # 4. Verify Entities created with group_id=userId
    # 5. Verify Conversation.activeEntities updated
```

**Test 3: User-Scoped Learning**
```python
async def test_user_scoped_learning():
    # 1. Create two users (alice, bob)
    # 2. Each user creates conversations with entities
    # 3. Verify alice's agent can't see bob's entities
    # 4. Verify semantic search filtered by group_id
    # 5. Verify each user trains independent knowledge graph
```

**Test 4: WorkingMemory Assembly**
```python
async def test_working_memory():
    # 1. Create conversation with multiple turns
    # 2. Assemble WorkingMemory
    # 3. Verify immediatePath follows isActive alternatives
    # 4. Verify activeEntities includes Entities from path
    # 5. Verify totalTokens accurate
```

### Success Criteria
- [ ] All integration tests pass
- [ ] Episode binding works end-to-end
- [ ] Entity extraction populates activeEntities
- [ ] User-scoped isolation verified
- [ ] WorkingMemory assembly correct

---

## Phase 7: Documentation (Day 11)

### Goals
- Update root CLAUDE.md with dual-system philosophy
- Create aiden/README.md
- Document deployment procedures
- Create migration guide

### Tasks

**7.1: Update Root CLAUDE.md**

```markdown
# Graphiti+: Semantic Memory + Orchestration

This repository contains:

## Graphiti (Upstream Library)
- graphiti_core/ - Semantic memory foundation
- Episodes, Entities, Facts
- Embedding generation, semantic search
- Temporal knowledge graphs

## Aiden (Orchestration Extension)
- aiden/ - Process orchestration layer  
- Services, Tools, Processes
- Conversations with alternatives
- User-scoped knowledge graphs

**Same database. Different node types. Unified knowledge graph.**

See aiden/README.md for Aiden specifics.
See graphiti_core/README.md for Graphiti specifics.
```

**7.2: Create aiden/README.md**

```markdown
# Aiden: The Orchestration Layer

Aiden extends Graphiti with process orchestration and conversation management.

## Architecture

**Same Neo4j Database**:
- Graphiti nodes: :Episode, :Entity, :Fact
- Aiden nodes: :Service, :Tool, :Process, :Conversation, :ConversationTurn

**User-Scoped Knowledge**:
- Episodes: group_id = userId
- Entities: group_id = userId
- Agent learns across all user conversations

**Lightweight Integration**:
- Property references (episodeId, activeEntities)
- Future-ready for direct edges

See docs/ for complete specifications.
```

### Success Criteria
- [ ] CLAUDE.md updated with dual-system philosophy
- [ ] aiden/README.md created
- [ ] Deployment guide complete
- [ ] Migration checklist created

---

## Rollback Plan

If issues arise:
1. **aiden/ in separate directory** - Just remove aiden/
2. **graphiti_core unchanged** - No rollback needed
3. **Deployment configs in deployment/** - Easy to revert
4. **Same database** - Can delete Aiden nodes via label

---

## Success Metrics

### Technical
- [ ] All tests pass (graphiti_core + aiden)
- [ ] No conflicts between Graphiti and Aiden nodes
- [ ] Episode binding < 1 second
- [ ] Semantic search works across conversations
- [ ] User isolation verified

### Architecture
- [ ] graphiti_core unchanged (can merge upstream)
- [ ] Clean separation (Aiden doesn't modify Graphiti nodes)
- [ ] Single Neo4j deployment works
- [ ] Both MCP servers operational

### Documentation
- [ ] Architecture documented
- [ ] API docs complete
- [ ] Deployment guide tested
- [ ] Migration path clear

---

## Next Steps After Phase 7

**Phase 8: Advanced Features**
- Add direct edges (HAS_EPISODE, HAS_ENTITY)
- Implement carousel introspection
- Add compression and summarization
- Build out Process library

**Phase 9: Production Hardening**
- Kubernetes manifests
- Terraform for GCP
- Monitoring and alerting
- Performance optimization

**Phase 10: Upstream Contribution**
- Document Aiden as Graphiti extension
- Contribute improvements to graphiti_core
- Share patterns with community