openapi: 3.1.0
info:
  title: Aiden Memory Agent Chat API
  version: 5.0.0
  description: |
    Specification-driven API for Aiden Memory Agent Chat system. This document is SOURCE OF TRUTH - 
    code must conform to spec, never vice versa.
    
    ## Architecture Patterns
    
    **Synchronous Operations (200/404/422):**
    - Read queries (GET endpoints)
    - Immediate validation failures
    - Metadata-only updates
    - Health checks
    
    **Asynchronous Operations (202 Accepted):**
    - Create/Update/Delete mutations
    - Process executions
    - Worker jobs
    - All operations producing events
    
    ## Event-Driven Core
    All mutations return `202 Accepted` with `operationId`. Clients poll `/api/v1/operations/{operationId}` 
    or subscribe to webhooks for completion. See AsyncAPI spec for event schemas.
    
    ## Business Rules
    All validation rules and invariants documented with `x-business-rules` extensions referencing 
    BR-* identifiers from Business Rules documentation.

  contact:
    name: API Support
    email: support@aidenmemory.ai
  license:
    name: Proprietary

servers:
  - url: https://api.aidenmemory.ai/api/v1
    description: Production
  - url: https://staging-api.aidenmemory.ai/api/v1
    description: Staging
  - url: http://localhost:3000/api/v1
    description: Local Development

security:
  - bearerAuth: []

tags:
  - name: Services
    description: Infrastructure endpoint management
  - name: Templates
    description: Service/Tool template management (archival + provenance)
  - name: ServiceTemplates
    description: Shareable Service blueprints (immutable structure)
  - name: Secrets
    description: Credential management
  - name: Tools
    description: Operation definitions
  - name: ToolTemplates
    description: Shareable Tool blueprints (immutable structure)
  - name: Processes
    description: Workflow orchestration
  - name: Conversations
    description: Dialogue management
  - name: Turns
    description: Conversation position management
  - name: Alternatives
    description: Multi-version turn management
  - name: WorkingMemory
    description: Context assembly
  - name: Entities
    description: Knowledge graph entities (Graphiti integration)
  - name: Summaries
    description: Compression artifact management
  - name: Introspections
    description: Agent reflection carousel management
  - name: Operations
    description: Async operation status
  - name: Workers
    description: Background job management
  - name: Health
    description: System health endpoints

