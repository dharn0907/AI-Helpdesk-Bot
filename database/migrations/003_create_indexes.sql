-- =====================================================
-- Migration: 003_create_indexes
-- Project: Omnichannel AI-Powered Customer Support
-- Database: Supabase PostgreSQL
-- Purpose: Improve database query performance
-- =====================================================


-- ORGANIZATION INDEXES

CREATE INDEX IF NOT EXISTS idx_org_members_user
ON public.organization_members(user_id);

CREATE INDEX IF NOT EXISTS idx_org_members_org
ON public.organization_members(organization_id);


-- CHATBOT INDEXES

CREATE INDEX IF NOT EXISTS idx_chatbots_org
ON public.chatbots(organization_id);

CREATE INDEX IF NOT EXISTS idx_chatbots_org_name
ON public.chatbots(organization_id, name);

CREATE INDEX IF NOT EXISTS idx_chatbot_channels_chatbot
ON public.chatbot_channels(chatbot_id);


-- CONVERSATION INDEXES

CREATE INDEX IF NOT EXISTS idx_conversations_org
ON public.conversations(organization_id);

CREATE INDEX IF NOT EXISTS idx_conversations_chatbot
ON public.conversations(chatbot_id);

CREATE INDEX IF NOT EXISTS idx_conversations_agent
ON public.conversations(assigned_agent_id);

CREATE INDEX IF NOT EXISTS idx_conversations_org_status
ON public.conversations(organization_id, status);


-- MESSAGE INDEXES

CREATE INDEX IF NOT EXISTS idx_messages_conversation
ON public.messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
ON public.messages(conversation_id, created_at);


-- KNOWLEDGE BASE INDEXES

CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org
ON public.knowledge_bases(organization_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_bases_chatbot
ON public.knowledge_bases(chatbot_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_base
ON public.knowledge_documents(knowledge_base_id);


-- TICKET INDEXES

CREATE INDEX IF NOT EXISTS idx_tickets_org
ON public.tickets(organization_id);

CREATE INDEX IF NOT EXISTS idx_tickets_conversation
ON public.tickets(conversation_id);

CREATE INDEX IF NOT EXISTS idx_tickets_agent
ON public.tickets(assigned_agent_id);

CREATE INDEX IF NOT EXISTS idx_tickets_org_status_priority
ON public.tickets(organization_id, status, priority);


-- TICKET MANAGEMENT INDEXES

CREATE INDEX IF NOT EXISTS idx_ticket_comments_ticket
ON public.ticket_comments(ticket_id);

CREATE INDEX IF NOT EXISTS idx_ticket_assignments_ticket
ON public.ticket_assignments(ticket_id);

CREATE INDEX IF NOT EXISTS idx_ticket_assignments_agent
ON public.ticket_assignments(support_agent_id);


-- AI CONFIGURATION INDEXES

CREATE INDEX IF NOT EXISTS idx_ai_configurations_org
ON public.ai_configurations(organization_id);

CREATE INDEX IF NOT EXISTS idx_ai_configurations_chatbot
ON public.ai_configurations(chatbot_id);


-- AI USAGE INDEXES

CREATE INDEX IF NOT EXISTS idx_ai_usage_org
ON public.ai_usage_logs(organization_id);

CREATE INDEX IF NOT EXISTS idx_ai_usage_conversation
ON public.ai_usage_logs(conversation_id);

CREATE INDEX IF NOT EXISTS idx_ai_usage_created
ON public.ai_usage_logs(created_at);


-- AI EXECUTION INDEXES

CREATE INDEX IF NOT EXISTS idx_ai_execution_org
ON public.ai_execution_logs(organization_id);

CREATE INDEX IF NOT EXISTS idx_ai_execution_conversation
ON public.ai_execution_logs(conversation_id);

CREATE INDEX IF NOT EXISTS idx_ai_execution_created
ON public.ai_execution_logs(created_at);


-- =====================================================
-- END OF MIGRATION
-- =====================================================