-- =====================================================
-- OMNICHANNEL AI CUSTOMER SUPPORT SYSTEM
-- Migration: 001_initial_schema
-- Purpose: Initial database schema
-- Database: Supabase PostgreSQL
-- =====================================================

-- SECTION 1: Required Extensions
-- SECTION 2: Custom Types and Enums
-- SECTION 3: Tenant and Identity Tables
-- SECTION 4: Chatbot and Channel Tables
-- SECTION 5: Conversation Tables
-- SECTION 6: Knowledge Base and RAG Tables
-- SECTION 7: Helpdesk and Ticket Tables
-- SECTION 8: AI Configuration and Observability Tables

-- =============================================
-- BATCH 1: TENANT & IDENTITY
-- =============================================

-- 1. ORGANIZATIONS

CREATE TABLE public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,

    slug TEXT NOT NULL UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 2. ORGANIZATION MEMBERS

CREATE TABLE public.organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    user_id UUID NOT NULL
        REFERENCES auth.users(id)
        ON DELETE CASCADE,

    role TEXT NOT NULL
        CHECK (role IN (
            'owner',
            'admin',
            'support_agent',
            'developer'
        )),

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active',
            'inactive',
            'invited'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organization_id, user_id)
);


-- 3. ORGANIZATION SETTINGS

CREATE TABLE public.organization_settings (
    organization_id UUID PRIMARY KEY
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    settings JSONB NOT NULL DEFAULT '{}'::JSONB,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 4. SUPPORT AGENTS

CREATE TABLE public.support_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_member_id UUID NOT NULL UNIQUE
        REFERENCES public.organization_members(id)
        ON DELETE CASCADE,

    availability_status TEXT NOT NULL DEFAULT 'offline'
        CHECK (availability_status IN (
            'available',
            'busy',
            'offline'
        )),

    skills TEXT[] NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================
-- END OF BATCH 1
-- TENANT & IDENTITY
-- =============================================

-- =============================================
-- BATCH 2: CHATBOT & CHANNELS
-- =============================================

-- 5. CHATBOTS

CREATE TABLE public.chatbots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    created_by_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    name TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 6. CHATBOT CHANNELS

CREATE TABLE public.chatbot_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    chatbot_id UUID NOT NULL
        REFERENCES public.chatbots(id)
        ON DELETE CASCADE,

    channel_type TEXT NOT NULL,

    external_identifier TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (chatbot_id, channel_type, external_identifier)
);


-- 7. CHATBOT SETTINGS

CREATE TABLE public.chatbot_settings (
    chatbot_id UUID PRIMARY KEY
        REFERENCES public.chatbots(id)
        ON DELETE CASCADE,

    settings JSONB NOT NULL DEFAULT '{}'::JSONB,

    system_prompt TEXT,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================
-- END OF BATCH 2
-- CHATBOT & CHANNELS
-- =============================================


-- =============================================
-- BATCH 3: CONVERSATIONS & MESSAGING
-- =============================================


-- 8. CONVERSATIONS

CREATE TABLE public.conversations (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    chatbot_id UUID NOT NULL
        REFERENCES public.chatbots(id)
        ON DELETE CASCADE,

    channel_id UUID
        REFERENCES public.chatbot_channels(id)
        ON DELETE SET NULL,

    assigned_agent_id UUID
        REFERENCES public.support_agents(id)
        ON DELETE SET NULL,

    customer_identifier TEXT,

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active',
            'pending',
            'resolved',
            'closed'
        )),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    last_message_at TIMESTAMPTZ,

    closed_at TIMESTAMPTZ

);


-- 9. CONVERSATION SESSIONS

CREATE TABLE public.conversation_sessions (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL
        REFERENCES public.conversations(id)
        ON DELETE CASCADE,

    session_key TEXT NOT NULL UNIQUE,

    visitor_id TEXT,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    expires_at TIMESTAMPTZ

);


-- 10. MESSAGES