paths:
  # ==================== SERVICES ====================
  
  /services:
    get:
      tags: [Services]
      summary: List all Services
      operationId: listServices
      description: Retrieve paginated list of Services visible to the authenticated user (owned or `shared=true`) with optional filtering.
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: type
          in: query
          schema:
            $ref: '#/components/schemas/ServiceType'
          description: Filter by Service type
        - name: enabled
          in: query
          schema:
            type: boolean
          description: Filter by enabled status
        - name: status
          in: query
          schema:
            $ref: '#/components/schemas/HealthStatus'
          description: Filter by health status
      responses:
        '200':
          description: Services retrieved successfully
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Service'
        '401':
          $ref: '#/components/responses/Unauthorized'

    post:
      tags: [Services]
      summary: Create new Service
      operationId: createService
      description: |
        Create a new Service with async processing. Returns operation ID for status polling.
        
        **Business Rules:**
        - BR-SERVICE-001: Type-protocol compatibility enforced
        - BR-SERVICE-002: Secret requirements validated
        - BR-SERVICE-005: Connection schema must be valid JSON Schema
        - BR-SERVICE-006: Connection schema must align with chosen protocol
      x-sync: false
      x-business-rules:
        - BR-SERVICE-001
        - BR-SERVICE-002
        - BR-SERVICE-005
        - BR-SERVICE-006
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /services/{id}:
    parameters:
      - $ref: '#/components/parameters/ServiceIdParam'
    
    get:
      tags: [Services]
      summary: Get Service by ID
      operationId: getService
      x-sync: true
      responses:
        '200':
          description: Service retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Service'
        '404':
          $ref: '#/components/responses/NotFound'
        '401':
          $ref: '#/components/responses/Unauthorized'
    
    put:
      tags: [Services]
      summary: Update Service
      operationId: updateService
      description: |
        Update Service properties. Returns operation ID for status polling.
        
        **Business Rules:**
        - BR-SERVICE-001: Type-protocol compatibility (type/protocol immutable)
        - BR-SERVICE-005: Connection schema validity
        - BR-SERVICE-006: Connection schema must align with chosen protocol
      x-sync: false
      x-business-rules:
        - BR-SERVICE-001
        - BR-SERVICE-005
        - BR-SERVICE-006
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
    
    delete:
      tags: [Services]
      summary: Delete Service
      operationId: deleteService
      description: |
        Delete Service if no Tools reference it.
        
        **Business Rules:**
        - BR-SERVICE-004: Deletion safety (no Tool references)
      x-sync: false
      x-business-rules:
        - BR-SERVICE-004
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /services/{id}/share:
    parameters:
      - $ref: '#/components/parameters/ServiceIdParam'
    put:
      tags: [Services]
      summary: Toggle Service sharing
      operationId: toggleServiceSharing
      description: |
        Owner-only toggle of `shared`. Returns 409 if attempting to unshare while other users depend on this Service (BR-SHARE-004).
      x-sync: false
      x-business-rules:
        - BR-SHARE-003
        - BR-SHARE-004
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                shared:
                  type: boolean
              required: [shared]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

  /services/{id}/health:
    parameters:
      - $ref: '#/components/parameters/ServiceIdParam'
    
    post:
      tags: [Services]
      summary: Run health check on Service
      operationId: checkServiceHealth
      description: Execute health check and return current status synchronously
      x-sync: true
      responses:
        '200':
          description: Health check completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthCheckResult'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== SERVICE & TOOL TEMPLATES ====================
  
  /service-templates:
    get:
      tags: [ServiceTemplates]
      summary: List Service Templates (owned or shared)
      operationId: listServiceTemplates
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: owned
          in: query
          schema: {type: boolean}
          description: Filter to templates owned by authenticated user
        - name: shared
          in: query
          schema: {type: boolean}
          description: Filter to templates shared by others
        - name: includeArchived
          in: query
          required: false
          schema:
            type: boolean
            default: false
          description: |
            Include archived templates in results. Default: false (only active templates).
      responses:
        '200':
          description: ServiceTemplates retrieved (owner attribution included)
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/ServiceTemplate'
    post:
      tags: [ServiceTemplates]
      summary: Create Service Template
      operationId: createServiceTemplate
      description: Create immutable Service blueprint; ownerId set from auth context.
      x-sync: false
      x-business-rules:
        - BR-TEMPLATE-001
        - BR-SHARE-001
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceTemplateCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /service-templates/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema: {type: string, format: uuid}
    
    get:
      tags: [ServiceTemplates]
      summary: Get Service Template
      operationId: getServiceTemplate
      x-sync: true
      x-business-rules:
        - BR-SHARE-003
      responses:
        '200':
          description: Template retrieved (includes ownerId and shared)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServiceTemplate'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [ServiceTemplates]
      summary: Toggle Service Template sharing
      operationId: toggleServiceTemplateSharing
      description: |
        Owner-only toggle of `shared`. Cannot unshare if other users depend (BR-SHARE-004).
      x-sync: false
      x-business-rules:
        - BR-SHARE-003
        - BR-SHARE-004
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                shared:
                  type: boolean
              required: [shared]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

    delete:
      tags:
        - Templates
      summary: Archive Service Template (soft delete)
      description: |
        Sets archived=true. Template becomes hidden in default listings but
        remains accessible for audit trail and instance provenance display.
        
        **Effects:**
        - Template excluded from GET /service-templates (unless ?includeArchived=true)
        - GET /service-templates/{id} still works (returns archived template)
        - Instance serviceTemplateId references remain valid
        - UI shows "Created from: [Template Name] (archived)"
        - Cannot instantiate new Services from archived template (422)
        
        **No dependency blocking** - instances unaffected by archival.
        Archival is reversible (set archived=false to restore).
        
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '202':
          description: Template archived successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServiceTemplate'
        '404':
          description: Template not found or not owned by requester
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
      x-business-rules:
        - BR-TEMPLATE-001
        - BR-TEMPLATE-002
        - BR-TEMPLATE-006

  /service-templates/{id}/instances:
    get:
      tags:
        - Templates
      summary: List Services instantiated from this Template
      description: |
        Returns Services where serviceTemplateId = {id}.
        Soft reference - templateId field may point to archived template.
        
        Performance: Indexed query on serviceTemplateId.
        
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: includeShared
          in: query
          schema:
            type: boolean
            default: false
          description: |
            If true, includes instances owned by others that are shared with you.
            If false, only your own instances.
            
      responses:
        '200':
          description: Paginated list of Service instances
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Service'
                      metadata:
                        type: object
                        properties:
                          templateName:
                            type: string
                          templateArchived:
                            type: boolean
                          totalInstances:
                            type: integer
                          ownedByYou:
                            type: integer
                          sharedWithYou:
                            type: integer
        '404':
          description: Template not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
      x-business-rules:
        - BR-TEMPLATE-007

  /tool-templates:
    get:
      tags: [ToolTemplates]
      summary: List Tool Templates (owned or shared)
      operationId: listToolTemplates
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: owned
          in: query
          schema: {type: boolean}
          description: Filter to templates owned by authenticated user
        - name: shared
          in: query
          schema: {type: boolean}
          description: Filter to templates shared by others
        - name: includeArchived
          in: query
          required: false
          schema:
            type: boolean
            default: false
          description: |
            Include archived templates in results. Default: false (only active templates).
      responses:
        '200':
          description: ToolTemplates retrieved (owner attribution included)
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/ToolTemplate'
    post:
      tags: [ToolTemplates]
      summary: Create Tool Template
      operationId: createToolTemplate
      description: Create immutable Tool blueprint; ownerId set from auth context.
      x-sync: false
      x-business-rules:
        - BR-TEMPLATE-001
        - BR-SHARE-001
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolTemplateCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /tool-templates/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema: {type: string, format: uuid}
    
    get:
      tags: [ToolTemplates]
      summary: Get Tool Template
      operationId: getToolTemplate
      x-sync: true
      x-business-rules:
        - BR-SHARE-003
      responses:
        '200':
          description: Template retrieved (includes ownerId and shared)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ToolTemplate'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [ToolTemplates]
      summary: Toggle Tool Template sharing
      operationId: toggleToolTemplateSharing
      description: |
        Owner-only toggle of `shared`. Cannot unshare if other users depend (BR-SHARE-004).
      x-sync: false
      x-business-rules:
        - BR-SHARE-003
        - BR-SHARE-004
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                shared:
                  type: boolean
              required: [shared]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

    delete:
      tags:
        - Templates
      summary: Archive Tool Template (soft delete)
      operationId: deleteToolTemplate
      description: |
        Sets archived=true. Template becomes hidden in default listings but
        remains accessible for audit trail and instance provenance display.
        
        **Effects:**
        - Template excluded from GET /tool-templates (unless ?includeArchived=true)
        - GET /tool-templates/{id} still works (returns archived template)
        - Instance toolTemplateId references remain valid
        - UI shows "Created from: [Template Name] (archived)"
        - Cannot instantiate new Tools from archived template (422)
        
        **No dependency blocking** - instances unaffected by archival.
        Archival is reversible (set archived=false to restore).
        
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '202':
          description: Template archived successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ToolTemplate'
        '404':
          description: Template not found or not owned by requester
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
      x-business-rules:
        - BR-TEMPLATE-001
        - BR-TEMPLATE-002
        - BR-TEMPLATE-006

  /tool-templates/{id}/instances:
    get:
      tags:
        - Templates
      summary: List Tools instantiated from this Template
      description: |
        Returns Tools where toolTemplateId = {id}.
        Soft reference - templateId field may point to archived template.
        
        Performance: Indexed query on toolTemplateId.
        
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: includeShared
          in: query
          schema:
            type: boolean
            default: false
          description: |
            If true, includes instances owned by others that are shared with you.
            If false, only your own instances.
            
      responses:
        '200':
          description: Paginated list of Tool instances
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Tool'
                      metadata:
                        type: object
                        properties:
                          templateName:
                            type: string
                          templateArchived:
                            type: boolean
                          totalInstances:
                            type: integer
                          ownedByYou:
                            type: integer
                          sharedWithYou:
                            type: integer
        '404':
          description: Template not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
      x-business-rules:
        - BR-TEMPLATE-007

  # ==================== SECRETS ====================
  
  /secrets:
    get:
      tags: [Secrets]
      summary: List all Secrets (metadata only)
      operationId: listSecrets
      x-sync: true
      description: |
        Returns metadata for Secrets owned by the authenticated user only. Responses are filtered by `userId`; encrypted values are never exposed.
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
      responses:
        '200':
          description: Secrets retrieved (encrypted values never exposed)
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/SecretMetadata'

    post:
      tags: [Secrets]
      summary: Create new Secret
      operationId: createSecret
      description: |
        Create encrypted Secret. Returns operation ID for status polling.
        
        **Business Rules:**
        - BR-SECRET-001: Immutable encryption (write-only)
        - BR-SECRET-002A: User-scoped ownership set from auth context
        - BR-SECRET-003: Secret type must match usage expectations
        
        `userId` is derived from the authenticated token and MUST NOT be supplied in the request body. Encrypted value never appears in responses.
      x-sync: false
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-002A
        - BR-SECRET-003
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SecretCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '409':
          $ref: '#/components/responses/Conflict'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /secrets/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Secrets]
      summary: Get Secret metadata (encrypted value never exposed)
      operationId: getSecret
      x-sync: true
      description: Owner-only lookup. Non-owners receive 404 to avoid leaking existence; encrypted values are never returned.
      responses:
        '200':
          description: Secret metadata retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SecretMetadata'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Secrets]
      summary: Rotate Secret (update encrypted value)
      operationId: rotateSecret
      description: |
        Replace encrypted value with new credentials.
        
        **Business Rules:**
        - BR-SECRET-001: Immutable encryption (rotation only)
        - BR-SECRET-002A: Owner-only rotation (userId from auth)
        - BR-SEC-001: Secret access control (non-owner 404)
      x-sync: false
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-002A
        - BR-SEC-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SecretRotateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'
    
    delete:
      tags: [Secrets]
      summary: Delete Secret
      operationId: deleteSecret
      description: |
        Delete Secret if no Tools reference it.
        
        **Business Rules:**
        - BR-SECRET-002: Deletion safety (no Tool references)
        - BR-SECRET-002A: Owner-only deletion (userId from auth)
        - BR-SEC-001: Secret access control (non-owner 404)
      x-sync: false
      x-business-rules:
        - BR-SECRET-002
        - BR-SECRET-002A
        - BR-SEC-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

  /secrets/{id}/share:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    put:
      tags: [Secrets]
      summary: Toggle Secret sharing (metadata visibility only)
      operationId: toggleSecretSharing
      description: |
        Owner-only toggle of Secret `shared`. Secrets remain owner-only for execution; cross-user use is always forbidden (BR-SHARE-006). Unshare/delete blocked if other users reference the Secret metadata (BR-SHARE-004, BR-SECRET-002).
      x-sync: false
      x-business-rules:
        - BR-SHARE-003
        - BR-SHARE-004
        - BR-SHARE-006
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                shared:
                  type: boolean
              required: [shared]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

  # ==================== TOOLS ====================
  
  /tools:
    get:
      tags: [Tools]
      summary: List all Tools
      operationId: listTools
      description: Retrieve paginated list of Tools visible to the authenticated user (owned or `shared=true`).
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: serviceId
          in: query
          schema:
            type: string
            format: uuid
          description: Filter by Service ID
        - name: enabled
          in: query
          schema:
            type: boolean
          description: Filter by enabled status
      responses:
        '200':
          description: Tools retrieved successfully
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Tool'

    post:
      tags: [Tools]
      summary: Create new Tool
      operationId: createTool
      description: |
        Create a new Tool bound to a Service.
        
        **Business Rules:**
        - BR-TOOL-001: Connection params must conform to Service schema
        - BR-TOOL-002: Input schema must declare all operation variables
        - BR-TOOL-003: Output schema must be valid JSON Schema
        - BR-SECRET-002B: secretId (when required) must belong to the same user as the Tool/Conversation
      x-sync: false
      x-business-rules:
        - BR-TOOL-001
        - BR-TOOL-002
        - BR-TOOL-003
        - BR-SECRET-002B
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /tools/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Tools]
      summary: Get Tool by ID
      operationId: getTool
      x-sync: true
      responses:
        '200':
          description: Tool retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Tool'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Tools]
      summary: Update Tool
      operationId: updateTool
      x-sync: false
      x-business-rules:
        - BR-TOOL-001
        - BR-TOOL-002
        - BR-TOOL-003
        - BR-SECRET-002B
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
    
    delete:
      tags: [Tools]
      summary: Delete Tool
      operationId: deleteTool
      description: |
        Delete Tool if no ProcessSteps reference it.
        
        **Business Rules:**
        - BR-TOOL-004: Deletion safety (no ProcessStep references)
      x-sync: false
      x-business-rules:
        - BR-TOOL-004
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
        '409':
          $ref: '#/components/responses/Conflict'

  /tools/{id}/share:
    put:
      tags:
        - Tools
      summary: Toggle Tool sharing
      description: |
        Updates shared flag. Immediate effect - no blocking, no grace period.
        
        **If unsharing (true → false):**
        - Response includes advisory warning about dependent resources
        - Action completes successfully regardless
        - Dependent Processes remain valid but will fail at execution (BR-EXEC-003)
        
        **Owner controls resources.** System warns but does not block.
        
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - shared
              properties:
                shared:
                  type: boolean
                  description: New sharing state
      responses:
        '200':
          description: |
            Sharing updated successfully. If unsharing and dependencies exist,
            response includes warning metadata for UI display.
          content:
            application/json:
              schema:
                type: object
                required:
                  - id
                  - shared
                  - updatedAt
                properties:
                  id:
                    type: string
                    format: uuid
                  shared:
                    type: boolean
                  warning:
                    type: object
                    nullable: true
                    description: Present when unsharing with dependencies
                    properties:
                      affectedProcessCount:
                        type: integer
                        description: Number of Processes owned by others that reference this Tool
                      affectedUserCount:
                        type: integer
                        description: Number of distinct users who will be affected
                      message:
                        type: string
                        example: "3 Processes owned by 2 users depend on this Tool. They will fail at execution."
                  updatedAt:
                    type: string
                    format: date-time
              example:
                id: "550e8400-e29b-41d4-a716-446655440000"
                shared: false
                warning:
                  affectedProcessCount: 3
                  affectedUserCount: 2
                  message: "3 Processes owned by 2 users depend on this Tool. They will fail at execution."
                updatedAt: "2025-12-04T10:30:00Z"
        '404':
          description: Tool not found or not owned by requester
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      security:
        - bearerAuth: []
      x-business-rules:
        - BR-SHARE-002
        - BR-SHARE-009

  /tools/{id}/test:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Tools]
      summary: Test Tool execution
      operationId: testTool
      description: Execute Tool with sample inputs to validate configuration
      x-sync: false
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                inputs:
                  type: object
                  description: Test input values matching Tool inputSchema
              required: [inputs]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== PROCESSES ====================
  
  /processes:
    get:
      tags: [Processes]
      summary: List all Processes
      operationId: listProcesses
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: enabled
          in: query
          schema:
            type: boolean
          description: Filter by enabled status
      responses:
        '200':
          description: Processes retrieved successfully
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Process'

    post:
      tags: [Processes]
      summary: Create new Process
      operationId: createProcess
      description: |
        Create new workflow Process.
        
        **Business Rules:**
        - BR-PROCESS-001: Must contain at least one ProcessStep
        - BR-PROCESS-002: Step dependencies must be acyclic (DAG)
        - BR-PROCESS-003: Dependencies must reference prior steps
        - BR-PROCESS-004: Parallel steps must be independent
        - BR-PROCESS-005: Output variables must be traceable
        - BR-PROCESS-006: Token budgets must respect Process.tokenBudget
        - BR-PROCESS-009: Enabled Processes may only reference enabled Tools
        - BR-STEP-002: Interpolation expressions may only reference prior context
      x-sync: false
      x-business-rules:
        - BR-PROCESS-001
        - BR-PROCESS-002
        - BR-PROCESS-003
        - BR-PROCESS-004
        - BR-PROCESS-005
        - BR-PROCESS-006
        - BR-PROCESS-009
        - BR-STEP-002
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ProcessCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /processes/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Processes]
      summary: Get Process by ID
      operationId: getProcess
      x-sync: true
      responses:
        '200':
          description: Process retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Process'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Processes]
      summary: Update Process
      operationId: updateProcess
      x-sync: false
      x-business-rules:
        - BR-PROCESS-001
        - BR-PROCESS-002
        - BR-PROCESS-003
        - BR-PROCESS-004
        - BR-PROCESS-005
        - BR-PROCESS-006
        - BR-PROCESS-009
        - BR-STEP-002
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ProcessUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
    
    delete:
      tags: [Processes]
      summary: Delete Process
      operationId: deleteProcess
      description: |
        Delete Process if no Conversations reference it.
        
        **Business Rules:**
        - BR-PROCESS-008: Deletion safety (no Conversation references)
      x-sync: false
      x-business-rules:
        - BR-PROCESS-008
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'

  /processes/{id}/execute:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Processes]
      summary: Execute Process
      operationId: executeProcess
      description: |
        Execute Process workflow with provided inputs.
        
        **Business Rules:**
        - BR-STEP-001: Inputs must conform to Process initialContext requirements
        - BR-EXEC-001: Execution atomicity (all-or-nothing)
      x-sync: false
      x-business-rules:
        - BR-STEP-001
        - BR-EXEC-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                initialContext:
                  type: object
                  description: Input values matching Process initialContext variables
                conversationId:
                  type: string
                  format: uuid
                  description: Optional conversation context for execution
              required: [initialContext]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  # ==================== CONVERSATIONS ====================
  
  /conversations:
    get:
      tags: [Conversations]
      summary: List user's Conversations
      operationId: listConversations
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: status
          in: query
          schema:
            type: string
            enum: [active, archived]
          description: Filter by status
      responses:
        '200':
          description: Conversations retrieved successfully
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Conversation'

    post:
      tags: [Conversations]
      summary: Create new Conversation
      operationId: createConversation
      x-sync: false
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConversationCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'

  /conversations/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Conversations]
      summary: Get Conversation by ID
      operationId: getConversation
      x-sync: true
      responses:
        '200':
          description: Conversation retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Conversation'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Conversations]
      summary: Update Conversation metadata
      operationId: updateConversation
      description: |
        Update title or processId hint. Synchronous because it's metadata-only.
        
        **Business Rules:**
        - BR-CONV-001: ProcessId must reference enabled Process if provided
      x-sync: true
      x-business-rules:
        - BR-CONV-001
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConversationUpdateRequest'
      responses:
        '200':
          description: Conversation updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Conversation'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'
    
  /conversations/{id}/tree:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Conversations]
      summary: Get Conversation tree structure
      operationId: getConversationTree
      description: |
        Retrieve complete Turn tree with alternatives, relationships, and cache status.
        
        **Business Rules:**
        - BR-TURN-014: Cache status derived for all agent alternatives
      x-sync: true
      x-business-rules:
        - BR-TURN-014
      responses:
        '200':
          description: Conversation tree retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConversationTree'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/turns:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Turns]
      summary: Create new Turn in Conversation
      operationId: createTurn
      description: |
        Create new Turn with initial alternative. Creates Episode in Graphiti.
        
        **Business Rules:**
        - BR-TURN-003: Parent Turn validation
        - BR-TURN-009: Alternative input context requirement
        - BR-EPISODE-002: Episode group_id user scoping
      x-sync: false
      x-business-rules:
        - BR-TURN-003
        - BR-TURN-009
        - BR-EPISODE-002
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TurnCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /conversations/{id}/turns/{turnId}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: turnId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Turns]
      summary: Get Turn by ID
      operationId: getTurn
      x-sync: true
      responses:
        '200':
          description: Turn retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConversationTurn'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/turns/{turnId}/fork:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: turnId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Turns]
      summary: Fork Conversation from Turn
      operationId: forkConversation
      description: |
        Create new Conversation branching from specified Turn.
        
        **Business Rules:**
        - BR-CONV-003: Fork integrity (parent/origin references)
      x-sync: false
      x-business-rules:
        - BR-CONV-003
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ForkConversationRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/turns/{turnId}/alternatives:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: turnId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Alternatives]
      summary: Create new alternative for Turn
      operationId: createAlternative
      description: |
        Create new alternative (user edit or agent regeneration).
        
        **Business Rules:**
        - BR-TURN-012: User alternative creation
        - BR-TURN-013: Agent alternative generation
        - BR-ALT-003: Input context immutability
      x-sync: false
      x-business-rules:
        - BR-TURN-012
        - BR-TURN-013
        - BR-ALT-003
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AlternativeCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/turns/{turnId}/alternatives/{altId}/activate:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: turnId
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: altId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    put:
      tags: [Alternatives]
      summary: Activate alternative (UI selection)
      operationId: activateAlternative
      description: |
        Switch active alternative and trigger cascade. Synchronous metadata operation.
        
        **Business Rules:**
        - BR-ALT-002: Active alternative uniqueness and cascade
        - BR-TURN-011: Active alternative switching
      x-sync: true
      x-business-rules:
        - BR-ALT-002
        - BR-TURN-011
      responses:
        '200':
          description: Alternative activated and cascade completed
          content:
            application/json:
              schema:
                type: object
                properties:
                  turnId:
                    type: string
                    format: uuid
                  alternativeId:
                    type: string
                    format: uuid
                  affectedTurns:
                    type: array
                    items:
                      type: object
                      properties:
                        turnId:
                          type: string
                          format: uuid
                        updatedAlternatives:
                          type: array
                          items:
                            type: object
                            properties:
                              id:
                                type: string
                                format: uuid
                              isActive:
                                type: boolean
                              cacheStatus:
                                $ref: '#/components/schemas/CacheStatus'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/turns/{turnId}/alternatives/{altId}/regenerate:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: turnId
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: altId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Alternatives]
      summary: Regenerate alternative response
      operationId: regenerateAlternative
      description: |
        Re-run Process that created this alternative.
        
        **Business Rules:**
        - BR-CONV-001B: Execution uses alternative.processId
        - BR-ALT-004: Lazy regeneration (explicit request)
      x-sync: false
      x-business-rules:
        - BR-CONV-001B
        - BR-ALT-004
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== WORKING MEMORY ====================
  
  /conversations/{id}/working-memory:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [WorkingMemory]
      summary: Get WorkingMemory for Conversation
      operationId: getWorkingMemory
      description: |
        Retrieve current WorkingMemory state with assembled context.
        
        **Business Rules:**
        - BR-MEMORY-002: Immediate path from active alternatives
        - BR-MEMORY-003: Token budget accuracy
      x-sync: true
      x-business-rules:
        - BR-MEMORY-002
        - BR-MEMORY-003
      responses:
        '200':
          description: WorkingMemory retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkingMemory'
        '404':
          $ref: '#/components/responses/NotFound'

  /conversations/{id}/working-memory/compress:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [WorkingMemory]
      summary: Trigger WorkingMemory compression
      operationId: compressWorkingMemory
      description: |
        Manually trigger compression job for WorkingMemory.
        
        **Business Rules:**
        - BR-SUMMARY-003: Compression level calculation
        - BR-SUMMARY-006: Compression counter synchronization
      x-sync: false
      x-business-rules:
        - BR-SUMMARY-003
        - BR-SUMMARY-006
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: false
        content:
          application/json:
            schema:
              type: object
              properties:
                targetCompressionRatio:
                  type: number
                  minimum: 0.1
                  maximum: 0.9
                  default: 0.3
                  description: Target compression ratio (default 0.3)
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== SUMMARIES ====================
  
  /conversations/{id}/summaries:
    parameters:
      - $ref: '#/components/parameters/ConversationIdParam'
    get:
      tags: [Summaries]
      summary: List Summaries in Conversation
      operationId: listSummaries
      description: |
        **Audience:** Public (UI), Admin (debugging)
        **Pattern:** Synchronous read query
        
        Returns all compression Summaries for a Conversation, ordered by priorTurnId sequence.
      x-sync: true
      x-business-rules:
        - BR-SUMMARY-001
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
      responses:
        '200':
          description: Paginated list of Summaries
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Summary'
        '404':
          $ref: '#/components/responses/NotFound'

    post:
      tags: [Summaries]
      summary: Create Summary (Admin Override)
      operationId: createSummary
      description: |
        **Audience:** Admin (emergency repair)
        **Pattern:** Async mutation with event publishing
        
        Manually inject a Summary when automated compression failed or produced incorrect results. Requires pre-created Graphiti Episode.
      x-sync: false
      x-business-rules:
        - BR-SUMMARY-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SummaryCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /conversations/{id}/summaries/{summaryId}:
    parameters:
      - $ref: '#/components/parameters/ConversationIdParam'
      - name: summaryId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    get:
      tags: [Summaries]
      summary: Get Summary by ID
      operationId: getSummary
      description: |
        **Audience:** Public (UI), Admin (debugging)
        **Pattern:** Synchronous read query
      x-sync: true
      x-business-rules:
        - BR-SUMMARY-001
      responses:
        '200':
          description: Summary details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Summary'
        '404':
          $ref: '#/components/responses/NotFound'

    put:
      tags: [Summaries]
      summary: Update Summary (Emergency Repair)
      operationId: updateSummary
      description: |
        **Audience:** Admin (emergency repair)
        **Pattern:** Async mutation with event publishing
        
        Replace Summary's episodeId pointer to corrected Episode content. Original Episode remains in Graphiti for audit trail.
      x-sync: false
      x-business-rules:
        - BR-SUMMARY-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SummaryUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

    delete:
      tags: [Summaries]
      summary: Delete Summary
      operationId: deleteSummary
      description: |
        **Audience:** Admin (repair)
        **Pattern:** Async mutation with event publishing
        
        Remove Summary from Conversation. Worker may trigger recompression if context becomes under-compressed.
      x-sync: false
      x-business-rules:
        - BR-SUMMARY-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== INTROSPECTIONS ====================
  
  /introspections:
    get:
      tags: [Introspections]
      summary: List User's Introspection Carousel
      operationId: listIntrospections
      description: |
        **Audience:** Public (UI), Admin (debugging)
        **Pattern:** Synchronous read query
      x-sync: true
      x-business-rules:
        - BR-INTRO-001
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
      responses:
        '200':
          description: Paginated list of Introspections
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Introspection'

    post:
      tags: [Introspections]
      summary: Create Introspection (Manual Injection)
      operationId: createIntrospection
      description: |
        **Audience:** Public (persona control), Admin (repair)
        **Pattern:** Async mutation with event publishing
      x-sync: false
      x-business-rules:
        - BR-INTRO-001
        - BR-INTRO-003
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IntrospectionCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '409':
          description: Carousel position already occupied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

  /introspections/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    get:
      tags: [Introspections]
      summary: Get Introspection by ID
      operationId: getIntrospection
      description: |
        **Audience:** Public (UI), Admin (debugging)
        **Pattern:** Synchronous read query
      x-sync: true
      x-business-rules:
        - BR-INTRO-001
      responses:
        '200':
          description: Introspection details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Introspection'
        '404':
          $ref: '#/components/responses/NotFound'

    put:
      tags: [Introspections]
      summary: Update Introspection (Persona Correction)
      operationId: updateIntrospection
      description: |
        **Audience:** Public (persona control), Admin (repair)
        **Pattern:** Async mutation with event publishing
      x-sync: false
      x-business-rules:
        - BR-INTRO-001
        - BR-INTRO-003
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IntrospectionUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/BusinessRuleViolation'

    delete:
      tags: [Introspections]
      summary: Delete Introspection
      operationId: deleteIntrospection
      description: |
        **Audience:** Public (persona control), Admin (repair)
        **Pattern:** Async mutation with event publishing
      x-sync: false
      x-business-rules:
        - BR-INTRO-001
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== ENTITIES ====================
  
  /entities:
    get:
      tags: [Entities]
      summary: Search/list Entities
      operationId: listEntities
      x-sync: true
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: query
          in: query
          schema:
            type: string
          description: Semantic search query
        - name: category
          in: query
          schema:
            type: string
          description: Filter by entity category
        - name: conversationId
          in: query
          schema:
            type: string
            format: uuid
          description: Filter by Conversation activeEntities
      responses:
        '200':
          description: Entities retrieved successfully
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/PaginatedResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items:
                          $ref: '#/components/schemas/Entity'

    post:
      tags: [Entities]
      summary: Create user Entity
      operationId: createEntity
      description: |
        Create user-defined Entity with immediate availability.
        
        **Business Rules:**
        - BR-ENTITY-002: User creation requirements
        - BR-ENTITY-006: Immediate availability in Conversation
        - BR-ENTITY-008: User scope isolation
      x-sync: false
      x-business-rules:
        - BR-ENTITY-002
        - BR-ENTITY-006
        - BR-ENTITY-008
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EntityCreateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'

  /entities/{uuid}:
    parameters:
      - name: uuid
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Entities]
      summary: Get Entity by UUID
      operationId: getEntity
      x-sync: true
      responses:
        '200':
          description: Entity retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Entity'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Entities]
      summary: Update Entity
      operationId: updateEntity
      description: |
        Update Entity metadata. Syncs to Graphiti.
        
        **Business Rules:**
        - BR-ENTITY-004: Enrichment append-only
        - BR-ENTITY-005: Category stability
      x-sync: false
      x-business-rules:
        - BR-ENTITY-004
        - BR-ENTITY-005
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EntityUpdateRequest'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          $ref: '#/components/responses/NotFound'
    
    delete:
      tags: [Entities]
      summary: Delete Entity
      operationId: deleteEntity
      description: Delete Entity from Graphiti (managed by Graphiti lifecycle)
      x-sync: false
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== OPERATIONS ====================
  
  /operations/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Operations]
      summary: Poll operation status
      operationId: getOperation
      x-sync: true
      responses:
        '200':
          description: Operation status retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OperationStatus'
        '404':
          $ref: '#/components/responses/NotFound'

  /operations/{id}/cancel:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    post:
      tags: [Operations]
      summary: Cancel operation
      operationId: cancelOperation
      x-sync: false
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== WORKERS (Admin/Debug) ====================
  
  /workers:
    get:
      tags: [Workers]
      summary: List workers
      operationId: listWorkers
      x-sync: true
      parameters:
        - name: type
          in: query
          schema:
            type: string
          description: Filter by worker type
        - name: status
          in: query
          schema:
            type: string
            enum: [idle, busy, offline]
          description: Filter by status
      responses:
        '200':
          description: Workers retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  workers:
                    type: array
                    items:
                      $ref: '#/components/schemas/Worker'

  /workers/{type}/jobs:
    parameters:
      - name: type
        in: path
        required: true
        schema:
          type: string
    
    post:
      tags: [Workers]
      summary: Submit worker job
      operationId: submitWorkerJob
      x-sync: false
      parameters:
        - $ref: '#/components/parameters/IdempotencyKeyHeader'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                input:
                  type: object
                  description: Job-specific input data
                priority:
                  type: string
                  enum: [normal, high, urgent]
                  default: normal
              required: [input]
      responses:
        '202':
          $ref: '#/components/responses/AsyncAccepted'
        '400':
          $ref: '#/components/responses/ValidationError'

  /workers/{type}/jobs/{id}:
    parameters:
      - name: type
        in: path
        required: true
        schema:
          type: string
      - name: id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    
    get:
      tags: [Workers]
      summary: Poll job status
      operationId: getWorkerJob
      x-sync: true
      responses:
        '200':
          description: Job status retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkerJobStatus'
        '404':
          $ref: '#/components/responses/NotFound'

  # ==================== HEALTH ====================
  
  /health:
    get:
      tags: [Health]
      summary: System health check
      operationId: healthCheck
      security: []
      x-sync: true
      responses:
        '200':
          description: System is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthCheckResult'

  /health/live:
    get:
      tags: [Health]
      summary: Liveness probe
      operationId: livenessCheck
      security: []
      x-sync: true
      responses:
        '200':
          description: Process is running

  /health/ready:
    get:
      tags: [Health]
      summary: Readiness probe
      operationId: readinessCheck
      security: []
      x-sync: true
      responses:
        '200':
          description: Ready to serve traffic

  /metrics:
    get:
      tags: [Health]
      summary: Prometheus metrics
      operationId: getMetrics
      security: []
      x-sync: true
      responses:
        '200':
          description: Metrics in Prometheus format
          content:
            text/plain:
              schema:
                type: string

