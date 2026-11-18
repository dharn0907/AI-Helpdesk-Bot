# Database Design — Omnichannel AI-Powered Customer Support System

## 1. Scope and status

This document describes the **proposed logical database design** for the omnichannel customer-support platform. It targets **Supabase PostgreSQL**, with **pgvector** for retrieval-augmented generation (RAG).

The design supports multiple organizations (tenants), each managing chatbots, channels, conversations, knowledge bases, tickets, support agents, and AI configuration/usage.

> **Important:** This is a design baseline derived from the agreed project architecture, not a verified dump of the live Supabase schema. Compare it with the SQL migrations currently in the repository before treating it as the implemented schema.

## 2. Design principles

- **Multi-tenancy:** tenant-owned records are associated with `organization_id` directly or through a parent record.
- **Tenant isolation:** implement Row Level Security (RLS) policies for organization-scoped access. Application filters alone are not a security boundary.
- **Supabase Auth:** `organization_members.user_id` references the managed `auth.users.id`. Supabase owns that table; it is not recreated in the application schema.
- **Secrets:** never store provider API keys in ordinary configuration JSON. Store a secret-manager reference.
- **RAG:** documents are split into chunks; embeddings are stored separately so the embedding model and vector dimension can be managed explicitly.
- **Auditability:** ticket assignment history and AI execution/usage logs are separate records.

## 3. Entity catalogue

| Entity | Purpose |
|---|---|
| `organizations` | Tenant/company account. |
| `organization_members` | Maps Supabase Auth users to an organization and role. |
| `organization_settings` | One-to-one organization-level preferences. |
| `chatbots` | A chatbot owned by an organization. |
| `chatbot_channels` | Deployment/integration channels for a chatbot (website, WhatsApp, etc.). |
| `chatbot_settings` | One-to-one chatbot behavior and presentation settings. |
| `support_agents` | Helpdesk agent profile for an organization member. |
| `conversations` | Customer interaction routed through a chatbot/channel. |
| `conversation_sessions` | Visitor/session instances associated with a conversation. |
| `messages` | Individual customer, bot, agent, or system messages. |
| `knowledge_bases` | Organization knowledge collection, optionally associated with a chatbot. |
| `knowledge_documents` | Uploaded source documents in a knowledge base. |
| `knowledge_chunks` | Text segments extracted from a document. |
| `document_embeddings` | Vector representation(s) of knowledge chunks. |
| `tickets` | Support issue created from a conversation or another source. |
| `ticket_comments` | Discussion and status notes on a ticket. |
| `ticket_assignments` | Assignment history between tickets and support agents. |
| `ai_configurations` | Organization/chatbot LLM provider and model configuration. |
| `ai_usage_logs` | Token and estimated-cost accounting. |
| `ai_execution_logs` | Operational log for AI tasks, latency, and failures. |

## 4. Relationships and cardinalities

Cardinality notation: **1:N** means one parent can have many children; **1:1** means one-to-one; **0..1** means optional.

| Parent | Child | Cardinality | FK / rule |
|---|---|---:|---|
| `organizations` | `organization_members` | 1:N | `organization_members.organization_id` |
| `organizations` | `organization_settings` | 1:1 | `organization_settings.organization_id` is PK and FK |
| `organizations` | `chatbots` | 1:N | `chatbots.organization_id` |
| `organizations` | `knowledge_bases` | 1:N | `knowledge_bases.organization_id` |
| `organizations` | `tickets` | 1:N | `tickets.organization_id` |
| `organizations` | `ai_configurations` | 1:N | `ai_configurations.organization_id` |
| `organizations` | `conversations` | 1:N | `conversations.organization_id` |
| `organizations` | `ai_usage_logs` / `ai_execution_logs` | 1:N | Each log carries `organization_id` |
| `organization_members` | `support_agents` | 1:0..1 | `support_agents.organization_member_id` is unique |
| `organization_members` | `chatbots` | 1:N (optional creator) | `chatbots.created_by_member_id` |
| `organization_members` | `messages` | 1:N (optional sender) | `messages.sender_member_id` |
| `organization_members` | `tickets` | 1:N (optional creator) | `tickets.created_by_member_id` |
| `chatbots` | `chatbot_channels` | 1:N | `chatbot_channels.chatbot_id` |
| `chatbots` | `chatbot_settings` | 1:1 | `chatbot_settings.chatbot_id` is PK and FK |
| `chatbots` | `conversations` | 1:N | `conversations.chatbot_id` |
| `chatbots` | `knowledge_bases` | 1:N or optional association | `knowledge_bases.chatbot_id` is nullable |
| `chatbots` | `ai_configurations` | 1:N or optional association | `ai_configurations.chatbot_id` is nullable |
| `chatbot_channels` | `conversations` | 1:N; conversation channel optional | `conversations.channel_id` |
| `conversations` | `conversation_sessions` | 1:N | `conversation_sessions.conversation_id` |
| `conversations` | `messages` | 1:N | `messages.conversation_id` |
| `conversations` | `tickets` | 1:N; ticket link optional | `tickets.conversation_id` is nullable |
| `conversations` | `ai_usage_logs` / `ai_execution_logs` | 1:N; log link optional | Each log has nullable `conversation_id` |
| `conversation_sessions` | `messages` | 1:N; message session optional | `messages.session_id` is nullable |
| `support_agents` | `conversations` | 1:N; assignment optional | `conversations.assigned_agent_id` |
| `support_agents` | `tickets` | 1:N; assignment optional | `tickets.assigned_agent_id` |
| `knowledge_bases` | `knowledge_documents` | 1:N | `knowledge_documents.knowledge_base_id` |
| `knowledge_documents` | `knowledge_chunks` | 1:N | `knowledge_chunks.document_id` |
| `knowledge_chunks` | `document_embeddings` | 1:N across embedding models | `document_embeddings.chunk_id`; unique per chunk/model |
| `tickets` | `ticket_comments` | 1:N | `ticket_comments.ticket_id` |
| `tickets` | `ticket_assignments` | 1:N | `ticket_assignments.ticket_id` |
| `support_agents` | `ticket_assignments` | 1:N | `ticket_assignments.support_agent_id` |
| `ai_configurations` | `ai_usage_logs` / `ai_execution_logs` | 1:N; log reference optional | `ai_configuration_id` |
| `messages` | `ai_usage_logs` / `ai_execution_logs` | 1:N; log reference optional | `message_id` |

