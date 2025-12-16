```yaml
asyncapi: 3.0.0
info:
  title: Aiden Memory Agent Chat Events
  version: 5.0.0
  description: |
    Event-driven architecture specification for Aiden Memory Agent Chat.
    All state mutations produce events; workers consume events to transform state.
    
    This document is SOURCE OF TRUTH for event schemas and flow.

servers:
  production:
    host: nats://localhost:4222
    protocol: nats
    description: NATS message broker

channels:
  service.creation.requested:
    address: service.creation.requested
    messages:
      ServiceCreationRequested:
        $ref: '#/components/messages/ServiceCreationRequested'
    description: Published when POST /api/v1/services receives valid request
    
  service.created:
    address: service.created
    messages:
      ServiceCreated:
        $ref: '#/components/messages/ServiceCreated'
    description: Published when CreateServiceWorker successfully creates Service
    
  service.creation.failed:
    address: service.creation.failed
    messages:
      ServiceCreationFailed:
        $ref: '#/components/messages/ServiceCreationFailed'
    description: Published when Service creation fails validation or persistence

  service.update.requested:
    address: service.update.requested
    messages:
      ServiceUpdateRequested:
        $ref: '#/components/messages/ServiceUpdateRequested'
    description: Published when PUT /api/v1/services/{id} receives valid request
    x-event-flow-diagrams:
      - service-update-happy
      - service-update-failure

  service.updated:
    address: service.updated
    messages:
      ServiceUpdated:
        $ref: '#/components/messages/ServiceUpdated'
    description: Published when UpdateServiceWorker successfully updates Service
    x-event-flow-diagrams:
      - service-update-happy

  service.update.failed:
    address: service.update.failed
    messages:
      ServiceUpdateFailed:
        $ref: '#/components/messages/ServiceUpdateFailed'
    description: Published when Service update fails validation or persistence
    x-event-flow-diagrams:
      - service-update-failure

  service.deletion.requested:
    address: service.deletion.requested
    messages:
      ServiceDeletionRequested:
        $ref: '#/components/messages/ServiceDeletionRequested'
    description: Published when DELETE /api/v1/services/{id} receives valid request
    x-event-flow-diagrams:
      - service-deletion-happy
      - service-deletion-failure

  service.deleted:
    address: service.deleted
    messages:
      ServiceDeleted:
        $ref: '#/components/messages/ServiceDeleted'
    description: Published when DeleteServiceWorker removes Service
    x-event-flow-diagrams:
      - service-deletion-happy

  service.deletion.failed:
    address: service.deletion.failed
    messages:
      ServiceDeletionFailed:
        $ref: '#/components/messages/ServiceDeletionFailed'
    description: Published when Service deletion fails safety checks
    x-event-flow-diagrams:
      - service-deletion-failure


  secret.creation.requested:
    address: secret.creation.requested
    messages:
      SecretCreationRequested:
        $ref: '#/components/messages/SecretCreationRequested'
    description: Published when POST /api/v1/secrets receives valid request; includes `OWNED_BY` edge target for owner scoping and subscriber filtering.
    x-event-flow-diagrams:
      - secret-creation-happy
      - secret-creation-failure

  secret.created:
    address: secret.created
    messages:
      SecretCreated:
        $ref: '#/components/messages/SecretCreated'
    description: Published when CreateSecretWorker stores encrypted secret; payload carries `OWNED_BY` edge target and never includes plaintext.
    x-event-flow-diagrams:
      - secret-creation-happy

  secret.creation.failed:
    address: secret.creation.failed
    messages:
      SecretCreationFailed:
        $ref: '#/components/messages/SecretCreationFailed'
    description: Published when secret creation fails validation
    x-event-flow-diagrams:
      - secret-creation-failure

  secret.rotation.requested:
    address: secret.rotation.requested
    messages:
      SecretRotationRequested:
        $ref: '#/components/messages/SecretRotationRequested'
    description: Published when PUT /api/v1/secrets/{id} receives valid request; only owner-scoped rotations are published.
    x-event-flow-diagrams:
      - secret-rotation-happy
      - secret-rotation-failure

  secret.rotated:
    address: secret.rotated
    messages:
      SecretRotated:
        $ref: '#/components/messages/SecretRotated'
    description: Published when RotateSecretWorker updates encrypted value; payload includes `OWNED_BY` edge target for downstream filtering.
    x-event-flow-diagrams:
      - secret-rotation-happy

  secret.rotation.failed:
    address: secret.rotation.failed
    messages:
      SecretRotationFailed:
        $ref: '#/components/messages/SecretRotationFailed'
    description: Published when secret rotation fails validation or storage
    x-event-flow-diagrams:
      - secret-rotation-failure

  secret.deletion.requested:
    address: secret.deletion.requested
    messages:
      SecretDeletionRequested:
        $ref: '#/components/messages/SecretDeletionRequested'
    description: Published when DELETE /api/v1/secrets/{id} receives valid owner-scoped request.
    x-event-flow-diagrams:
      - secret-deletion-happy
      - secret-deletion-failure

  secret.deleted:
    address: secret.deleted
    messages:
      SecretDeleted:
        $ref: '#/components/messages/SecretDeleted'
    description: Published when DeleteSecretWorker removes the secret; payload retains `OWNED_BY` edge target.
    x-event-flow-diagrams:
      - secret-deletion-happy

  secret.deletion.failed:
    address: secret.deletion.failed
    messages:
      SecretDeletionFailed:
        $ref: '#/components/messages/SecretDeletionFailed'
    description: Published when secret deletion fails due to references
    x-event-flow-diagrams:
      - secret-deletion-failure

  tool.creation.requested:
    address: tool.creation.requested
    messages:
      ToolCreationRequested:
        $ref: '#/components/messages/ToolCreationRequested'
    description: Published when POST /api/v1/tools receives valid request
    x-event-flow-diagrams:
      - tool-creation-happy
      - tool-creation-failure

  tool.created:
    address: tool.created
    messages:
      ToolCreated:
        $ref: '#/components/messages/ToolCreated'
    description: Published when CreateToolWorker successfully persists Tool
    x-event-flow-diagrams:
      - tool-creation-happy

  tool.creation.failed:
    address: tool.creation.failed
    messages:
      ToolCreationFailed:
        $ref: '#/components/messages/ToolCreationFailed'
    description: Published when Tool creation fails validation or persistence
    x-event-flow-diagrams:
      - tool-creation-failure

  tool.update.requested:
    address: tool.update.requested
    messages:
      ToolUpdateRequested:
        $ref: '#/components/messages/ToolUpdateRequested'
    description: Published when PUT /api/v1/tools/{id} receives valid request
    x-event-flow-diagrams:
      - tool-update-happy
      - tool-update-failure

  tool.updated:
    address: tool.updated
    messages:
      ToolUpdated:
        $ref: '#/components/messages/ToolUpdated'
    description: Published when UpdateToolWorker applies Tool changes
    x-event-flow-diagrams:
      - tool-update-happy

  tool.update.failed:
    address: tool.update.failed
    messages:
      ToolUpdateFailed:
        $ref: '#/components/messages/ToolUpdateFailed'
    description: Published when Tool update fails validation or persistence
    x-event-flow-diagrams:
      - tool-update-failure

  tool.deletion.requested:
    address: tool.deletion.requested
    messages:
      ToolDeletionRequested:
        $ref: '#/components/messages/ToolDeletionRequested'
    description: Published when DELETE /api/v1/tools/{id} receives valid request
    x-event-flow-diagrams:
      - tool-deletion-happy
      - tool-deletion-failure

  tool.deleted:
    address: tool.deleted
    messages:
      ToolDeleted:
        $ref: '#/components/messages/ToolDeleted'
    description: Published when DeleteToolWorker removes Tool
    x-event-flow-diagrams:
      - tool-deletion-happy

  tool.deletion.failed:
    address: tool.deletion.failed
    messages:
      ToolDeletionFailed:
        $ref: '#/components/messages/ToolDeletionFailed'
    description: Published when Tool deletion fails dependency checks
    x-event-flow-diagrams:
      - tool-deletion-failure

  tool.test.requested:
    address: tool.test.requested
    messages:
      ToolTestRequested:
        $ref: '#/components/messages/ToolTestRequested'
    description: Published when POST /api/v1/tools/{id}/test receives valid request
    x-event-flow-diagrams:
      - tool-test-happy
      - tool-test-failure

  tool.tested:
    address: tool.tested
    messages:
      ToolTested:
        $ref: '#/components/messages/ToolTested'
    description: Published when ToolTestWorker completes execution
    x-event-flow-diagrams:
      - tool-test-happy

  tool.test.failed:
    address: tool.test.failed
    messages:
      ToolTestFailed:
        $ref: '#/components/messages/ToolTestFailed'
    description: Published when Tool test fails or errors
    x-event-flow-diagrams:
      - tool-test-failure

  process.creation.requested:
    address: process.creation.requested
    messages:
      ProcessCreationRequested:
        $ref: '#/components/messages/ProcessCreationRequested'
    description: Published when POST /api/v1/processes receives valid request
    x-event-flow-diagrams:
      - process-creation-happy
      - process-creation-failure

  process.created:
    address: process.created
    messages:
      ProcessCreated:
        $ref: '#/components/messages/ProcessCreated'
    description: Published when CreateProcessWorker persists Process
    x-event-flow-diagrams:
      - process-creation-happy

  process.creation.failed:
    address: process.creation.failed
    messages:
      ProcessCreationFailed:
        $ref: '#/components/messages/ProcessCreationFailed'
    description: Published when Process creation fails validation or persistence
    x-event-flow-diagrams:
      - process-creation-failure

  process.update.requested:
    address: process.update.requested
    messages:
      ProcessUpdateRequested:
        $ref: '#/components/messages/ProcessUpdateRequested'
    description: Published when PUT /api/v1/processes/{id} receives valid request
    x-event-flow-diagrams:
      - process-update-happy
      - process-update-failure

  process.updated:
    address: process.updated
    messages:
      ProcessUpdated:
        $ref: '#/components/messages/ProcessUpdated'
    description: Published when UpdateProcessWorker applies Process changes
    x-event-flow-diagrams:
      - process-update-happy

  process.update.failed:
    address: process.update.failed
    messages:
      ProcessUpdateFailed:
        $ref: '#/components/messages/ProcessUpdateFailed'
    description: Published when Process update fails validation or persistence
    x-event-flow-diagrams:
      - process-update-failure

  process.deletion.requested:
    address: process.deletion.requested
    messages:
      ProcessDeletionRequested:
        $ref: '#/components/messages/ProcessDeletionRequested'
    description: Published when DELETE /api/v1/processes/{id} receives valid request
    x-event-flow-diagrams:
      - process-deletion-happy
      - process-deletion-failure

  process.deleted:
    address: process.deleted
    messages:
      ProcessDeleted:
        $ref: '#/components/messages/ProcessDeleted'
    description: Published when DeleteProcessWorker removes Process
    x-event-flow-diagrams:
      - process-deletion-happy

  process.deletion.failed:
    address: process.deletion.failed
    messages:
      ProcessDeletionFailed:
        $ref: '#/components/messages/ProcessDeletionFailed'
    description: Published when Process deletion fails due to references
    x-event-flow-diagrams:
      - process-deletion-failure

  process.execution.requested:
    address: process.execution.requested
    messages:
      ProcessExecutionRequested:
        $ref: '#/components/messages/ProcessExecutionRequested'
    description: Published when POST /api/v1/processes/{id}/execute receives valid request
    x-event-flow-diagrams:
      - process-execution-happy
      - process-execution-failure

  process.executed:
    address: process.executed
    messages:
      ProcessExecuted:
        $ref: '#/components/messages/ProcessExecuted'
    description: Published when ProcessExecutionWorker completes workflow
    x-event-flow-diagrams:
      - process-execution-happy

  process.execution.failed:
    address: process.execution.failed
    messages:
      ProcessExecutionFailed:
        $ref: '#/components/messages/ProcessExecutionFailed'
    description: Published when Process execution fails or errors
    x-event-flow-diagrams:
      - process-execution-failure

  conversation.creation.requested:
    address: conversation.creation.requested
    messages:
      ConversationCreationRequested:
        $ref: '#/components/messages/ConversationCreationRequested'
    description: Published when POST /api/v1/conversations receives valid request
    x-event-flow-diagrams:
      - conversation-creation-happy
      - conversation-creation-failure

  conversation.created:
    address: conversation.created
    messages:
      ConversationCreated:
        $ref: '#/components/messages/ConversationCreated'
    description: Published when CreateConversationWorker persists Conversation
    x-event-flow-diagrams:
      - conversation-creation-happy

  conversation.creation.failed:
    address: conversation.creation.failed
    messages:
      ConversationCreationFailed:
        $ref: '#/components/messages/ConversationCreationFailed'
    description: Published when Conversation creation fails validation
    x-event-flow-diagrams:
      - conversation-creation-failure

  turn.creation.requested:
    address: turn.creation.requested
    messages:
      TurnCreationRequested:
        $ref: '#/components/messages/TurnCreationRequested'
    description: Published when POST /api/v1/conversations/{id}/turns receives valid request
    x-event-flow-diagrams:
      - turn-creation-happy
      - turn-creation-failure

  turn.created:
    address: turn.created
    messages:
      TurnCreated:
        $ref: '#/components/messages/TurnCreated'
    description: Published when CreateTurnWorker persists new Turn + alternative
    x-event-flow-diagrams:
      - turn-creation-happy

  turn.creation.failed:
    address: turn.creation.failed
    messages:
      TurnCreationFailed:
        $ref: '#/components/messages/TurnCreationFailed'
    description: Published when Turn creation fails validation or persistence
    x-event-flow-diagrams:
      - turn-creation-failure

  conversation.fork.requested:
    address: conversation.fork.requested
    messages:
      ConversationForkRequested:
        $ref: '#/components/messages/ConversationForkRequested'
    description: Published when POST /api/v1/conversations/{id}/turns/{turnId}/fork receives valid request
    x-event-flow-diagrams:
      - conversation-fork-happy
      - conversation-fork-failure

  conversation.forked:
    address: conversation.forked
    messages:
      ConversationForked:
        $ref: '#/components/messages/ConversationForked'
    description: Published when ForkConversationWorker creates new branch
    x-event-flow-diagrams:
      - conversation-fork-happy

  conversation.fork.failed:
    address: conversation.fork.failed
    messages:
      ConversationForkFailed:
        $ref: '#/components/messages/ConversationForkFailed'
    description: Published when conversation fork fails validation
    x-event-flow-diagrams:
      - conversation-fork-failure

  alternative.creation.requested:
    address: alternative.creation.requested
    messages:
      AlternativeCreationRequested:
        $ref: '#/components/messages/AlternativeCreationRequested'
    description: Published when POST /api/v1/conversations/{id}/turns/{turnId}/alternatives receives valid request
    x-event-flow-diagrams:
      - alternative-creation-happy
      - alternative-creation-failure

  alternative.created:
    address: alternative.created
    messages:
      AlternativeCreated:
        $ref: '#/components/messages/AlternativeCreated'
    description: Published when CreateAlternativeWorker stores new alternative
    x-event-flow-diagrams:
      - alternative-creation-happy

  alternative.creation.failed:
    address: alternative.creation.failed
    messages:
      AlternativeCreationFailed:
        $ref: '#/components/messages/AlternativeCreationFailed'
    description: Published when alternative creation fails validation
    x-event-flow-diagrams:
      - alternative-creation-failure

  alternative.regeneration.requested:
    address: alternative.regeneration.requested
    messages:
      AlternativeRegenerationRequested:
        $ref: '#/components/messages/AlternativeRegenerationRequested'
    description: Published when POST /api/v1/conversations/{id}/turns/{turnId}/alternatives/{altId}/regenerate receives valid request
    x-event-flow-diagrams:
      - alternative-regeneration-happy
      - alternative-regeneration-failure

  alternative.regenerated:
    address: alternative.regenerated
    messages:
      AlternativeRegenerated:
        $ref: '#/components/messages/AlternativeRegenerated'
    description: Published when RegenerateAlternativeWorker completes rerun
    x-event-flow-diagrams:
      - alternative-regeneration-happy

  alternative.regeneration.failed:
    address: alternative.regeneration.failed
    messages:
      AlternativeRegenerationFailed:
        $ref: '#/components/messages/AlternativeRegenerationFailed'
    description: Published when alternative regeneration fails
    x-event-flow-diagrams:
      - alternative-regeneration-failure

  context.compression.requested:
    address: context.compression.requested
    messages:
      ContextCompressionRequested:
        $ref: '#/components/messages/ContextCompressionRequested'
    description: Published when POST /api/v1/conversations/{id}/working-memory/compress receives valid request
    x-event-flow-diagrams:
      - working-memory-compression-happy
      - working-memory-compression-failure

  context.compressed:
    address: context.compressed
    messages:
      ContextCompressed:
        $ref: '#/components/messages/ContextCompressed'
    description: Published when WorkingMemoryCompressionWorker completes compression
    x-event-flow-diagrams:
      - working-memory-compression-happy

  context.compression.failed:
    address: context.compression.failed
    messages:
      ContextCompressionFailed:
        $ref: '#/components/messages/ContextCompressionFailed'
    description: Published when WorkingMemory compression fails
    x-event-flow-diagrams:
      - working-memory-compression-failure

  entity.creation.requested:
    address: entity.creation.requested
    messages:
      EntityCreationRequested:
        $ref: '#/components/messages/EntityCreationRequested'
    description: Published when POST /api/v1/entities receives valid request
    x-event-flow-diagrams:
      - entity-creation-happy
      - entity-creation-failure

  entity.created:
    address: entity.created
    messages:
      EntityCreated:
        $ref: '#/components/messages/EntityCreated'
    description: Published when CreateEntityWorker persists Entity
    x-event-flow-diagrams:
      - entity-creation-happy

  entity.creation.failed:
    address: entity.creation.failed
    messages:
      EntityCreationFailed:
        $ref: '#/components/messages/EntityCreationFailed'
    description: Published when Entity creation fails validation/persistence
    x-event-flow-diagrams:
      - entity-creation-failure

  entity.update.requested:
    address: entity.update.requested
    messages:
      EntityUpdateRequested:
        $ref: '#/components/messages/EntityUpdateRequested'
    description: Published when PUT /api/v1/entities/{uuid} receives valid request
    x-event-flow-diagrams:
      - entity-update-happy
      - entity-update-failure

  entity.updated:
    address: entity.updated
    messages:
      EntityUpdated:
        $ref: '#/components/messages/EntityUpdated'
    description: Published when UpdateEntityWorker applies changes
    x-event-flow-diagrams:
      - entity-update-happy

  entity.update.failed:
    address: entity.update.failed
    messages:
      EntityUpdateFailed:
        $ref: '#/components/messages/EntityUpdateFailed'
    description: Published when Entity update fails validation/persistence
    x-event-flow-diagrams:
      - entity-update-failure

  entity.deletion.requested:
    address: entity.deletion.requested
    messages:
      EntityDeletionRequested:
        $ref: '#/components/messages/EntityDeletionRequested'
    description: Published when DELETE /api/v1/entities/{uuid} receives valid request
    x-event-flow-diagrams:
      - entity-deletion-happy
      - entity-deletion-failure

  entity.deleted:
    address: entity.deleted
    messages:
      EntityDeleted:
        $ref: '#/components/messages/EntityDeleted'
    description: Published when DeleteEntityWorker removes Entity
    x-event-flow-diagrams:
      - entity-deletion-happy

  entity.deletion.failed:
    address: entity.deletion.failed
    messages:
      EntityDeletionFailed:
        $ref: '#/components/messages/EntityDeletionFailed'
    description: Published when Entity deletion fails due to references
    x-event-flow-diagrams:
      - entity-deletion-failure

  summary.creation.requested:
    address: summary.creation.requested
    messages:
      SummaryCreationRequested:
        $ref: '#/components/messages/SummaryCreationRequested'
    description: Published when POST /api/v1/conversations/{id}/summaries receives valid request
    x-event-flow-diagrams:
      - summary-creation-happy
      - summary-creation-failure

  summary.created:
    address: summary.created
    messages:
      SummaryCreated:
        $ref: '#/components/messages/SummaryCreated'
    description: Published when SummaryWorker persists Summary
    x-event-flow-diagrams:
      - summary-creation-happy

  summary.creation.failed:
    address: summary.creation.failed
    messages:
      SummaryCreationFailed:
        $ref: '#/components/messages/SummaryCreationFailed'
    description: Published when Summary creation fails validation
    x-event-flow-diagrams:
      - summary-creation-failure

  summary.update.requested:
    address: summary.update.requested
    messages:
      SummaryUpdateRequested:
        $ref: '#/components/messages/SummaryUpdateRequested'
    description: Published when PUT /api/v1/conversations/{id}/summaries/{summaryId} receives valid request
    x-event-flow-diagrams:
      - summary-update-happy
      - summary-update-failure

  summary.updated:
    address: summary.updated
    messages:
      SummaryUpdated:
        $ref: '#/components/messages/SummaryUpdated'
    description: Published when SummaryWorker updates Summary `HAS_CONTENT` edge binding
    x-event-flow-diagrams:
      - summary-update-happy

  summary.update.failed:
    address: summary.update.failed
    messages:
      SummaryUpdateFailed:
        $ref: '#/components/messages/SummaryUpdateFailed'
    description: Published when Summary update fails validation
    x-event-flow-diagrams:
      - summary-update-failure

  summary.deletion.requested:
    address: summary.deletion.requested
    messages:
      SummaryDeletionRequested:
        $ref: '#/components/messages/SummaryDeletionRequested'
    description: Published when DELETE /api/v1/conversations/{id}/summaries/{summaryId} receives valid request
    x-event-flow-diagrams:
      - summary-deletion-happy
      - summary-deletion-failure

  summary.deleted:
    address: summary.deleted
    messages:
      SummaryDeleted:
        $ref: '#/components/messages/SummaryDeleted'
    description: Published when SummaryWorker deletes Summary (admin override)
    x-event-flow-diagrams:
      - summary-deletion-happy

  summary.deletion.failed:
    address: summary.deletion.failed
    messages:
      SummaryDeletionFailed:
        $ref: '#/components/messages/SummaryDeletionFailed'
    description: Published when Summary deletion fails validation
    x-event-flow-diagrams:
      - summary-deletion-failure

  introspection.creation.requested:
    address: introspection.creation.requested
    messages:
      IntrospectionCreationRequested:
        $ref: '#/components/messages/IntrospectionCreationRequested'
    description: Published when POST /api/v1/introspections receives valid request
    x-event-flow-diagrams:
      - introspection-creation-happy
      - introspection-creation-failure

  introspection.created:
    address: introspection.created
    messages:
      IntrospectionCreated:
        $ref: '#/components/messages/IntrospectionCreated'
    description: Published when IntrospectionWorker adds carousel entry
    x-event-flow-diagrams:
      - introspection-creation-happy

  introspection.creation.failed:
    address: introspection.creation.failed
    messages:
      IntrospectionCreationFailed:
        $ref: '#/components/messages/IntrospectionCreationFailed'
    description: Published when Introspection creation fails validation
    x-event-flow-diagrams:
      - introspection-creation-failure

  introspection.update.requested:
    address: introspection.update.requested
    messages:
      IntrospectionUpdateRequested:
        $ref: '#/components/messages/IntrospectionUpdateRequested'
    description: Published when PUT /api/v1/introspections/{id} receives valid request
    x-event-flow-diagrams:
      - introspection-update-happy
      - introspection-update-failure

  introspection.updated:
    address: introspection.updated
    messages:
      IntrospectionUpdated:
        $ref: '#/components/messages/IntrospectionUpdated'
    description: Published when IntrospectionWorker updates carousel entry
    x-event-flow-diagrams:
      - introspection-update-happy

  introspection.update.failed:
    address: introspection.update.failed
    messages:
      IntrospectionUpdateFailed:
        $ref: '#/components/messages/IntrospectionUpdateFailed'
    description: Published when Introspection update fails validation
    x-event-flow-diagrams:
      - introspection-update-failure

  introspection.deletion.requested:
    address: introspection.deletion.requested
    messages:
      IntrospectionDeletionRequested:
        $ref: '#/components/messages/IntrospectionDeletionRequested'
    description: Published when DELETE /api/v1/introspections/{id} receives valid request
    x-event-flow-diagrams:
      - introspection-deletion-happy
      - introspection-deletion-failure

  introspection.deleted:
    address: introspection.deleted
    messages:
      IntrospectionDeleted:
        $ref: '#/components/messages/IntrospectionDeleted'
    description: Published when IntrospectionWorker deletes carousel entry
    x-event-flow-diagrams:
      - introspection-deletion-happy

  introspection.deletion.failed:
    address: introspection.deletion.failed
    messages:
      IntrospectionDeletionFailed:
        $ref: '#/components/messages/IntrospectionDeletionFailed'
    description: Published when Introspection deletion fails validation
    x-event-flow-diagrams:
      - introspection-deletion-failure

  operation.cancellation.requested:
    address: operation.cancellation.requested
    messages:
      OperationCancellationRequested:
        $ref: '#/components/messages/OperationCancellationRequested'
    description: Published when POST /api/v1/operations/{id}/cancel receives valid request
    x-event-flow-diagrams:
      - operation-cancellation-happy
      - operation-cancellation-failure

  operation.cancelled:
    address: operation.cancelled
    messages:
      OperationCancelled:
        $ref: '#/components/messages/OperationCancelled'
    description: Published when OperationCancellationWorker marks operation cancelled
    x-event-flow-diagrams:
      - operation-cancellation-happy

  operation.cancellation.failed:
    address: operation.cancellation.failed
    messages:
      OperationCancellationFailed:
        $ref: '#/components/messages/OperationCancellationFailed'
    description: Published when operation cancellation fails or is disallowed
    x-event-flow-diagrams:
      - operation-cancellation-failure

  worker.job-submission.requested:
    address: worker.job-submission.requested
    messages:
      WorkerJobSubmissionRequested:
        $ref: '#/components/messages/WorkerJobSubmissionRequested'
    description: Published when POST /api/v1/workers/{type}/jobs receives valid request
    x-event-flow-diagrams:
      - worker-job-submission-happy
      - worker-job-submission-failure

  worker.job-submitted:
    address: worker.job-submitted
    messages:
      WorkerJobSubmitted:
        $ref: '#/components/messages/WorkerJobSubmitted'
    description: Published when WorkerJobScheduler enqueues job
    x-event-flow-diagrams:
      - worker-job-submission-happy

  worker.job-submission.failed:
    address: worker.job-submission.failed
    messages:
      WorkerJobSubmissionFailed:
        $ref: '#/components/messages/WorkerJobSubmissionFailed'
    description: Published when worker job submission fails
    x-event-flow-diagrams:
      - worker-job-submission-failure

  # ... (repeat pattern for all async operations)

operations:
  createService:
    action: send
    channel:
      $ref: '#/channels/service.creation.requested'
    messages:
      - $ref: '#/channels/service.creation.requested/messages/ServiceCreationRequested'
    description: API publishes this event when client POSTs to /api/v1/services

  onServiceCreated:
    action: receive
    channel:
      $ref: '#/channels/service.created'
    messages:
      - $ref: '#/channels/service.created/messages/ServiceCreated'
    description: Subscribers receive notification of successful Service creation

  updateService:
    action: send
    channel:
      $ref: '#/channels/service.update.requested'
    messages:
      - $ref: '#/channels/service.update.requested/messages/ServiceUpdateRequested'
    description: API publishes when client PUTs to /api/v1/services/{id}

  onServiceUpdated:
    action: receive
    channel:
      $ref: '#/channels/service.updated'
    messages:
      - $ref: '#/channels/service.updated/messages/ServiceUpdated'
    description: Subscribers notified when a Service update succeeds

  deleteService:
    action: send
    channel:
      $ref: '#/channels/service.deletion.requested'
    messages:
      - $ref: '#/channels/service.deletion.requested/messages/ServiceDeletionRequested'
    description: API publishes when client DELETEs /api/v1/services/{id}

  onServiceDeleted:
    action: receive
    channel:
      $ref: '#/channels/service.deleted'
    messages:
      - $ref: '#/channels/service.deleted/messages/ServiceDeleted'
    description: Subscribers notified when a Service is deleted

  createSecret:
    action: send
    channel:
      $ref: '#/channels/secret.creation.requested'
    messages:
      - $ref: '#/channels/secret.creation.requested/messages/SecretCreationRequested'
    description: API publishes when client POSTs to /api/v1/secrets

  onSecretCreated:
    action: receive
    channel:
      $ref: '#/channels/secret.created'
    messages:
      - $ref: '#/channels/secret.created/messages/SecretCreated'
    description: Subscribers notified when a secret is created

  rotateSecret:
    action: send
    channel:
      $ref: '#/channels/secret.rotation.requested'
    messages:
      - $ref: '#/channels/secret.rotation.requested/messages/SecretRotationRequested'
    description: API publishes when client PUTs to /api/v1/secrets/{id}

  onSecretRotated:
    action: receive
    channel:
      $ref: '#/channels/secret.rotated'
    messages:
      - $ref: '#/channels/secret.rotated/messages/SecretRotated'
    description: Subscribers notified when a secret rotation succeeds

  deleteSecret:
    action: send
    channel:
      $ref: '#/channels/secret.deletion.requested'
    messages:
      - $ref: '#/channels/secret.deletion.requested/messages/SecretDeletionRequested'
    description: API publishes when client DELETEs /api/v1/secrets/{id}

  onSecretDeleted:
    action: receive
    channel:
      $ref: '#/channels/secret.deleted'
    messages:
      - $ref: '#/channels/secret.deleted/messages/SecretDeleted'
    description: Subscribers notified when a secret is deleted

  createTool:
    action: send
    channel:
      $ref: '#/channels/tool.creation.requested'
    messages:
      - $ref: '#/channels/tool.creation.requested/messages/ToolCreationRequested'
    description: API publishes when client POSTs to /api/v1/tools

  onToolCreated:
    action: receive
    channel:
      $ref: '#/channels/tool.created'
    messages:
      - $ref: '#/channels/tool.created/messages/ToolCreated'
    description: Subscribers notified when a Tool is created

  updateTool:
    action: send
    channel:
      $ref: '#/channels/tool.update.requested'
    messages:
      - $ref: '#/channels/tool.update.requested/messages/ToolUpdateRequested'
    description: API publishes when client PUTs to /api/v1/tools/{id}

  onToolUpdated:
    action: receive
    channel:
      $ref: '#/channels/tool.updated'
    messages:
      - $ref: '#/channels/tool.updated/messages/ToolUpdated'
    description: Subscribers notified when a Tool update succeeds

  deleteTool:
    action: send
    channel:
      $ref: '#/channels/tool.deletion.requested'
    messages:
      - $ref: '#/channels/tool.deletion.requested/messages/ToolDeletionRequested'
    description: API publishes when client DELETEs /api/v1/tools/{id}

  onToolDeleted:
    action: receive
    channel:
      $ref: '#/channels/tool.deleted'
    messages:
      - $ref: '#/channels/tool.deleted/messages/ToolDeleted'
    description: Subscribers notified when a Tool is deleted

  testToolExecution:
    action: send
    channel:
      $ref: '#/channels/tool.test.requested'
    messages:
      - $ref: '#/channels/tool.test.requested/messages/ToolTestRequested'
    description: API publishes when client POSTs /api/v1/tools/{id}/test

  onToolTested:
    action: receive
    channel:
      $ref: '#/channels/tool.tested'
    messages:
      - $ref: '#/channels/tool.tested/messages/ToolTested'
    description: Subscribers notified when a Tool test completes

  createProcess:
    action: send
    channel:
      $ref: '#/channels/process.creation.requested'
    messages:
      - $ref: '#/channels/process.creation.requested/messages/ProcessCreationRequested'
    description: API publishes when client POSTs to /api/v1/processes

  onProcessCreated:
    action: receive
    channel:
      $ref: '#/channels/process.created'
    messages:
      - $ref: '#/channels/process.created/messages/ProcessCreated'
    description: Subscribers notified when a Process is created

  updateProcess:
    action: send
    channel:
      $ref: '#/channels/process.update.requested'
    messages:
      - $ref: '#/channels/process.update.requested/messages/ProcessUpdateRequested'
    description: API publishes when client PUTs to /api/v1/processes/{id}

  onProcessUpdated:
    action: receive
    channel:
      $ref: '#/channels/process.updated'
    messages:
      - $ref: '#/channels/process.updated/messages/ProcessUpdated'
    description: Subscribers notified when a Process update succeeds

  deleteProcess:
    action: send
    channel:
      $ref: '#/channels/process.deletion.requested'
    messages:
      - $ref: '#/channels/process.deletion.requested/messages/ProcessDeletionRequested'
    description: API publishes when client DELETEs /api/v1/processes/{id}

  onProcessDeleted:
    action: receive
    channel:
      $ref: '#/channels/process.deleted'
    messages:
      - $ref: '#/channels/process.deleted/messages/ProcessDeleted'
    description: Subscribers notified when a Process is deleted

  executeProcessRequest:
    action: send
    channel:
      $ref: '#/channels/process.execution.requested'
    messages:
      - $ref: '#/channels/process.execution.requested/messages/ProcessExecutionRequested'
    description: API publishes when client POSTs /api/v1/processes/{id}/execute

  onProcessExecuted:
    action: receive
    channel:
      $ref: '#/channels/process.executed'
    messages:
      - $ref: '#/channels/process.executed/messages/ProcessExecuted'
    description: Subscribers notified when a Process execution completes

  createConversation:
    action: send
    channel:
      $ref: '#/channels/conversation.creation.requested'
    messages:
      - $ref: '#/channels/conversation.creation.requested/messages/ConversationCreationRequested'
    description: API publishes when client POSTs to /api/v1/conversations

  onConversationCreated:
    action: receive
    channel:
      $ref: '#/channels/conversation.created'
    messages:
      - $ref: '#/channels/conversation.created/messages/ConversationCreated'
    description: Subscribers notified when a Conversation is created

  createTurn:
    action: send
    channel:
      $ref: '#/channels/turn.creation.requested'
    messages:
      - $ref: '#/channels/turn.creation.requested/messages/TurnCreationRequested'
    description: API publishes when client POSTs /api/v1/conversations/{id}/turns

  onTurnCreated:
    action: receive
    channel:
      $ref: '#/channels/turn.created'
    messages:
      - $ref: '#/channels/turn.created/messages/TurnCreated'
    description: Subscribers notified when a Turn is created

  forkConversation:
    action: send
    channel:
      $ref: '#/channels/conversation.fork.requested'
    messages:
      - $ref: '#/channels/conversation.fork.requested/messages/ConversationForkRequested'
    description: API publishes when client POSTs /api/v1/conversations/{id}/turns/{turnId}/fork

  onConversationForked:
    action: receive
    channel:
      $ref: '#/channels/conversation.forked'
    messages:
      - $ref: '#/channels/conversation.forked/messages/ConversationForked'
    description: Subscribers notified when a conversation fork completes

  createAlternative:
    action: send
    channel:
      $ref: '#/channels/alternative.creation.requested'
    messages:
      - $ref: '#/channels/alternative.creation.requested/messages/AlternativeCreationRequested'
    description: API publishes when client POSTs /api/v1/conversations/{id}/turns/{turnId}/alternatives

  onAlternativeCreated:
    action: receive
    channel:
      $ref: '#/channels/alternative.created'
    messages:
      - $ref: '#/channels/alternative.created/messages/AlternativeCreated'
    description: Subscribers notified when an alternative is created

  regenerateAlternative:
    action: send
    channel:
      $ref: '#/channels/alternative.regeneration.requested'
    messages:
      - $ref: '#/channels/alternative.regeneration.requested/messages/AlternativeRegenerationRequested'
    description: API publishes when client POSTs /api/v1/conversations/{id}/turns/{turnId}/alternatives/{altId}/regenerate

  onAlternativeRegenerated:
    action: receive
    channel:
      $ref: '#/channels/alternative.regenerated'
    messages:
      - $ref: '#/channels/alternative.regenerated/messages/AlternativeRegenerated'
    description: Subscribers notified when an alternative regeneration completes

  compressWorkingMemory:
    action: send
    channel:
      $ref: '#/channels/context.compression.requested'
    messages:
      - $ref: '#/channels/context.compression.requested/messages/ContextCompressionRequested'
    description: API publishes when client POSTs /api/v1/conversations/{id}/working-memory/compress

  onWorkingMemoryCompressed:
    action: receive
    channel:
      $ref: '#/channels/context.compressed'
    messages:
      - $ref: '#/channels/context.compressed/messages/ContextCompressed'
    description: Subscribers notified when WorkingMemory compression completes

  createEntity:
    action: send
    channel:
      $ref: '#/channels/entity.creation.requested'
    messages:
      - $ref: '#/channels/entity.creation.requested/messages/EntityCreationRequested'
    description: API publishes when client POSTs to /api/v1/entities

  onEntityCreated:
    action: receive
    channel:
      $ref: '#/channels/entity.created'
    messages:
      - $ref: '#/channels/entity.created/messages/EntityCreated'
    description: Subscribers notified when an Entity is created

  updateEntity:
    action: send
    channel:
      $ref: '#/channels/entity.update.requested'
    messages:
      - $ref: '#/channels/entity.update.requested/messages/EntityUpdateRequested'
    description: API publishes when client PUTs to /api/v1/entities/{uuid}

  onEntityUpdated:
    action: receive
    channel:
      $ref: '#/channels/entity.updated'
    messages:
      - $ref: '#/channels/entity.updated/messages/EntityUpdated'
    description: Subscribers notified when an Entity update succeeds

  deleteEntity:
    action: send
    channel:
      $ref: '#/channels/entity.deletion.requested'
    messages:
      - $ref: '#/channels/entity.deletion.requested/messages/EntityDeletionRequested'
    description: API publishes when client DELETEs /api/v1/entities/{uuid}

  onEntityDeleted:
    action: receive
    channel:
      $ref: '#/channels/entity.deleted'
    messages:
      - $ref: '#/channels/entity.deleted/messages/EntityDeleted'
    description: Subscribers notified when an Entity is deleted

  createSummary:
    action: send
    channel:
      $ref: '#/channels/summary.creation.requested'
    messages:
      - $ref: '#/channels/summary.creation.requested/messages/SummaryCreationRequested'
    description: API publishes when client POSTs to /api/v1/conversations/{id}/summaries

  onSummaryCreated:
    action: receive
    channel:
      $ref: '#/channels/summary.created'
    messages:
      - $ref: '#/channels/summary.created/messages/SummaryCreated'
    description: Subscribers notified when a Summary is created

  updateSummary:
    action: send
    channel:
      $ref: '#/channels/summary.update.requested'
    messages:
      - $ref: '#/channels/summary.update.requested/messages/SummaryUpdateRequested'
    description: API publishes when client PUTs to /api/v1/conversations/{id}/summaries/{summaryId}

  onSummaryUpdated:
    action: receive
    channel:
      $ref: '#/channels/summary.updated'
    messages:
      - $ref: '#/channels/summary.updated/messages/SummaryUpdated'
    description: Subscribers notified when a Summary update succeeds

  deleteSummary:
    action: send
    channel:
      $ref: '#/channels/summary.deletion.requested'
    messages:
      - $ref: '#/channels/summary.deletion.requested/messages/SummaryDeletionRequested'
    description: API publishes when client DELETEs /api/v1/conversations/{id}/summaries/{summaryId}

  onSummaryDeleted:
    action: receive
    channel:
      $ref: '#/channels/summary.deleted'
    messages:
      - $ref: '#/channels/summary.deleted/messages/SummaryDeleted'
    description: Subscribers notified when a Summary is deleted

  createIntrospection:
    action: send
    channel:
      $ref: '#/channels/introspection.creation.requested'
    messages:
      - $ref: '#/channels/introspection.creation.requested/messages/IntrospectionCreationRequested'
    description: API publishes when client POSTs to /api/v1/introspections

  onIntrospectionCreated:
    action: receive
    channel:
      $ref: '#/channels/introspection.created'
    messages:
      - $ref: '#/channels/introspection.created/messages/IntrospectionCreated'
    description: Subscribers notified when an Introspection is created

  updateIntrospection:
    action: send
    channel:
      $ref: '#/channels/introspection.update.requested'
    messages:
      - $ref: '#/channels/introspection.update.requested/messages/IntrospectionUpdateRequested'
    description: API publishes when client PUTs to /api/v1/introspections/{id}

  onIntrospectionUpdated:
    action: receive
    channel:
      $ref: '#/channels/introspection.updated'
    messages:
      - $ref: '#/channels/introspection.updated/messages/IntrospectionUpdated'
    description: Subscribers notified when an Introspection update succeeds

  deleteIntrospection:
    action: send
    channel:
      $ref: '#/channels/introspection.deletion.requested'
    messages:
      - $ref: '#/channels/introspection.deletion.requested/messages/IntrospectionDeletionRequested'
    description: API publishes when client DELETEs /api/v1/introspections/{id}

  onIntrospectionDeleted:
    action: receive
    channel:
      $ref: '#/channels/introspection.deleted'
    messages:
      - $ref: '#/channels/introspection.deleted/messages/IntrospectionDeleted'
    description: Subscribers notified when an Introspection is deleted

  cancelOperation:
    action: send
    channel:
      $ref: '#/channels/operation.cancellation.requested'
    messages:
      - $ref: '#/channels/operation.cancellation.requested/messages/OperationCancellationRequested'
    description: API publishes when client POSTs /api/v1/operations/{id}/cancel

  onOperationCancelled:
    action: receive
    channel:
      $ref: '#/channels/operation.cancelled'
    messages:
      - $ref: '#/channels/operation.cancelled/messages/OperationCancelled'
    description: Subscribers notified when an operation is cancelled

  submitWorkerJob:
    action: send
    channel:
      $ref: '#/channels/worker.job-submission.requested'
    messages:
      - $ref: '#/channels/worker.job-submission.requested/messages/WorkerJobSubmissionRequested'
    description: API publishes when client POSTs /api/v1/workers/{type}/jobs

  onWorkerJobSubmitted:
    action: receive
    channel:
      $ref: '#/channels/worker.job-submitted'
    messages:
      - $ref: '#/channels/worker.job-submitted/messages/WorkerJobSubmitted'
    description: Subscribers notified when a worker job is enqueued

components:
  messages:
    ServiceCreationRequested:
      name: ServiceCreationRequested
      title: Service Creation Requested
      summary: Client requested Service creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceCreationRequestedPayload'
      x-business-rules:
        - BR-SERVICE-001  # Type-protocol compatibility
        - BR-SERVICE-002  # Secret requirements
      x-validation:
        - connectionSchema must be valid JSON Schema
        - type/protocol combination must be valid
      
    ServiceCreated:
      name: ServiceCreated
      title: Service Created Successfully
      summary: CreateServiceWorker persisted Service to database
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks
        - Record MetricValue for creation time
      
    ServiceCreationFailed:
      name: ServiceCreationFailed
      title: Service Creation Failed
      summary: CreateServiceWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Log error with correlation ID
        - Alert if failure rate exceeds threshold

    ServiceUpdateRequested:
      name: ServiceUpdateRequested
      title: Service Update Requested
      summary: Client requested Service update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceUpdateRequestedPayload'
      x-business-rules:
        - BR-SERVICE-001
        - BR-SERVICE-005
        - BR-SERVICE-006

    ServiceUpdated:
      name: ServiceUpdated
      title: Service Updated Successfully
      summary: UpdateServiceWorker applied changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ServiceUpdateFailed:
      name: ServiceUpdateFailed
      title: Service Update Failed
      summary: UpdateServiceWorker could not apply requested changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    ServiceDeletionRequested:
      name: ServiceDeletionRequested
      title: Service Deletion Requested
      summary: Client requested Service deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceDeletionRequestedPayload'
      x-business-rules:
        - BR-SERVICE-004

    ServiceDeleted:
      name: ServiceDeleted
      title: Service Deleted Successfully
      summary: DeleteServiceWorker removed Service
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ServiceDeletionFailed:
      name: ServiceDeletionFailed
      title: Service Deletion Failed
      summary: DeleteServiceWorker failed due to references or persistence errors
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ServiceDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    SecretCreationRequested:
      name: SecretCreationRequested
      title: Secret Creation Requested
      summary: Client requested Secret creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretCreationRequestedPayload'
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-003

    SecretCreated:
      name: SecretCreated
      title: Secret Created Successfully
      summary: CreateSecretWorker stored encrypted secret metadata
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SecretCreationFailed:
      name: SecretCreationFailed
      title: Secret Creation Failed
      summary: CreateSecretWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Log error with correlation ID

    SecretRotationRequested:
      name: SecretRotationRequested
      title: Secret Rotation Requested
      summary: Client requested Secret rotation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretRotationRequestedPayload'
      x-business-rules:
        - BR-SECRET-001
        - BR-SECRET-003

    SecretRotated:
      name: SecretRotated
      title: Secret Rotated Successfully
      summary: RotateSecretWorker replaced encrypted value
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretRotatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SecretRotationFailed:
      name: SecretRotationFailed
      title: Secret Rotation Failed
      summary: RotateSecretWorker could not rotate secret
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretRotationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert if multiple rotation failures detected

    SecretDeletionRequested:
      name: SecretDeletionRequested
      title: Secret Deletion Requested
      summary: Client requested Secret deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretDeletionRequestedPayload'
      x-business-rules:
        - BR-SECRET-002

    SecretDeleted:
      name: SecretDeleted
      title: Secret Deleted Successfully
      summary: DeleteSecretWorker removed secret metadata
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SecretDeletionFailed:
      name: SecretDeletionFailed
      title: Secret Deletion Failed
      summary: DeleteSecretWorker failed due to references or errors
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SecretDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    ToolCreationRequested:
      name: ToolCreationRequested
      title: Tool Creation Requested
      summary: Client requested Tool creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolCreationRequestedPayload'
      x-business-rules:
        - BR-TOOL-001
        - BR-TOOL-002

    ToolCreated:
      name: ToolCreated
      title: Tool Created Successfully
      summary: CreateToolWorker persisted Tool
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ToolCreationFailed:
      name: ToolCreationFailed
      title: Tool Creation Failed
      summary: CreateToolWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert if configuration invalid

    ToolUpdateRequested:
      name: ToolUpdateRequested
      title: Tool Update Requested
      summary: Client requested Tool update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolUpdateRequestedPayload'
      x-business-rules:
        - BR-TOOL-003

    ToolUpdated:
      name: ToolUpdated
      title: Tool Updated Successfully
      summary: UpdateToolWorker applied Tool changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ToolUpdateFailed:
      name: ToolUpdateFailed
      title: Tool Update Failed
      summary: UpdateToolWorker could not apply changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert owner for remediation

    ToolDeletionRequested:
      name: ToolDeletionRequested
      title: Tool Deletion Requested
      summary: Client requested Tool deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolDeletionRequestedPayload'
      x-business-rules:
        - BR-TOOL-004

    ToolDeleted:
      name: ToolDeleted
      title: Tool Deleted Successfully
      summary: DeleteToolWorker removed Tool
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ToolDeletionFailed:
      name: ToolDeletionFailed
      title: Tool Deletion Failed
      summary: DeleteToolWorker failed due to references or errors
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    ToolTestRequested:
      name: ToolTestRequested
      title: Tool Test Requested
      summary: Client requested Tool test execution via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolTestRequestedPayload'
      x-business-rules:
        - BR-TOOL-005

    ToolTested:
      name: ToolTested
      title: Tool Test Completed
      summary: ToolTestWorker finished executing Tool test
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolTestedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers with results

    ToolTestFailed:
      name: ToolTestFailed
      title: Tool Test Failed
      summary: ToolTestWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ToolTestFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Tool owner for investigation

    ProcessCreationRequested:
      name: ProcessCreationRequested
      title: Process Creation Requested
      summary: Client requested Process creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessCreationRequestedPayload'
      x-business-rules:
        - BR-PROCESS-001
        - BR-PROCESS-006

    ProcessCreated:
      name: ProcessCreated
      title: Process Created Successfully
      summary: CreateProcessWorker persisted Process
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ProcessCreationFailed:
      name: ProcessCreationFailed
      title: Process Creation Failed
      summary: CreateProcessWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Process owner

    ProcessUpdateRequested:
      name: ProcessUpdateRequested
      title: Process Update Requested
      summary: Client requested Process update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessUpdateRequestedPayload'
      x-business-rules:
        - BR-PROCESS-002
        - BR-PROCESS-009

    ProcessUpdated:
      name: ProcessUpdated
      title: Process Updated Successfully
      summary: UpdateProcessWorker applied Process changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ProcessUpdateFailed:
      name: ProcessUpdateFailed
      title: Process Update Failed
      summary: UpdateProcessWorker could not apply changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Process owner

    ProcessDeletionRequested:
      name: ProcessDeletionRequested
      title: Process Deletion Requested
      summary: Client requested Process deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessDeletionRequestedPayload'
      x-business-rules:
        - BR-PROCESS-003

    ProcessDeleted:
      name: ProcessDeleted
      title: Process Deleted Successfully
      summary: DeleteProcessWorker removed Process
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ProcessDeletionFailed:
      name: ProcessDeletionFailed
      title: Process Deletion Failed
      summary: DeleteProcessWorker failed due to references
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    ProcessExecutionRequested:
      name: ProcessExecutionRequested
      title: Process Execution Requested
      summary: Client requested Process execution via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessExecutionRequestedPayload'
      x-business-rules:
        - BR-STEP-001
        - BR-EXEC-001

    ProcessExecuted:
      name: ProcessExecuted
      title: Process Execution Completed
      summary: ProcessExecutionWorker finished running Process
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessExecutedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers with results

    ProcessExecutionFailed:
      name: ProcessExecutionFailed
      title: Process Execution Failed
      summary: ProcessExecutionWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ProcessExecutionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert owner for investigation

    ConversationCreationRequested:
      name: ConversationCreationRequested
      title: Conversation Creation Requested
      summary: Client requested Conversation creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationCreationRequestedPayload'
      x-business-rules:
        - BR-CONV-001
        - BR-CONV-002

    ConversationCreated:
      name: ConversationCreated
      title: Conversation Created Successfully
      summary: CreateConversationWorker persisted Conversation
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ConversationCreationFailed:
      name: ConversationCreationFailed
      title: Conversation Creation Failed
      summary: CreateConversationWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    TurnCreationRequested:
      name: TurnCreationRequested
      title: Turn Creation Requested
      summary: Client requested Turn creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/TurnCreationRequestedPayload'
      x-business-rules:
        - BR-TURN-001
        - BR-TURN-002
        - BR-TURN-004
        - BR-TURN-006
        - BR-TURN-008

    TurnCreated:
      name: TurnCreated
      title: Turn Created Successfully
      summary: CreateTurnWorker persisted new Turn and alternative
      contentType: application/json
      payload:
        $ref: '#/components/schemas/TurnCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Establish HAS_TURN edge (Conversation → Turn)
        - Establish CHILD_OF edge (Turn → parent Turn) if parentTurnId provided
        - Establish HAS_ALTERNATIVE edge (Turn → Alternative) for initial alternative
        - Notify subscribers via webhooks

    TurnCreationFailed:
      name: TurnCreationFailed
      title: Turn Creation Failed
      summary: CreateTurnWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/TurnCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    ConversationForkRequested:
      name: ConversationForkRequested
      title: Conversation Fork Requested
      summary: Client requested conversation fork via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationForkRequestedPayload'
      x-business-rules:
        - BR-CONV-003

    ConversationForked:
      name: ConversationForked
      title: Conversation Forked Successfully
      summary: ForkConversationWorker created new branch conversation
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationForkedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    ConversationForkFailed:
      name: ConversationForkFailed
      title: Conversation Fork Failed
      summary: ForkConversationWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ConversationForkFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    AlternativeCreationRequested:
      name: AlternativeCreationRequested
      title: Alternative Creation Requested
      summary: Client requested alternative creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeCreationRequestedPayload'
      x-business-rules:
        - BR-ALT-001
        - BR-ALT-002
        - BR-ALT-003

    AlternativeCreated:
      name: AlternativeCreated
      title: Alternative Created Successfully
      summary: CreateAlternativeWorker persisted alternative
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Establish HAS_ALTERNATIVE edge (Turn → Alternative)
        - Establish RESPONDS_TO edge (Alternative → parent Alternative) if responding to prior turn
        - Establish EXECUTED_BY edge (Alternative → Process) if agent turn
        - Trigger async HAS_CONTENT edge creation (Alternative → Episode) via EpisodeIngestionWorker
        - Notify subscribers via webhooks

    AlternativeCreationFailed:
      name: AlternativeCreationFailed
      title: Alternative Creation Failed
      summary: CreateAlternativeWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    AlternativeRegenerationRequested:
      name: AlternativeRegenerationRequested
      title: Alternative Regeneration Requested
      summary: Client requested alternative regeneration via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeRegenerationRequestedPayload'
      x-business-rules:
        - BR-ALT-004

    AlternativeRegenerated:
      name: AlternativeRegenerated
      title: Alternative Regenerated Successfully
      summary: RegenerateAlternativeWorker produced new alternative output
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeRegeneratedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    AlternativeRegenerationFailed:
      name: AlternativeRegenerationFailed
      title: Alternative Regeneration Failed
      summary: RegenerateAlternativeWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/AlternativeRegenerationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    ContextCompressionRequested:
      name: ContextCompressionRequested
      title: WorkingMemory Compression Requested
      summary: Client requested WorkingMemory compression via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ContextCompressionRequestedPayload'
      x-business-rules:
        - BR-MEMORY-001
        - BR-MEMORY-002
        - BR-MEMORY-003
        - BR-MEMORY-004

    ContextCompressed:
      name: ContextCompressed
      title: WorkingMemory Compression Completed
      summary: WorkingMemoryCompressionWorker produced compressed context
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ContextCompressedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Establish HAS_SUMMARY edge (Conversation → Summary)
        - Establish SUMMARIZES edges (Summary → source Episodes)
        - Establish HAS_CONTENT edge (Summary → Episode) for summary content
        - Establish COVERS_UP_TO edge (Summary → boundary Turn)
        - Establish CREATED_BY_PROCESS edge (Summary → compression Process)
        - Notify subscribers via webhooks

    ContextCompressionFailed:
      name: ContextCompressionFailed
      title: WorkingMemory Compression Failed
      summary: WorkingMemoryCompressionWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/ContextCompressionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert SRE team for remediation

    EntityCreationRequested:
      name: EntityCreationRequested
      title: Entity Creation Requested
      summary: Client requested Entity creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityCreationRequestedPayload'
      x-business-rules:
        - BR-ENTITY-001
        - BR-ENTITY-008

    EntityCreated:
      name: EntityCreated
      title: Entity Created Successfully
      summary: CreateEntityWorker persisted Entity
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    EntityCreationFailed:
      name: EntityCreationFailed
      title: Entity Creation Failed
      summary: CreateEntityWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Entity owner

    EntityUpdateRequested:
      name: EntityUpdateRequested
      title: Entity Update Requested
      summary: Client requested Entity update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityUpdateRequestedPayload'
      x-business-rules:
        - BR-ENTITY-002

    EntityUpdated:
      name: EntityUpdated
      title: Entity Updated Successfully
      summary: UpdateEntityWorker applied changes
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    EntityUpdateFailed:
      name: EntityUpdateFailed
      title: Entity Update Failed
      summary: UpdateEntityWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Entity owner

    EntityDeletionRequested:
      name: EntityDeletionRequested
      title: Entity Deletion Requested
      summary: Client requested Entity deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityDeletionRequestedPayload'
      x-business-rules:
        - BR-ENTITY-003

    EntityDeleted:
      name: EntityDeleted
      title: Entity Deleted Successfully
      summary: DeleteEntityWorker removed Entity
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    EntityDeletionFailed:
      name: EntityDeletionFailed
      title: Entity Deletion Failed
      summary: DeleteEntityWorker failed due to references
      contentType: application/json
      payload:
        $ref: '#/components/schemas/EntityDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert dependency owners

    SummaryCreationRequested:
      name: SummaryCreationRequested
      title: Summary Creation Requested
      summary: Client requested Summary creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryCreationRequestedPayload'
      x-business-rules:
        - BR-SUMMARY-001

    SummaryCreated:
      name: SummaryCreated
      title: Summary Created Successfully
      summary: SummaryWorker persisted Summary
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SummaryCreationFailed:
      name: SummaryCreationFailed
      title: Summary Creation Failed
      summary: SummaryWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    SummaryUpdateRequested:
      name: SummaryUpdateRequested
      title: Summary Update Requested
      summary: Client requested Summary update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryUpdateRequestedPayload'
      x-business-rules:
        - BR-SUMMARY-001

    SummaryUpdated:
      name: SummaryUpdated
      title: Summary Updated Successfully
      summary: SummaryWorker updated Summary episode binding
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SummaryUpdateFailed:
      name: SummaryUpdateFailed
      title: Summary Update Failed
      summary: SummaryWorker failed to update Summary
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    SummaryDeletionRequested:
      name: SummaryDeletionRequested
      title: Summary Deletion Requested
      summary: Client requested Summary deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryDeletionRequestedPayload'
      x-business-rules:
        - BR-SUMMARY-001

    SummaryDeleted:
      name: SummaryDeleted
      title: Summary Deleted Successfully
      summary: SummaryWorker deleted Summary
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    SummaryDeletionFailed:
      name: SummaryDeletionFailed
      title: Summary Deletion Failed
      summary: SummaryWorker failed to delete Summary
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SummaryDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert Conversation owner

    IntrospectionCreationRequested:
      name: IntrospectionCreationRequested
      title: Introspection Creation Requested
      summary: Client requested Introspection creation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionCreationRequestedPayload'
      x-business-rules:
        - BR-INTRO-001
        - BR-INTRO-003

    IntrospectionCreated:
      name: IntrospectionCreated
      title: Introspection Created Successfully
      summary: IntrospectionWorker created carousel entry
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionCreatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    IntrospectionCreationFailed:
      name: IntrospectionCreationFailed
      title: Introspection Creation Failed
      summary: IntrospectionWorker encountered error
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionCreationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert user/admin

    IntrospectionUpdateRequested:
      name: IntrospectionUpdateRequested
      title: Introspection Update Requested
      summary: Client requested Introspection update via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionUpdateRequestedPayload'
      x-business-rules:
        - BR-INTRO-001

    IntrospectionUpdated:
      name: IntrospectionUpdated
      title: Introspection Updated Successfully
      summary: IntrospectionWorker updated carousel entry
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionUpdatedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    IntrospectionUpdateFailed:
      name: IntrospectionUpdateFailed
      title: Introspection Update Failed
      summary: IntrospectionWorker failed to update entry
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionUpdateFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert user/admin

    IntrospectionDeletionRequested:
      name: IntrospectionDeletionRequested
      title: Introspection Deletion Requested
      summary: Client requested Introspection deletion via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionDeletionRequestedPayload'
      x-business-rules:
        - BR-INTRO-001

    IntrospectionDeleted:
      name: IntrospectionDeleted
      title: Introspection Deleted Successfully
      summary: IntrospectionWorker deleted carousel entry
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionDeletedPayload'
      x-triggers:
        - Update operation status to 'completed'
        - Notify subscribers via webhooks

    IntrospectionDeletionFailed:
      name: IntrospectionDeletionFailed
      title: Introspection Deletion Failed
      summary: IntrospectionWorker failed to delete entry
      contentType: application/json
      payload:
        $ref: '#/components/schemas/IntrospectionDeletionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert user/admin

    OperationCancellationRequested:
      name: OperationCancellationRequested
      title: Operation Cancellation Requested
      summary: Client requested cancellation of async operation via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/OperationCancellationRequestedPayload'
      x-business-rules:
        - BR-OP-001

    OperationCancelled:
      name: OperationCancelled
      title: Operation Cancelled
      summary: OperationCancellationWorker marked operation as cancelled
      contentType: application/json
      payload:
        $ref: '#/components/schemas/OperationCancelledPayload'
      x-triggers:
        - Update operation status to 'cancelled'
        - Notify subscribers via webhooks

    OperationCancellationFailed:
      name: OperationCancellationFailed
      title: Operation Cancellation Failed
      summary: OperationCancellationWorker could not cancel operation
      contentType: application/json
      payload:
        $ref: '#/components/schemas/OperationCancellationFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert operations team

    WorkerJobSubmissionRequested:
      name: WorkerJobSubmissionRequested
      title: Worker Job Submission Requested
      summary: Client requested worker job submission via API
      contentType: application/json
      payload:
        $ref: '#/components/schemas/WorkerJobSubmissionRequestedPayload'
      x-business-rules:
        - BR-WORKER-001

    WorkerJobSubmitted:
      name: WorkerJobSubmitted
      title: Worker Job Submitted
      summary: WorkerJobScheduler enqueued job
      contentType: application/json
      payload:
        $ref: '#/components/schemas/WorkerJobSubmittedPayload'
      x-triggers:
        - Update operation status to 'queued'
        - Notify monitoring system

    WorkerJobSubmissionFailed:
      name: WorkerJobSubmissionFailed
      title: Worker Job Submission Failed
      summary: WorkerJobScheduler failed to enqueue job
      contentType: application/json
      payload:
        $ref: '#/components/schemas/WorkerJobSubmissionFailedPayload'
      x-triggers:
        - Update operation status to 'failed'
        - Alert operations team

  schemas:
    ServiceCreationRequestedPayload:
      type: object
      required:
        - operationId
        - userId
        - timestamp
        - request
      properties:
        operationId:
          type: string
          format: uuid
          description: Unique ID for operation tracking
        userId:
          type: string
          format: uuid
          description: User initiating creation
        timestamp:
          type: string
          format: date-time
          description: Request received timestamp (ISO 8601)
        correlationId:
          type: string
          format: uuid
          description: Distributed trace ID
        idempotencyKey:
          type: string
          format: uuid
          description: Client-provided idempotency key
        request:
          $ref: '#/components/schemas/ServiceCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateServiceWorker
        retry-policy: none  # Request events not retried
        
    ServiceCreatedPayload:
      type: object
      required:
        - operationId
        - serviceId
        - timestamp
        - service
      properties:
        operationId:
          type: string
          format: uuid
        serviceId:
          type: string
          format: uuid
          description: Created Service ID
        timestamp:
          type: string
          format: date-time
          description: Creation completed timestamp
        correlationId:
          type: string
          format: uuid
        service:
          $ref: '#/components/schemas/Service'
        metrics:
          type: object
          properties:
            executionTimeMs:
              type: number
            validationTimeMs:
              type: number
      x-event-metadata:
        producer: CreateServiceWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
          - MetricsAggregator
        retry-policy: none  # Success events not retried
        
    ServiceCreationFailedPayload:
      type: object
      required:
        - operationId
        - timestamp
        - error
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: '#/components/schemas/StandardError'
        retryCount:
          type: integer
          description: Number of retry attempts made
        retryable:
          type: boolean
          description: Whether operation can be retried
      x-event-metadata:
        producer: CreateServiceWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff  # Transient failures retried
        max-retries: 3
        
    ServiceUpdateRequestedPayload:
      type: object
      required:
        - operationId
        - userId
        - timestamp
        - request
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ServiceUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: UpdateServiceWorker
        retry-policy: none
        
    ServiceUpdatedPayload:
      type: object
      required:
        - operationId
        - serviceId
        - timestamp
        - service
      properties:
        operationId:
          type: string
          format: uuid
        serviceId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        service:
          $ref: './05-openapi.md#/components/schemas/Service'
        metrics:
          type: object
          properties:
            executionTimeMs:
              type: number
      x-event-metadata:
        producer: UpdateServiceWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none
        
    ServiceUpdateFailedPayload:
      type: object
      required:
        - operationId
        - timestamp
        - error
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: UpdateServiceWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3
        
    ServiceDeletionRequestedPayload:
      type: object
      required:
        - operationId
        - userId
        - timestamp
        - request
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/parameters/ServiceIdParam'
      x-event-metadata:
        producer: APIController
        consumer: DeleteServiceWorker
        retry-policy: none
        
    ServiceDeletedPayload:
      type: object
      required:
        - operationId
        - serviceId
        - timestamp
        - service
      properties:
        operationId:
          type: string
          format: uuid
        serviceId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        service:
          $ref: './05-openapi.md#/components/schemas/Service'
      x-event-metadata:
        producer: DeleteServiceWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none
        
    ServiceDeletionFailedPayload:
      type: object
      required:
        - operationId
        - timestamp
        - error
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: DeleteServiceWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3
        
        retry-policy: exponential-backoff
        max-retries: 3

    SecretCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/SecretCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateSecretWorker
        retry-policy: none

    SecretCreatedPayload:
      type: object
      required: [operationId, userId, secretId, timestamp, secret]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        secretId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        secret:
          $ref: './05-openapi.md#/components/schemas/SecretMetadata'
      x-event-metadata:
        producer: CreateSecretWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SecretCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateSecretWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    SecretRotationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/SecretRotateRequest'
      x-event-metadata:
        producer: APIController
        consumer: RotateSecretWorker
        retry-policy: none

    SecretRotatedPayload:
      type: object
      required: [operationId, userId, secretId, timestamp, secret]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        secretId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        secret:
          $ref: './05-openapi.md#/components/schemas/SecretMetadata'
      x-event-metadata:
        producer: RotateSecretWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SecretRotationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: RotateSecretWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    SecretDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/SecretMetadata'
      x-event-metadata:
        producer: APIController
        consumer: DeleteSecretWorker
        retry-policy: none

    SecretDeletedPayload:
      type: object
      required: [operationId, userId, secretId, timestamp, secret]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        secretId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        secret:
          $ref: './05-openapi.md#/components/schemas/SecretMetadata'
      x-event-metadata:
        producer: DeleteSecretWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SecretDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: DeleteSecretWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ToolCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ToolCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateToolWorker
        retry-policy: none

    ToolCreatedPayload:
      type: object
      required: [operationId, toolId, timestamp, tool]
      properties:
        operationId:
          type: string
          format: uuid
        toolId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        tool:
          $ref: './05-openapi.md#/components/schemas/Tool'
      x-event-metadata:
        producer: CreateToolWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ToolCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateToolWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ToolUpdateRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ToolUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: UpdateToolWorker
        retry-policy: none

    ToolUpdatedPayload:
      type: object
      required: [operationId, toolId, timestamp, tool]
      properties:
        operationId:
          type: string
          format: uuid
        toolId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        tool:
          $ref: './05-openapi.md#/components/schemas/Tool'
      x-event-metadata:
        producer: UpdateToolWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ToolUpdateFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: UpdateToolWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ToolDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          type: object
          properties:
            toolId:
              $ref: './05-openapi.md#/paths/~1tools~1{id}/parameters/0/schema'
          required: [toolId]
      x-event-metadata:
        producer: APIController
        consumer: DeleteToolWorker
        retry-policy: none

    ToolDeletedPayload:
      type: object
      required: [operationId, toolId, timestamp, tool]
      properties:
        operationId:
          type: string
          format: uuid
        toolId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        tool:
          $ref: './05-openapi.md#/components/schemas/Tool'
      x-event-metadata:
        producer: DeleteToolWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ToolDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: DeleteToolWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ToolTestRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/paths/~1tools~1{id}~1test/post/requestBody/content/application~1json/schema'
      x-event-metadata:
        producer: APIController
        consumer: ToolTestWorker
        retry-policy: none

    ToolTestResult:
      type: object
      properties:
        status:
          type: string
          enum: [pending, success, failure]
        output:
          type: object
          additionalProperties: true
        logs:
          type: array
          items:
            type: string

    ToolTestedPayload:
      type: object
      required: [operationId, toolId, timestamp, result]
      properties:
        operationId:
          type: string
          format: uuid
        toolId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        result:
          $ref: '#/components/schemas/ToolTestResult'
      x-event-metadata:
        producer: ToolTestWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ToolTestFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: ToolTestWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ProcessCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ProcessCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateProcessWorker
        retry-policy: none

    ProcessCreatedPayload:
      type: object
      required: [operationId, processId, timestamp, process]
      properties:
        operationId:
          type: string
          format: uuid
        processId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        process:
          $ref: './05-openapi.md#/components/schemas/Process'
      x-event-metadata:
        producer: CreateProcessWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ProcessCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateProcessWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ProcessUpdateRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ProcessUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: UpdateProcessWorker
        retry-policy: none

    ProcessUpdatedPayload:
      type: object
      required: [operationId, processId, timestamp, process]
      properties:
        operationId:
          type: string
          format: uuid
        processId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        process:
          $ref: './05-openapi.md#/components/schemas/Process'
      x-event-metadata:
        producer: UpdateProcessWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ProcessUpdateFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: UpdateProcessWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ProcessDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          type: object
          required: [processId]
          properties:
            processId:
              type: string
              format: uuid
      x-event-metadata:
        producer: APIController
        consumer: DeleteProcessWorker
        retry-policy: none

    ProcessDeletedPayload:
      type: object
      required: [operationId, processId, timestamp, process]
      properties:
        operationId:
          type: string
          format: uuid
        processId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        process:
          $ref: './05-openapi.md#/components/schemas/Process'
      x-event-metadata:
        producer: DeleteProcessWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ProcessDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: DeleteProcessWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ProcessExecutionRequest:
      type: object
      required: [processId, initialContext]
      properties:
        processId:
          type: string
          format: uuid
        initialContext:
          type: object
          additionalProperties: true
        conversationId:
          type: string
          format: uuid
          nullable: true

    ProcessExecutionResult:
      type: object
      properties:
        status:
          type: string
          enum: [queued, running, completed, failed]
        outputs:
          type: object
          additionalProperties: true
        metrics:
          type: object
          properties:
            totalSteps:
              type: integer
            durationMs:
              type: number
        logs:
          type: array
          items:
            type: string

    ProcessExecutionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: '#/components/schemas/ProcessExecutionRequest'
      x-event-metadata:
        producer: APIController
        consumer: ProcessExecutionWorker
        retry-policy: none

    ProcessExecutedPayload:
      type: object
      required: [operationId, processId, timestamp, execution]
      properties:
        operationId:
          type: string
          format: uuid
        processId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        execution:
          $ref: '#/components/schemas/ProcessExecutionResult'
      x-event-metadata:
        producer: ProcessExecutionWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
          - MetricsAggregator
        retry-policy: none

    ProcessExecutionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: ProcessExecutionWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ConversationCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ConversationCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateConversationWorker
        retry-policy: none

    ConversationCreatedPayload:
      type: object
      required: [operationId, conversationId, timestamp, conversation]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        conversation:
          $ref: './05-openapi.md#/components/schemas/Conversation'
      x-event-metadata:
        producer: CreateConversationWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ConversationCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateConversationWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    TurnCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/TurnCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateTurnWorker
        retry-policy: none

    TurnCreatedPayload:
      type: object
      required: [operationId, conversationId, turnId, timestamp, turn]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        turnId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        turn:
          $ref: './05-openapi.md#/components/schemas/ConversationTurn'
      x-event-metadata:
        producer: CreateTurnWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    TurnCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateTurnWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    ConversationForkRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/ForkConversationRequest'
      x-event-metadata:
        producer: APIController
        consumer: ForkConversationWorker
        retry-policy: none

    ConversationForkedPayload:
      type: object
      required: [operationId, conversationId, newConversationId, timestamp, conversation]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        newConversationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        conversation:
          $ref: './05-openapi.md#/components/schemas/Conversation'
      x-event-metadata:
        producer: ForkConversationWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ConversationForkFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: ForkConversationWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    AlternativeCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/AlternativeCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateAlternativeWorker
        retry-policy: none

    AlternativeCreatedPayload:
      type: object
      required: [operationId, conversationId, turnId, alternativeId, timestamp, alternative]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        turnId:
          type: string
          format: uuid
        alternativeId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        alternative:
          $ref: './05-openapi.md#/components/schemas/Alternative'
      x-event-metadata:
        producer: CreateAlternativeWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    AlternativeCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateAlternativeWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    AlternativeRegenerateRequest:
      type: object
      properties:
        regenerateReason:
          type: string
          description: Optional note describing why regeneration was requested
      additionalProperties: false

    AlternativeRegenerationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: '#/components/schemas/AlternativeRegenerateRequest'
      x-event-metadata:
        producer: APIController
        consumer: RegenerateAlternativeWorker
        retry-policy: none

    AlternativeRegeneratedPayload:
      type: object
      required: [operationId, conversationId, turnId, alternativeId, timestamp, alternative]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        turnId:
          type: string
          format: uuid
        alternativeId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        alternative:
          $ref: './05-openapi.md#/components/schemas/Alternative'
      x-event-metadata:
        producer: RegenerateAlternativeWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    AlternativeRegenerationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: RegenerateAlternativeWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    WorkingMemoryCompressionRequest:
      type: object
      properties:
        conversationId:
          type: string
          format: uuid
        targetCompressionRatio:
          type: number
          minimum: 0.1
          maximum: 0.9
          default: 0.3
      required: [conversationId]

    ContextCompressionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: '#/components/schemas/WorkingMemoryCompressionRequest'
      x-event-metadata:
        producer: APIController
        consumer: WorkingMemoryCompressionWorker
        retry-policy: none

    ContextCompressedPayload:
      type: object
      required: [operationId, conversationId, timestamp, workingMemory]
      properties:
        operationId:
          type: string
          format: uuid
        conversationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        workingMemory:
          $ref: './05-openapi.md#/components/schemas/WorkingMemory'
      x-event-metadata:
        producer: WorkingMemoryCompressionWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    ContextCompressionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: WorkingMemoryCompressionWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    EntityCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/EntityCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: CreateEntityWorker
        retry-policy: none

    EntityCreatedPayload:
      type: object
      required: [operationId, entityId, timestamp, entity]
      properties:
        operationId:
          type: string
          format: uuid
        entityId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        entity:
          $ref: './05-openapi.md#/components/schemas/Entity'
      x-event-metadata:
        producer: CreateEntityWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    EntityCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: CreateEntityWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    EntityUpdateRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/EntityUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: UpdateEntityWorker
        retry-policy: none

    EntityUpdatedPayload:
      type: object
      required: [operationId, entityId, timestamp, entity]
      properties:
        operationId:
          type: string
          format: uuid
        entityId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        entity:
          $ref: './05-openapi.md#/components/schemas/Entity'
      x-event-metadata:
        producer: UpdateEntityWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    EntityUpdateFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: UpdateEntityWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    EntityDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          type: object
          required: [entityId]
          properties:
            entityId:
              type: string
              format: uuid
      x-event-metadata:
        producer: APIController
        consumer: DeleteEntityWorker
        retry-policy: none

    EntityDeletedPayload:
      type: object
      required: [operationId, entityId, timestamp, entity]
      properties:
        operationId:
          type: string
          format: uuid
        entityId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        entity:
          $ref: './05-openapi.md#/components/schemas/Entity'
      x-event-metadata:
        producer: DeleteEntityWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    EntityDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: DeleteEntityWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    SummaryCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/SummaryCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: SummaryWorker
        retry-policy: none

    SummaryCreatedPayload:
      type: object
      required: [operationId, summaryId, timestamp, summary]
      properties:
        operationId:
          type: string
          format: uuid
        summaryId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        summary:
          $ref: './05-openapi.md#/components/schemas/Summary'
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SummaryCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    SummaryUpdateRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/SummaryUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: SummaryWorker
        retry-policy: none

    SummaryUpdatedPayload:
      type: object
      required: [operationId, summaryId, timestamp, summary]
      properties:
        operationId:
          type: string
          format: uuid
        summaryId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        summary:
          $ref: './05-openapi.md#/components/schemas/Summary'
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SummaryUpdateFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    SummaryDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          type: object
          required: [conversationId, summaryId]
          properties:
            conversationId:
              type: string
              format: uuid
            summaryId:
              type: string
              format: uuid
      x-event-metadata:
        producer: APIController
        consumer: SummaryWorker
        retry-policy: none

    SummaryDeletedPayload:
      type: object
      required: [operationId, summaryId, timestamp, summary]
      properties:
        operationId:
          type: string
          format: uuid
        summaryId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        summary:
          $ref: './05-openapi.md#/components/schemas/Summary'
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    SummaryDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: SummaryWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    IntrospectionCreationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/IntrospectionCreateRequest'
      x-event-metadata:
        producer: APIController
        consumer: IntrospectionWorker
        retry-policy: none

    IntrospectionCreatedPayload:
      type: object
      required: [operationId, introspectionId, timestamp, introspection]
      properties:
        operationId:
          type: string
          format: uuid
        introspectionId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        introspection:
          $ref: './05-openapi.md#/components/schemas/Introspection'
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    IntrospectionCreationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    IntrospectionUpdateRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/components/schemas/IntrospectionUpdateRequest'
      x-event-metadata:
        producer: APIController
        consumer: IntrospectionWorker
        retry-policy: none

    IntrospectionUpdatedPayload:
      type: object
      required: [operationId, introspectionId, timestamp, introspection]
      properties:
        operationId:
          type: string
          format: uuid
        introspectionId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        introspection:
          $ref: './05-openapi.md#/components/schemas/Introspection'
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    IntrospectionUpdateFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    IntrospectionDeletionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          type: object
          required: [introspectionId]
          properties:
            introspectionId:
              type: string
              format: uuid
      x-event-metadata:
        producer: APIController
        consumer: IntrospectionWorker
        retry-policy: none

    IntrospectionDeletedPayload:
      type: object
      required: [operationId, introspectionId, timestamp, introspection]
      properties:
        operationId:
          type: string
          format: uuid
        introspectionId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        introspection:
          $ref: './05-openapi.md#/components/schemas/Introspection'
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    IntrospectionDeletionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: IntrospectionWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    OperationCancellationRequestedPayload:
      type: object
      required: [operationId, userId, timestamp]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        reason:
          type: string
          description: Optional cancellation note
      x-event-metadata:
        producer: APIController
        consumer: OperationCancellationWorker
        retry-policy: none

    OperationCancelledPayload:
      type: object
      required: [operationId, timestamp, status]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        status:
          $ref: './05-openapi.md#/components/schemas/OperationStatus'
      x-event-metadata:
        producer: OperationCancellationWorker
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    OperationCancellationFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
      x-event-metadata:
        producer: OperationCancellationWorker
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3

    WorkerJobSubmissionRequestedPayload:
      type: object
      required: [operationId, userId, timestamp, request]
      properties:
        operationId:
          type: string
          format: uuid
        userId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        idempotencyKey:
          type: string
          format: uuid
        request:
          $ref: './05-openapi.md#/paths/~1workers~1{type}~1jobs/post/requestBody/content/application~1json/schema'
      x-event-metadata:
        producer: APIController
        consumer: WorkerJobScheduler
        retry-policy: none

    WorkerJobSubmittedPayload:
      type: object
      required: [operationId, jobId, timestamp, job]
      properties:
        operationId:
          type: string
          format: uuid
        jobId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        job:
          $ref: './05-openapi.md#/components/schemas/WorkerJobStatus'
      x-event-metadata:
        producer: WorkerJobScheduler
        consumers:
          - OperationStatusUpdater
          - WebhookNotifier
        retry-policy: none

    WorkerJobSubmissionFailedPayload:
      type: object
      required: [operationId, timestamp, error]
      properties:
        operationId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        correlationId:
          type: string
          format: uuid
        error:
          $ref: './05-openapi.md#/components/schemas/ErrorResponse'
        retryCount:
          type: integer
        retryable:
          type: boolean
      x-event-metadata:
        producer: WorkerJobScheduler
        consumers:
          - OperationStatusUpdater
          - AlertingService
        retry-policy: exponential-backoff
        max-retries: 3
        
    ServiceCreateRequest:
      type: object
      # ... (schema from OpenAPI spec)
      
    Service:
      type: object
      # ... (schema from OpenAPI spec)
      
    StandardError:
      type: object
      # ... (schema from OpenAPI spec)

  x-business-rule-mappings:
    BR-SERVICE-001:
      enforced-at: API validation
      enforced-by: ServiceCreationRequested validation
      failure-event: ServiceCreationFailed with code=INVALID_TYPE_PROTOCOL_COMBINATION
      
    BR-SERVICE-002:
      enforced-at: Worker validation
      enforced-by: CreateServiceWorker pre-persistence check
      failure-event: ServiceCreationFailed with code=MISSING_SECRET_REFERENCE

    BR-SERVICE-003:
      enforced-at: Worker health evaluation
      enforced-by: ServiceHealthMonitor job (updates Service.status directly)
      failure-event: none (health endpoint remains synchronous)

    BR-SERVICE-004:
      enforced-at: API validation
      enforced-by: ServiceUpdateRequested validation
      failure-event: ServiceUpdateFailed with code=IMMUTABLE_FIELD_CHANGE

    BR-SERVICE-005:
      enforced-at: Worker validation
      enforced-by: DeleteServiceWorker dependency check
      failure-event: ServiceDeletionFailed with code=DEPENDENT_REFERENCES_EXIST

    BR-SERVICE-006:
      enforced-at: API validation
      enforced-by: ServiceUpdateRequested protocol/schema check
      failure-event: ServiceUpdateFailed with code=PROTOCOL_SCHEMA_MISMATCH

    BR-SECRET-001:
      enforced-at: API validation
      enforced-by: SecretCreationRequested and SecretRotationRequested validation
      failure-event: SecretCreationFailed with code=IMMUTABLE_SECRET_RULE or SecretRotationFailed with code=IMMUTABLE_SECRET_RULE

    BR-SECRET-002:
      enforced-at: Worker validation
      enforced-by: DeleteSecretWorker dependency check
      failure-event: SecretDeletionFailed with code=SECRET_IN_USE

    BR-SECRET-002A:
      enforced-at: API validation
      enforced-by: SecretCreationRequested user scoping (`OWNED_BY` edge target immutable, derived from auth)
      failure-event: SecretCreationFailed with code=USER_SCOPE_MISMATCH

    BR-SECRET-002B:
      enforced-at: Worker execution validation
      enforced-by: ProcessExecutionWorker Tool invocation guard (`OWNED_BY` edge alignment between Secret, Tool, and Conversation)
      failure-event: Execution request rejected with code=SECRET_OWNERSHIP_VIOLATION (no cross-tenant event published)

    BR-SECRET-003:
      enforced-at: API validation
      enforced-by: SecretCreationRequested and SecretRotationRequested type enforcement
      failure-event: SecretCreationFailed with code=INVALID_SECRET_TYPE

    BR-SEC-001:
      enforced-at: API and worker authorization
      enforced-by: Owner filters on Secret reads/rotations/deletes and ProcessExecutionWorker secret access checks
      failure-event: Request rejected with 404 to non-owner (no resource existence leak)

    BR-TOOL-001:
      enforced-at: API validation
      enforced-by: ToolCreationRequested connection param check
      failure-event: ToolCreationFailed with code=INVALID_CONNECTION_PARAMS

    BR-TOOL-002:
      enforced-at: API validation
      enforced-by: ToolCreationRequested input schema validation
      failure-event: ToolCreationFailed with code=INPUT_SCHEMA_MISSING

    BR-TOOL-003:
      enforced-at: API validation
      enforced-by: ToolUpdateRequested output schema validation
      failure-event: ToolUpdateFailed with code=INVALID_OUTPUT_SCHEMA

    BR-TOOL-004:
      enforced-at: Worker validation
      enforced-by: DeleteToolWorker dependency check
      failure-event: ToolDeletionFailed with code=TOOL_IN_USE

    BR-TOOL-005:
      enforced-at: Worker validation
      enforced-by: ToolTestWorker execution guardrails
      failure-event: ToolTestFailed with code=TOOL_TEST_ERROR

    BR-PROCESS-001:
      enforced-at: API validation
      enforced-by: ProcessCreationRequested validation
      failure-event: ProcessCreationFailed with code=INVALID_STEPS

    BR-PROCESS-002:
      enforced-at: API validation
      enforced-by: ProcessUpdateRequested validation
      failure-event: ProcessUpdateFailed with code=INVALID_DEPENDENCIES

    BR-PROCESS-003:
      enforced-at: Worker validation
      enforced-by: DeleteProcessWorker reference check
      failure-event: ProcessDeletionFailed with code=PROCESS_IN_USE

    BR-PROCESS-004:
      enforced-at: Worker execution
      enforced-by: ProcessExecutionWorker step orchestration
      failure-event: ProcessExecutionFailed with code=STEP_ORDER_VIOLATION

    BR-PROCESS-005:
      enforced-at: Worker execution
      enforced-by: ProcessExecutionWorker output validation
      failure-event: ProcessExecutionFailed with code=UNDEFINED_VARIABLE

    BR-PROCESS-006:
      enforced-at: API validation
      enforced-by: ProcessCreationRequested budget validation
      failure-event: ProcessCreationFailed with code=TOKEN_BUDGET_INVALID

    BR-PROCESS-007:
      enforced-at: Worker execution
      enforced-by: ProcessExecutionWorker recursion guard
      failure-event: ProcessExecutionFailed with code=RECURSION_LIMIT_EXCEEDED

    BR-PROCESS-008:
      enforced-at: Worker validation
      enforced-by: DeleteProcessWorker dependency check
      failure-event: ProcessDeletionFailed with code=CONVERSATION_DEPENDENCY_EXISTS

    BR-PROCESS-009:
      enforced-at: API validation
      enforced-by: ProcessUpdateRequested enabled-tool validation
      failure-event: ProcessUpdateFailed with code=DISABLED_TOOL_REFERENCE

    BR-CONV-001:
      enforced-at: API validation
      enforced-by: ConversationCreationRequested process hint validation
      failure-event: ConversationCreationFailed with code=INVALID_PROCESS_HINT

    BR-CONV-002:
      enforced-at: API validation
      enforced-by: ConversationCreationRequested user ownership validation
      failure-event: ConversationCreationFailed with code=INVALID_USER_ID

    BR-CONV-003:
      enforced-at: Worker validation
      enforced-by: ForkConversationWorker provenance checks
      failure-event: ConversationForkFailed with code=FORK_REFERENCES_INVALID

    BR-TURN-001:
      enforced-at: API validation
      enforced-by: TurnCreationRequested ownership validation
      failure-event: TurnCreationFailed with code=TURN_NOT_IN_CONVERSATION

    BR-TURN-002:
      enforced-at: API validation
      enforced-by: TurnCreationRequested membership validation
      failure-event: TurnCreationFailed with code=INVALID_CONVERSATION_LINK

    BR-TURN-004:
      enforced-at: Worker validation
      enforced-by: CreateTurnWorker sequence assignment
      failure-event: TurnCreationFailed with code=SEQUENCE_VIOLATION

    BR-TURN-006:
      enforced-at: Worker validation
      enforced-by: CreateTurnWorker episode association
      failure-event: TurnCreationFailed with code=EPISODE_MISSING

    BR-TURN-008:
      enforced-at: Worker validation
      enforced-by: CreateTurnWorker alternative checks
      failure-event: TurnCreationFailed with code=ALTERNATIVE_RULE_VIOLATION

    BR-ALT-001:
      enforced-at: API validation
      enforced-by: AlternativeCreationRequested immutable reference check
      failure-event: AlternativeCreationFailed with code=ALTERNATIVE_IMMUTABLE_FIELDS

    BR-ALT-002:
      enforced-at: Worker validation
      enforced-by: CreateAlternativeWorker active alternative enforcement
      failure-event: AlternativeCreationFailed with code=ACTIVE_ALTERNATIVE_VIOLATION

    BR-ALT-003:
      enforced-at: API validation
      enforced-by: AlternativeCreationRequested input context validation
      failure-event: AlternativeCreationFailed with code=INPUT_CONTEXT_INVALID

    BR-ALT-004:
      enforced-at: Worker execution
      enforced-by: RegenerateAlternativeWorker lazy regeneration rules
      failure-event: AlternativeRegenerationFailed with code=REGENERATION_DENIED

    BR-MEMORY-001:
      enforced-at: Worker validation
      enforced-by: WorkingMemoryCompressionWorker singleton enforcement
      failure-event: ContextCompressionFailed with code=WORKING_MEMORY_MISSING

    BR-MEMORY-002:
      enforced-at: Worker validation
      enforced-by: WorkingMemoryCompressionWorker immediate path assembly
      failure-event: ContextCompressionFailed with code=IMMEDIATE_PATH_INVALID

    BR-MEMORY-003:
      enforced-at: Worker validation
      enforced-by: WorkingMemoryCompressionWorker token budget calculation
      failure-event: ContextCompressionFailed with code=TOKEN_BUDGET_MISMATCH

    BR-MEMORY-004:
      enforced-at: Worker validation
      enforced-by: WorkingMemoryCompressionWorker reference verification
      failure-event: ContextCompressionFailed with code=CROSS_CONVERSATION_REFERENCE

    BR-ENTITY-001:
      enforced-at: API validation
      enforced-by: EntityCreationRequested validation
      failure-event: EntityCreationFailed with code=INVALID_ENTITY_PAYLOAD

    BR-ENTITY-002:
      enforced-at: API validation
      enforced-by: EntityCreationRequested and EntityUpdateRequested validation
      failure-event: EntityCreationFailed or EntityUpdateFailed with code=ENTITY_REQUIREMENTS_VIOLATION

    BR-ENTITY-003:
      enforced-at: Worker validation
      enforced-by: DeleteEntityWorker reference check
      failure-event: EntityDeletionFailed with code=ENTITY_REFERENCED

    BR-ENTITY-008:
      enforced-at: API validation
      enforced-by: EntityCreationRequested user scope validation
      failure-event: EntityCreationFailed with code=USER_SCOPE_MISMATCH

    BR-SUMMARY-001:
      enforced-at: API/Worker validation
      enforced-by: SummaryCreationRequested and SummaryWorker lifecycle enforcement
      failure-event: SummaryCreationFailed / SummaryUpdateFailed / SummaryDeletionFailed with code=SUMMARY_RULE_VIOLATION

    BR-INTRO-001:
      enforced-at: API/Worker validation
      enforced-by: IntrospectionCreationRequested and IntrospectionWorker carousel guardrails
      failure-event: IntrospectionCreationFailed / IntrospectionUpdateFailed / IntrospectionDeletionFailed with code=INTROSPECTION_RULE_VIOLATION

    BR-INTRO-003:
      enforced-at: API validation
      enforced-by: IntrospectionCreationRequested scope validation
      failure-event: IntrospectionCreationFailed with code=CAROUSEL_SCOPE_VIOLATION

    BR-OP-001:
      enforced-at: Worker validation
      enforced-by: OperationCancellationWorker cancellation eligibility check
      failure-event: OperationCancellationFailed with code=CANNOT_CANCEL

    BR-WORKER-001:
      enforced-at: API validation
      enforced-by: WorkerJobSubmissionRequested validation
      failure-event: WorkerJobSubmissionFailed with code=INVALID_WORKER_JOB_REQUEST

x-event-flow-diagrams:
  service-creation-happy-path: |
    Client → POST /api/v1/services
      → API validates request
      → API publishes ServiceCreationRequested
      → API returns 202 Accepted with operationId
      
    CreateServiceWorker consumes ServiceCreationRequested
      → Worker validates business rules
      → Worker persists Service to Neo4j
      → Worker publishes ServiceCreated
      
    OperationStatusUpdater consumes ServiceCreated
      → Updates operation status to 'completed'
      
    Client polls GET /api/v1/operations/{operationId}
      → Returns 200 with status='completed' and serviceId
      
  service-creation-failure-path: |
    Client → POST /api/v1/services
      → API validates request (PASSES)
      → API publishes ServiceCreationRequested
      → API returns 202 Accepted
      
    CreateServiceWorker consumes ServiceCreationRequested
      → Worker validates business rules (FAILS: BR-SERVICE-001)
      → Worker publishes ServiceCreationFailed
      
    OperationStatusUpdater consumes ServiceCreationFailed
      → Updates operation status to 'failed' with error details
      
    Client polls GET /api/v1/operations/{operationId}
      → Returns 200 with status='failed' and error.rule='BR-SERVICE-001'
```