# ==================== COMPONENTS ====================

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  parameters:
    ServiceIdParam:
      name: id
      in: path
      required: true
      schema:
        type: string
        format: uuid
      description: Service unique identifier
    
    PageParam:
      name: page
      in: query
      schema:
        type: integer
        minimum: 1
        default: 1
      description: Page number (1-indexed)
    
    LimitParam:
      name: limit
      in: query
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20
      description: Items per page (max 100)
    
    IdempotencyKeyHeader:
      name: Idempotency-Key
      in: header
      required: true
      schema:
        type: string
        format: uuid
      description: Client-generated UUID for idempotent operations
    
    ConversationIdParam:
      name: id
      in: path
      required: true
      schema:
        type: string
        format: uuid
      description: Conversation unique identifier

  responses:
    AsyncAccepted:
      description: Operation accepted for async processing
      headers:
        X-Correlation-ID:
          schema:
            type: string
            format: uuid
          description: Correlation ID for distributed tracing
      content:
        application/json:
          schema:
            type: object
            properties:
              operationId:
                type: string
                format: uuid
                description: ID for polling operation status
              statusUrl:
                type: string
                format: uri
                description: URL to poll for status
              message:
                type: string
                description: Human-readable status message
            required: [operationId, statusUrl]
    
    ValidationError:
      description: Request validation failed
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    
    BusinessRuleViolation:
      description: Business rule violated
      content:
        application/json:
          schema:
            allOf:
              - $ref: '#/components/schemas/ErrorResponse'
              - type: object
                properties:
                  violatedRule:
                    type: string
                    description: Business rule ID (BR-XXX-NNN)
                    example: BR-SERVICE-001
    
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    
    Unauthorized:
      description: Authentication required or failed
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    
    Conflict:
      description: Resource conflict (e.g., deletion safety violation)
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

  schemas:
    # ==================== CORE TYPES ====================
    
    ServiceType:
      type: string
      enum: [neo4j_graph, rest_api, llm_provider, mcp_server]
      description: Type of infrastructure service
    
    Protocol:
      type: string
      enum: [bolt, bolt+s, http, https, stdio, sse]
      description: Connection protocol
    
    HealthStatus:
      type: string
      enum: [healthy, degraded, down]
      description: Health status indicator
    
    CacheStatus:
      type: string
      enum: [valid, stale, generating]
      description: Alternative cache validity status
      x-business-rule: BR-TURN-014
    
    Speaker:
      type: string
      enum: [user, agent, system]
      description: Turn speaker type
    
    TurnType:
      type: string
      enum: [message, tool_result, summary]
      description: Turn content type
    
    ConversationStatus:
      type: string
      enum: [active, archived]
      description: Conversation lifecycle status

    # ==================== ERROR HANDLING ====================
    
    ErrorResponse:
      type: object
      properties:
        code:
          type: string
          description: Machine-readable error code
          example: VALIDATION_ERROR
        message:
          type: string
          description: Human-readable error message
        correlationId:
          type: string
          format: uuid
          description: Correlation ID for support/debugging
        timestamp:
          type: string
          format: date-time
          description: When error occurred (ISO 8601)
        details:
          type: object
          description: Additional error context
          properties:
            field:
              type: string
              description: Field that failed validation
            rule:
              type: string
              description: Business rule violated (BR-XXX-NNN)
            retryable:
              type: boolean
              description: Whether client can retry
            retryAfter:
              type: integer
              description: Seconds to wait before retry
      required: [code, message, correlationId, timestamp]

    # ==================== PAGINATION ====================
    
    PaginatedResponse:
      type: object
      properties:
        data:
          type: array
          description: Page of results
        pagination:
          type: object
          properties:
            page:
              type: integer
              minimum: 1
            limit:
              type: integer
              minimum: 1
              maximum: 100
            total:
              type: integer
              description: Total items across all pages
            totalPages:
              type: integer
          description: Total number of pages
        hasNext:
          type: boolean
        hasPrev:
          type: boolean
      required: [page, limit, total, totalPages, hasNext, hasPrev]
  required: [data, pagination]

  # ==================== TEMPLATES ====================
  
  ServiceTemplate:
    type: object
    properties:
      id:
        type: string
        format: uuid
        readOnly: true
      ownerId:
        type: string
        format: uuid
        readOnly: true
      name:
        type: string
        minLength: 1
      description:
        type: string
        nullable: true
      type:
        $ref: '#/components/schemas/ServiceType'
      protocol:
        $ref: '#/components/schemas/Protocol'
      connectionSchema:
        type: object
      requiresSecret:
        type: boolean
      shared:
        type: boolean
        default: false
      archived:
        type: boolean
        default: false
        description: |
          Soft delete flag. Archived templates excluded from default listings
          but remain accessible via direct GET and ?includeArchived=true filter.
      createdAt:
        type: string
        format: date-time
        readOnly: true
      updatedAt:
        type: string
        format: date-time
        readOnly: true
    required: [id, ownerId, name, type, protocol, connectionSchema, requiresSecret, shared, archived, createdAt, updatedAt]
    x-business-rules:
      - BR-TEMPLATE-001
      - BR-SHARE-001
      - BR-SHARE-002

  ServiceTemplateCreateRequest:
    type: object
    properties:
      name:
        type: string
        minLength: 1
      description:
        type: string
      type:
        $ref: '#/components/schemas/ServiceType'
      protocol:
        $ref: '#/components/schemas/Protocol'
      connectionSchema:
        type: object
      requiresSecret:
        type: boolean
        default: false
    required: [name, type, protocol, connectionSchema]
    x-business-rules:
      - BR-TEMPLATE-001

  ToolTemplate:
    type: object
    properties:
      id:
        type: string
        format: uuid
        readOnly: true
      ownerId:
        type: string
        format: uuid
        readOnly: true
      name:
        type: string
        minLength: 1
      description:
        type: string
        nullable: true
      operation:
        type: object
      inputSchema:
        type: object
      outputSchema:
        type: object
      shared:
        type: boolean
        default: false
      archived:
        type: boolean
        default: false
        description: |
          Soft delete flag. Archived templates excluded from default listings
          but remain accessible via direct GET and ?includeArchived=true filter.
      createdAt:
        type: string
        format: date-time
        readOnly: true
      updatedAt:
        type: string
        format: date-time
        readOnly: true
    required: [id, ownerId, name, operation, inputSchema, outputSchema, shared, archived, createdAt, updatedAt]
    x-business-rules:
      - BR-TEMPLATE-001
      - BR-SHARE-001
      - BR-SHARE-002

  ToolTemplateCreateRequest:
    type: object
    properties:
      name:
        type: string
        minLength: 1
      description:
        type: string
      operation:
        type: object
      inputSchema:
        type: object
      outputSchema:
        type: object
    required: [name, operation, inputSchema, outputSchema]
    x-business-rules:
      - BR-TEMPLATE-001

  # ==================== SERVICES ====================
    
    Service:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        ownerId:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        name:
          type: string
          minLength: 1
          maxLength: 100
          x-mutable: true
        type:
          $ref: '#/components/schemas/ServiceType'
          x-immutable: true
          x-business-rule: BR-SERVICE-001
        protocol:
          $ref: '#/components/schemas/Protocol'
          x-immutable: true
          x-business-rule: BR-SERVICE-001
        connectionSchema:
          type: object
          description: JSON Schema defining connection parameters
          x-mutable: true
          x-business-rule: BR-SERVICE-005
        requiresSecret:
          type: boolean
          x-immutable: true
          x-business-rule: BR-SERVICE-002
        serviceTemplateId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-immutable: true
          description: |
            Audit trail only. Records which ServiceTemplate this Service was instantiated from.
            NOT an operational dependency—Service contains complete copied structure and functions
            independently whether template exists or is archived. Soft reference may point to 
            archived template (UI displays gracefully).
          x-business-rules:
            - BR-TEMPLATE-001
            - BR-TEMPLATE-002
        shared:
          type: boolean
          default: false
          x-mutable: true
        enabled:
          type: boolean
          x-mutable: true
        status:
          $ref: '#/components/schemas/HealthStatus'
          readOnly: true
          x-business-rule: BR-SERVICE-003
        lastHealthCheck:
          type: string
          format: date-time
          readOnly: true
        errorMessage:
          type: string
          nullable: true
          readOnly: true
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true
      required: [id, ownerId, name, type, protocol, connectionSchema, requiresSecret, shared, enabled, status, createdAt, updatedAt]
      x-business-rules:
        - BR-SHARE-005
        - BR-SHARE-006
    
    ServiceCreateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        type:
          $ref: '#/components/schemas/ServiceType'
        protocol:
          $ref: '#/components/schemas/Protocol'
        connectionSchema:
          type: object
          description: Valid JSON Schema object
        requiresSecret:
          type: boolean
          default: false
        serviceTemplateId:
          type: string
          format: uuid
          nullable: true
          description: Optional template origin (immutable once set)
      required: [name, type, protocol, connectionSchema]
      x-business-rules:
        - BR-SERVICE-001
        - BR-SERVICE-002
        - BR-SERVICE-005
    
    ServiceUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        connectionSchema:
          type: object
          description: Valid JSON Schema object
        enabled:
          type: boolean
      minProperties: 1

    # ==================== SECRETS ====================
    
    SecretMetadata:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        userId:
          type: string
          format: uuid
          description: Immutable owner set from authenticated context
          readOnly: true
        name:
          type: string
        type:
          type: string
          enum: [api_key, oauth_token, password, certificate]
          x-immutable: true
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true
        shared:
          type: boolean
          default: false
          description: Shared flag does not grant cross-user execution; Secrets remain owner-only.
      required: [id, userId, name, type, shared, createdAt, updatedAt]
      description: Secret metadata (encrypted value never exposed); ownership enforced via userId, immutable after creation; Secrets are not executable cross-user even if marked shared.
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-002A
        - BR-SEC-001
    
    SecretCreateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        type:
          type: string
          enum: [api_key, oauth_token, password, certificate]
        value:
          type: string
          minLength: 1
          description: Plaintext value (will be encrypted)
          writeOnly: true
      required: [name, type, value]
      description: Secret creation request; `userId` is injected from auth context and MUST NOT be supplied by client.
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-002A
        - BR-SECRET-003
    
    SecretRotateRequest:
      type: object
      properties:
        value:
          type: string
          minLength: 1
          description: New plaintext value (will be encrypted)
          writeOnly: true
      required: [value]
      description: Rotate encrypted value for an existing Secret owned by the authenticated user.
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-002A
        - BR-SEC-001

    # ==================== TOOLS ====================
    
    Tool:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        ownerId:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        name:
          type: string
        serviceId:
          type: string
          format: uuid
          x-immutable: true
        connectionParams:
          type: object
          description: Conforms to Service connectionSchema; if `secretId` is present it MUST belong to the same user as the Tool and Conversation (owner-aligned credential use).
          x-business-rules:
            - BR-TOOL-001
            - BR-SECRET-002B
        operation:
          type: object
          description: Operation definition (discriminated by Service type)
        inputSchema:
          type: object
          description: JSON Schema for operation inputs
          x-business-rule: BR-TOOL-002
        outputSchema:
          type: object
          description: JSON Schema for operation outputs
          x-business-rule: BR-TOOL-003
        toolTemplateId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-immutable: true
          description: |
            Audit trail only. Records which ToolTemplate this Tool was instantiated from.
            NOT an operational dependency—Tool contains complete copied structure and functions
            independently whether template exists or is archived. Soft reference may point to 
            archived template (UI displays gracefully).
          x-business-rules:
            - BR-TEMPLATE-001
            - BR-TEMPLATE-002
        shared:
          type: boolean
          default: false
          x-mutable: true
        enabled:
          type: boolean
        status:
          $ref: '#/components/schemas/HealthStatus'
          readOnly: true
          x-business-rule: BR-TOOL-009
        lastHealthCheck:
          type: string
          format: date-time
          readOnly: true
        errorMessage:
          type: string
          nullable: true
          readOnly: true
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true
      required: [id, ownerId, name, serviceId, connectionParams, operation, inputSchema, outputSchema, shared, enabled, status, createdAt, updatedAt]
    
    ToolCreateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
        serviceId:
          type: string
          format: uuid
        connectionParams:
          type: object
          description: Conforms to Service connectionSchema; if `secretId` is present it MUST belong to the same user as the Tool and Conversation (BR-TOOL-001, BR-SECRET-002B).
        operation:
          type: object
        inputSchema:
          type: object
        outputSchema:
          type: object
        toolTemplateId:
          type: string
          format: uuid
          nullable: true
          description: Optional template origin (immutable once set)
      required: [name, serviceId, connectionParams, operation, inputSchema, outputSchema]
    
    ToolUpdateRequest:
      type: object
      properties:
        name:
          type: string
        connectionParams:
          type: object
          description: Conforms to Service connectionSchema; if `secretId` is present it MUST belong to the same user as the Tool and Conversation (BR-TOOL-001, BR-SECRET-002B).
        operation:
          type: object
        inputSchema:
          type: object
        outputSchema:
          type: object
        enabled:
          type: boolean
      minProperties: 1

    # ==================== PROCESSES ====================
    
    Process:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        name:
          type: string
        description:
          type: string
        ownerId:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
          description: |
            User who owns this Process. Set from authenticated context during
            creation. Determines which Tools this Process may reference.
          x-business-rules:
            - BR-PROCESS-010
        initialContext:
          type: array
          items:
            type: string
          description: Required input variable names
        steps:
          type: array
          items:
            $ref: '#/components/schemas/ProcessStep'
          minItems: 1
          x-business-rule: BR-PROCESS-001
        outputTemplate:
          type: string
          description: Handlebars-style template
        tokenBudget:
          type: integer
          minimum: 1
          nullable: true
        maxRecursionDepth:
          type: integer
          minimum: 1
          maximum: 10
          default: 3
          x-business-rule: BR-PROCESS-007
        enabled:
          type: boolean
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true
      required: [id, name, ownerId, initialContext, steps, outputTemplate, enabled, createdAt, updatedAt]
    
    ProcessStep:
      type: object
      properties:
        id:
          type: string
        toolId:
          type: string
          format: uuid
          nullable: true
          x-business-rule: BR-STEP-007
        processId:
          type: string
          format: uuid
          nullable: true
          x-business-rule: BR-STEP-007
        inputs:
          type: object
          description: Parameter → interpolation expression map
          x-business-rule: BR-STEP-001
        output:
          type: object
          properties:
            variable:
              type: string
            tokenBudget:
              type: integer
              minimum: 1
              nullable: true
            required:
              type: boolean
              x-business-rule: BR-STEP-004
          required: [variable, required]
        execution:
          type: object
          properties:
            mode:
              type: string
              enum: [parallel, sequential]
              default: sequential
            condition:
              type: string
              nullable: true
              description: JavaScript boolean expression
              x-business-rule: BR-STEP-003
            dependsOn:
              type: array
              items:
                type: string
              x-business-rule: BR-PROCESS-002
            timeout:
              type: integer
              minimum: 1
              maximum: 300
              nullable: true
              x-business-rule: BR-STEP-005
            interactionMode:
              type: string
              enum: [auto, manual]
              default: auto
              x-business-rule: BR-STEP-006
          required: [mode]
      required: [id, inputs, output, execution]
      x-business-rules:
        - BR-STEP-007
    
    ProcessCreateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
        description:
          type: string
        initialContext:
          type: array
          items:
            type: string
        steps:
          type: array
          items:
            $ref: '#/components/schemas/ProcessStep'
          minItems: 1
        outputTemplate:
          type: string
        tokenBudget:
          type: integer
          minimum: 1
        maxRecursionDepth:
          type: integer
          minimum: 1
          maximum: 10
          default: 3
      required: [name, initialContext, steps, outputTemplate]
    
    ProcessUpdateRequest:
      type: object
      properties:
        name:
          type: string
        description:
          type: string
        steps:
          type: array
          items:
            $ref: '#/components/schemas/ProcessStep'
          minItems: 1
        outputTemplate:
          type: string
        tokenBudget:
          type: integer
          minimum: 1
        maxRecursionDepth:
          type: integer
          minimum: 1
          maximum: 10
        enabled:
          type: boolean
      minProperties: 1

    # ==================== CONVERSATIONS ====================
    
    Conversation:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        title:
          type: string
          nullable: true
        userId:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        processId:
          type: string
          format: uuid
          nullable: true
          description: UI hint for preferred Process
          x-business-rule: BR-CONV-001
        status:
          $ref: '#/components/schemas/ConversationStatus'
        activeEntities:
          type: array
          items:
            type: string
            format: uuid
          description: Graphiti Entity UUIDs currently relevant
          x-business-rule: BR-CONV-004
        parentConversationId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-immutable: true
        forkOriginTurnId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-immutable: true
        forkOriginAlternativeId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-immutable: true
          x-business-rule: BR-CONV-003
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true
      required: [id, userId, status, activeEntities, createdAt, updatedAt]
    
    ConversationCreateRequest:
      type: object
      properties:
        title:
          type: string
        processId:
          type: string
          format: uuid
      required: []
    
    ConversationUpdateRequest:
      type: object
      properties:
        title:
          type: string
        processId:
          type: string
          format: uuid
          nullable: true
      minProperties: 1

    # ==================== TURNS & ALTERNATIVES ====================
    
    ConversationTurn:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        conversationId:
          type: string
          format: uuid
          readOnly: true
          x-immutable: true
        parentTurnId:
          type: string
          format: uuid
          nullable: true
          readOnly: true
          x-business-rule: BR-TURN-003
        sequence:
          type: integer
          minimum: 1
          readOnly: true
          x-business-rule: BR-TURN-004
        speaker:
          $ref: '#/components/schemas/Speaker'
          x-business-rule: BR-TURN-005
        turnType:
          $ref: '#/components/schemas/TurnType'
          x-business-rule: BR-TURN-005
        content:
          type: string
          readOnly: true
          description: Permanent storage (never deleted)
          x-immutable: true
          x-business-rule: BR-TURN-EPISODE-001
        alternatives:
          type: array
          items:
            $ref: '#/components/schemas/Alternative'
          minItems: 1
          x-business-rule: BR-TURN-008
        timestamp:
          type: string
          format: date-time
          readOnly: true
          x-immutable: true
      required: [id, conversationId, sequence, speaker, turnType, content, alternatives, timestamp]
      x-business-rule: BR-TURN-001
    
    Alternative:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        episodeId:
          type: string
          format: uuid
          nullable: true
          x-business-rule: BR-TURN-006
        processId:
          type: string
          format: uuid
          nullable: true
          description: Process that created this (agent only)
          x-immutable: true
          x-business-rule: BR-TURN-007
        createdAt:
          type: string
          format: date-time
          readOnly: true
        isActive:
          type: boolean
          x-business-rule: BR-ALT-002
        inputContext:
          type: object
          properties:
            parentAlternativeId:
              type: string
              format: uuid
              nullable: true
              x-immutable: true
              x-business-rule: BR-TURN-009
          required: [parentAlternativeId]
          x-business-rule: BR-ALT-003
        hasChildren:
          type: boolean
          readOnly: true
          description: Computed from child Turn references
        cacheStatus:
          $ref: '#/components/schemas/CacheStatus'
          readOnly: true
          x-business-rule: BR-TURN-014
      required: [id, createdAt, isActive, inputContext]
    
    TurnCreateRequest:
      type: object
      properties:
        parentTurnId:
          type: string
          format: uuid
          nullable: true
        parentAlternativeId:
          type: string
          format: uuid
          nullable: true
          description: Required if parentTurnId provided
        speaker:
          $ref: '#/components/schemas/Speaker'
        content:
          type: string
        processId:
          type: string
          format: uuid
          nullable: true
          description: Process for agent turns
      required: [speaker, content]
    
    AlternativeCreateRequest:
      type: object
      properties:
        content:
          type: string
          description: For user alternatives (edits)
        processId:
          type: string
          format: uuid
          description: For agent alternatives (regeneration)
        makeActive:
          type: boolean
          default: false
          description: Whether to make this alternative active
      minProperties: 1
    
    ForkConversationRequest:
      type: object
      properties:
        title:
          type: string
        alternativeId:
          type: string
          format: uuid
          description: Which alternative in fork origin Turn
        copyActiveEntities:
          type: boolean
          default: true
      required: [alternativeId]
    
    ConversationTree:
      type: object
      properties:
        conversationId:
          type: string
          format: uuid
        turns:
          type: array
          items:
            $ref: '#/components/schemas/ConversationTurn'
        relationships:
          type: array
          items:
            type: object
            properties:
              childId:
                type: string
                format: uuid
              parentId:
                type: string
                format: uuid
              parentAlternativeId:
                type: string
                format: uuid
            required: [childId, parentId, parentAlternativeId]
      required: [conversationId, turns, relationships]

    # ==================== WORKING MEMORY ====================
    
    WorkingMemory:
      type: object
      properties:
        conversationId:
          type: string
          format: uuid
        currentTurnId:
          type: string
          format: uuid
        currentAlternativeId:
          type: string
          format: uuid
        immediatePath:
          type: array
          items:
            type: object
            properties:
              turnId:
                type: string
                format: uuid
              alternativeId:
                type: string
                format: uuid
              episodeId:
                type: string
                format: uuid
            required: [turnId, alternativeId, episodeId]
          x-business-rule: BR-MEMORY-002
        summaries:
          type: array
          items:
            type: string
            format: uuid
          description: Summary IDs
        activeEntities:
          type: array
          items:
            $ref: '#/components/schemas/EntityReference'
        introspectionContext:
          type: array
          items:
            type: string
            format: uuid
          description: Introspection Episode UUIDs (user-scoped)
        totalTokens:
          type: integer
          minimum: 0
          x-business-rule: BR-MEMORY-003
        lastUpdated:
          type: string
          format: date-time
      required: [conversationId, currentTurnId, currentAlternativeId, immediatePath, summaries, activeEntities, introspectionContext, totalTokens, lastUpdated]
    
    EntityReference:
      type: object
      properties:
        entityUuid:
          type: string
          format: uuid
        name:
          type: string
        category:
          type: string
        relevanceScore:
          type: number
          minimum: 0
          maximum: 1
        source:
          type: string
          enum: [user, graphiti, enrichment]
        addedAt:
          type: string
          format: date-time
        includeSummary:
          type: boolean
        includeFacets:
          type: boolean
        includeRelationships:
          type: boolean
      required: [entityUuid, name, category, relevanceScore, source, addedAt, includeSummary, includeFacets, includeRelationships]

    # ==================== SUMMARY SCHEMAS ====================
    
    Summary:
      type: object
      description: Compression artifact containing condensed conversation history
      properties:
        id:
          type: string
          format: uuid
          x-immutable: true
        conversationId:
          type: string
          format: uuid
          x-immutable: true
        episodeId:
          type: string
          format: uuid
          description: Graphiti Episode UUID containing summary content
        sourceEpisodeIds:
          type: array
          items:
            type: string
            format: uuid
          x-immutable: true
          description: Episode UUIDs compressed into this Summary (Turn or lower-level Summary Episodes)
        compressionLevel:
          type: integer
          minimum: 0
          x-immutable: true
          description: Compression depth (`max(sourceEpisodes.compressionLevel) + 1`)
        priorTurnId:
          type: string
          format: uuid
          x-immutable: true
          description: Last Turn included in this summary
        tokenCount:
          type: integer
          minimum: 0
        createdAt:
          type: string
          format: date-time
          x-immutable: true
        createdBy:
          type: string
          enum: [worker, admin]
          x-immutable: true
        updatedAt:
          type: string
          format: date-time
          nullable: true
      required: [id, conversationId, episodeId, sourceEpisodeIds, compressionLevel, priorTurnId, tokenCount, createdAt, createdBy]

    SummaryCreateRequest:
      type: object
      description: Request to manually create a Summary (admin override)
      properties:
        episodeId:
          type: string
          format: uuid
        sourceEpisodeIds:
          type: array
          items:
            type: string
            format: uuid
          minItems: 1
        compressionLevel:
          type: integer
          minimum: 0
        priorTurnId:
          type: string
          format: uuid
        tokenCount:
          type: integer
          minimum: 0
      required: [episodeId, sourceEpisodeIds, compressionLevel, priorTurnId, tokenCount]

    SummaryUpdateRequest:
      type: object
      description: Request to update Summary's Episode pointer (emergency repair)
      properties:
        episodeId:
          type: string
          format: uuid
        tokenCount:
          type: integer
          minimum: 0
      required: [episodeId]

    # ==================== INTROSPECTION SCHEMAS ====================

    Introspection:
      type: object
      description: Agent reflection/persona component in user's carousel
      properties:
        id:
          type: string
          format: uuid
          x-immutable: true
        userId:
          type: string
          format: uuid
          x-immutable: true
        episodeId:
          type: string
          format: uuid
        position:
          type: integer
          minimum: 0
          maximum: 9
          x-immutable: true
        tokenCount:
          type: integer
          minimum: 0
        createdAt:
          type: string
          format: date-time
          x-immutable: true
        createdBy:
          type: string
          enum: [worker, user]
          x-immutable: true
        updatedAt:
          type: string
          format: date-time
          nullable: true
      required: [id, userId, episodeId, position, tokenCount, createdAt, createdBy]

    IntrospectionCreateRequest:
      type: object
      description: Request to manually inject an Introspection
      properties:
        episodeId:
          type: string
          format: uuid
        position:
          type: integer
          minimum: 0
          maximum: 9
        tokenCount:
          type: integer
          minimum: 0
      required: [episodeId, position, tokenCount]

    IntrospectionUpdateRequest:
      type: object
      description: Request to update Introspection's Episode pointer (persona correction)
      properties:
        episodeId:
          type: string
          format: uuid
        tokenCount:
          type: integer
          minimum: 0
      required: [episodeId]

    # ==================== ENTITIES ====================
    
    Entity:
      type: object
      properties:
        uuid:
          type: string
          format: uuid
          readOnly: true
        name:
          type: string
        entity_type:
          type: string
          nullable: true
        summary:
          type: string
        sources:
          type: array
          items:
            type: object
            properties:
              type:
                type: string
                enum: [user, graphiti, enrichment]
              created_at:
                type: string
                format: date-time
              created_by:
                type: string
                format: uuid
                nullable: true
              episode_id:
                type: string
                format: uuid
                nullable: true
              original_name:
                type: string
                nullable: true
              confidence:
                type: number
                minimum: 0
                maximum: 1
                nullable: true
          x-business-rule: BR-ENTITY-001
        facets:
          type: object
          nullable: true
          description: Type-specific metadata dimensions
        enrichment:
          type: object
          nullable: true
        enriched_at:
          type: string
          format: date-time
          nullable: true
        enriched_by:
          type: string
          format: uuid
          nullable: true
        created_at:
          type: string
          format: date-time
          readOnly: true
        valid_at:
          type: string
          format: date-time
          readOnly: true
        group_id:
          type: string
          format: uuid
          readOnly: true
          description: User ID (user scope isolation)
          x-business-rule: BR-ENTITY-008
      required: [uuid, name, summary, sources, created_at, valid_at, group_id]
    
    EntityCreateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
        category:
          type: string
          enum: [Person, Organization, Project, Concept, Object, Event, Place]
        summary:
          type: string
          minLength: 1
        conversationId:
          type: string
          format: uuid
          description: Add to this Conversation's activeEntities
      required: [name, summary]
      x-business-rule: BR-ENTITY-002
    
    EntityUpdateRequest:
      type: object
      properties:
        name:
          type: string
        category:
          type: string
        summary:
          type: string
        facets:
          type: object
      minProperties: 1

    # ==================== OPERATIONS ====================
    
    OperationStatus:
      type: object
      properties:
        operationId:
          type: string
          format: uuid
        status:
          type: string
          enum: [queued, processing, completed, failed]
        progress:
          type: integer
          minimum: 0
          maximum: 100
          nullable: true
        result:
          type: object
          nullable: true
          description: Operation result (if completed)
        error:
          $ref: '#/components/schemas/ErrorResponse'
          nullable: true
        startedAt:
          type: string
          format: date-time
          nullable: true
        completedAt:
          type: string
          format: date-time
          nullable: true
      required: [operationId, status]

    # ==================== WORKERS ====================
    
    Worker:
      type: object
      properties:
        id:
          type: string
          format: uuid
        type:
          type: string
        status:
          type: string
          enum: [idle, busy, offline]
        currentJobId:
          type: string
          format: uuid
          nullable: true
        lastHeartbeat:
          type: string
          format: date-time
        processedCount:
          type: integer
          minimum: 0
        errorCount:
          type: integer
          minimum: 0
        createdAt:
          type: string
          format: date-time
      required: [id, type, status, lastHeartbeat, processedCount, errorCount, createdAt]
    
    WorkerJobStatus:
      type: object
      properties:
        jobId:
          type: string
          format: uuid
        status:
          type: string
          enum: [queued, processing, completed, failed]
        progress:
          type: integer
          minimum: 0
          maximum: 100
        result:
          type: object
          nullable: true
        error:
          $ref: '#/components/schemas/ErrorResponse'
          nullable: true
        startedAt:
          type: string
          format: date-time
          nullable: true
        completedAt:
          type: string
          format: date-time
          nullable: true
      required: [jobId, status]

    # ==================== HEALTH ====================
    
    HealthCheckResult:
      type: object
      properties:
        status:
          $ref: '#/components/schemas/HealthStatus'
        timestamp:
          type: string
          format: date-time
        dependencies:
          type: object
          additionalProperties:
            $ref: '#/components/schemas/HealthStatus'
          description: Health status of dependent services
        errorMessage:
          type: string
          nullable: true
      required: [status, timestamp]

# ==================== ERROR CODES (SHARING/AUTH) ====================

OWNERSHIP_MISMATCH (422): Cross-ownership reference violates BR-SHARE-005/006/007. Example: Tool references private Service (Service.shared must be true) or Service references Secret with different owner.

PERMISSION_DENIED (403): Non-owner attempts to modify/delete or execute private Tool/Service (when policy prefers 403 over 404 for clarity).

NOT_FOUND (404): Resource missing OR not visible to caller (private and different owner); used to avoid ownership leaks for all five entity types.

DELETION_DEPENDENCY (409): Cannot delete/unshare because other users’ resources depend (BR-SHARE-004).
