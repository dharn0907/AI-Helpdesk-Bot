-- =============================================
-- MIGRATION 004
-- MULTI-TENANT REFERENTIAL INTEGRITY
-- =============================================

BEGIN;

-- 1. Add composite unique constraints

ALTER TABLE public.chatbots
ADD CONSTRAINT uq_chatbots_org_id
UNIQUE (organization_id, id);

ALTER TABLE public.conversations
ADD CONSTRAINT uq_conversations_org_id
UNIQUE (organization_id, id);

-- 2. Add organization ownership to support_agents

ALTER TABLE public.support_agents
ADD COLUMN organization_id UUID;

-- Populate organization_id using existing membership data

UPDATE public.support_agents sa
SET organization_id = om.organization_id
FROM public.organization_members om
WHERE sa.organization_member_id = om.id;

-- Ensure every support agent has an organization

ALTER TABLE public.support_agents
ALTER COLUMN organization_id SET NOT NULL;

-- 3. Ensure support agents belong to valid memberships

ALTER TABLE public.support_agents
ADD CONSTRAINT uq_support_agents_org_id
UNIQUE (organization_id, id);

ALTER TABLE public.support_agents
ADD CONSTRAINT fk_support_agent_membership_org
FOREIGN KEY (organization_id, organization_member_id)
REFERENCES public.organization_members
(organization_id, id);

-- 4. Validate chatbot ownership in conversations

ALTER TABLE public.conversations
ADD CONSTRAINT fk_conversation_chatbot_org
FOREIGN KEY (organization_id, chatbot_id)
REFERENCES public.chatbots
(organization_id, id);

-- 5. Validate support-agent ownership in conversations

ALTER TABLE public.conversations
ADD CONSTRAINT fk_conversation_agent_org
FOREIGN KEY (organization_id, assigned_agent_id)
REFERENCES public.support_agents
(organization_id, id);

-- 6. Validate conversation ownership in tickets

ALTER TABLE public.tickets
ADD CONSTRAINT fk_ticket_conversation_org
FOREIGN KEY (organization_id, conversation_id)
REFERENCES public.conversations
(organization_id, id);

-- 7. Validate support-agent ownership in tickets

ALTER TABLE public.tickets
ADD CONSTRAINT fk_ticket_agent_org
FOREIGN KEY (organization_id, assigned_agent_id)
REFERENCES public.support_agents
(organization_id, id);

COMMIT;

-- =============================================
-- END MIGRATION 004
-- =============================================