CREATE TABLE public.messages (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL
        REFERENCES public.conversations(id)
        ON DELETE CASCADE,

    session_id UUID
        REFERENCES public.conversation_sessions(id)
        ON DELETE SET NULL,

    sender_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    sender_type TEXT NOT NULL
        CHECK (sender_type IN (
            'customer',
            'bot',
            'agent',
            'system'
        )),

    content TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- =============================================
-- END OF BATCH 3
-- CONVERSATIONS & MESSAGING
-- =============================================


-- =============================================
-- BATCH 4: KNOWLEDGE BASE & RAG
-- =============================================


-- 11. KNOWLEDGE BASES

CREATE TABLE public.knowledge_bases (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    chatbot_id UUID
        REFERENCES public.chatbots(id)
        ON DELETE SET NULL,

    created_by_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    name TEXT NOT NULL,

    description TEXT,

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active',
            'inactive',
            'processing'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- 12. KNOWLEDGE DOCUMENTS

CREATE TABLE public.knowledge_documents (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    knowledge_base_id UUID NOT NULL
        REFERENCES public.knowledge_bases(id)
        ON DELETE CASCADE,

    uploaded_by_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    file_name TEXT NOT NULL,

    storage_path TEXT NOT NULL,

    file_type TEXT,

    file_size BIGINT,

    status TEXT NOT NULL DEFAULT 'uploaded'
        CHECK (status IN (
            'uploaded',
            'processing',
            'completed',
            'failed'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- 13. KNOWLEDGE CHUNKS

CREATE TABLE public.knowledge_chunks (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL
        REFERENCES public.knowledge_documents(id)
        ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL,

    content TEXT NOT NULL,

    token_count INTEGER,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_index)

);


-- 14. DOCUMENT EMBEDDINGS

CREATE TABLE public.document_embeddings (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    chunk_id UUID NOT NULL
        REFERENCES public.knowledge_chunks(id)
        ON DELETE CASCADE,

    embedding VECTOR(384) NOT NULL,

    embedding_model TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (chunk_id, embedding_model)

);


-- =============================================
-- END OF BATCH 4
-- KNOWLEDGE BASE & RAG
-- =============================================

-- =============================================
-- BATCH 5: HELPDESK & TICKET MANAGEMENT
-- =============================================


-- 15. TICKETS

CREATE TABLE public.tickets (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    conversation_id UUID
        REFERENCES public.conversations(id)
        ON DELETE SET NULL,

    created_by_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    assigned_agent_id UUID
        REFERENCES public.support_agents(id)
        ON DELETE SET NULL,

    title TEXT NOT NULL,

    description TEXT,

    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN (
            'open',
            'in_progress',
            'pending',
            'resolved',
            'closed'
        )),

    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN (
            'low',
            'medium',
            'high',
            'urgent'
        )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    resolved_at TIMESTAMPTZ

);


-- 16. TICKET COMMENTS

CREATE TABLE public.ticket_comments (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    ticket_id UUID NOT NULL
        REFERENCES public.tickets(id)
        ON DELETE CASCADE,

    author_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    author_type TEXT NOT NULL
        CHECK (author_type IN (
            'customer',
            'agent',
            'system'
        )),

    body TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- 17. TICKET ASSIGNMENTS

CREATE TABLE public.ticket_assignments (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    ticket_id UUID NOT NULL
        REFERENCES public.tickets(id)
        ON DELETE CASCADE,

    support_agent_id UUID NOT NULL
        REFERENCES public.support_agents(id)
        ON DELETE RESTRICT,

    assigned_by_member_id UUID
        REFERENCES public.organization_members(id)
        ON DELETE SET NULL,

    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    unassigned_at TIMESTAMPTZ

);


-- =============================================
-- END OF BATCH 5
-- HELPDESK & TICKET MANAGEMENT
-- =============================================


-- =============================================
-- BATCH 6: AI CONFIGURATION & OBSERVABILITY
-- =============================================


-- 18. AI CONFIGURATIONS

CREATE TABLE public.ai_configurations (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    chatbot_id UUID
        REFERENCES public.chatbots(id)
        ON DELETE CASCADE,

    provider TEXT NOT NULL,

    model_name TEXT NOT NULL,

    secret_reference TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- 19. AI USAGE LOGS

CREATE TABLE public.ai_usage_logs (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    chatbot_id UUID
        REFERENCES public.chatbots(id)
        ON DELETE SET NULL,

    conversation_id UUID
        REFERENCES public.conversations(id)
        ON DELETE SET NULL,

    message_id UUID
        REFERENCES public.messages(id)
        ON DELETE SET NULL,

    ai_configuration_id UUID
        REFERENCES public.ai_configurations(id)
        ON DELETE SET NULL,

    prompt_tokens INTEGER NOT NULL DEFAULT 0,

    completion_tokens INTEGER NOT NULL DEFAULT 0,

    total_tokens INTEGER NOT NULL DEFAULT 0,

    estimated_cost NUMERIC(12, 6) NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- 20. AI EXECUTION LOGS

CREATE TABLE public.ai_execution_logs (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    organization_id UUID NOT NULL
        REFERENCES public.organizations(id)
        ON DELETE CASCADE,

    chatbot_id UUID
        REFERENCES public.chatbots(id)
        ON DELETE SET NULL,

    conversation_id UUID
        REFERENCES public.conversations(id)
        ON DELETE SET NULL,

    message_id UUID
        REFERENCES public.messages(id)
        ON DELETE SET NULL,

    ai_configuration_id UUID
        REFERENCES public.ai_configurations(id)
        ON DELETE SET NULL,

    task TEXT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN (
            'success',
            'failed',
            'pending'
        )),

    latency_ms INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- =============================================
-- END OF BATCH 6
-- AI CONFIGURATION & OBSERVABILITY
-- =============================================