## 5. Important constraints and implementation notes

1. **Organization consistency:** every FK path must remain within the same organization. For example, a ticket's `organization_id` must match the organization of its conversation and assigned agent. Enforce this with composite constraints, carefully designed triggers, or transactional application validation plus RLS; simple independent FKs do not guarantee tenant consistency.
2. **Support-agent uniqueness:** `support_agents.organization_member_id` is unique, so one organization member has at most one agent profile.
3. **Assignment history:** `ticket_assignments` records each assignment period. `tickets.assigned_agent_id` is the current assignment shortcut. Keep both in sync transactionally.
4. **Conversation ownership:** `conversations.chatbot_id` is required; `channel_id` is optional to support conversations created through internal/test flows.
5. **Ticket origin:** `tickets.conversation_id` is nullable to allow tickets created from email, manual entry, or future channels.
6. **Vector dimension:** `vector(1024)` is a placeholder dimension. It must match the embedding model actually selected. Do not deploy this dimension blindly.
7. **Indexes:** add indexes to frequently filtered FKs and tenant/status/time combinations. The DBML lists the baseline indexes; tune them using query plans.
8. **Deletion policy:** decide explicitly whether to cascade, restrict, or soft-delete for each relationship before production. For customer-support audit records, avoid cascading deletion of messages/tickets unintentionally.
9. **RLS:** enable RLS on tenant-owned tables. Policies should derive organization membership from the authenticated user and should also cover inserts/updates/deletes.
10. **Supabase Storage:** `knowledge_documents.storage_path` points to an object in a Storage bucket. Storage objects are managed by Supabase Storage; they are not represented as a normal application table here.

## 6. Suggested lifecycle flows

### Chat and escalation
1. A customer starts a `conversation` against a `chatbot` and optionally a `chatbot_channel`.
2. A `conversation_session` tracks the visitor/session context.
3. Each interaction is stored in `messages`.
4. If automated resolution is insufficient, create a `ticket` linked to the conversation.
5. Assign the ticket to a `support_agent`; record each assignment in `ticket_assignments`.
6. Store agent/customer/system updates in `ticket_comments`.

### Knowledge ingestion and retrieval
1. Create a `knowledge_base` for an organization (optionally associate it with a chatbot).
2. Register each uploaded file in `knowledge_documents`, with its Storage object path.
3. Split document text into `knowledge_chunks`.
4. Generate one or more model-specific vectors in `document_embeddings`.
5. Retrieval queries the embedding column using pgvector and applies organization/knowledge-base authorization filters.

### AI execution and metering
1. Resolve the active `ai_configuration` for the organization/chatbot.
2. Execute the task (intent classification, retrieval, response generation, etc.).
3. Record operational outcome in `ai_execution_logs`.
4. Record token/cost usage in `ai_usage_logs`.

## 7. Files

- `database_erd.dbml` — editable DBML source for the logical ER diagram.
- `database_erd.png` — visual ER diagram generated from the same entity/relationship baseline.
- This document — relationship and cardinality reference.

## 8. Before production

- Compare every table and column with the actual SQL migrations.
- Confirm the embedding provider and vector dimension.
- Add explicit CHECK constraints or PostgreSQL enums for roles, statuses, priorities, channel types, and sender types.
- Add tenant-consistency constraints and test RLS with multiple organizations.
- Decide retention, deletion, and audit policies.
- Generate the final ERD from the deployed schema after migrations are applied.
