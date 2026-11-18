-- ==========================================
-- TASK 3.8: EXTEND ROW LEVEL SECURITY
-- ==========================================

-- 1. Enable RLS on remaining tables

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_embeddings ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticket_assignments ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ai_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_execution_logs ENABLE ROW LEVEL SECURITY;


-- ==========================================
-- 2. CONVERSATION POLICIES
-- ==========================================

CREATE POLICY "Members can view organization conversations"
ON public.conversations
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


CREATE POLICY "Members can view conversation sessions"
ON public.conversation_sessions
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.conversations c
        WHERE c.id = conversation_sessions.conversation_id
        AND public.is_org_member(c.organization_id)
    )
);


CREATE POLICY "Members can view conversation messages"
ON public.messages
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.conversations c
        WHERE c.id = messages.conversation_id
        AND public.is_org_member(c.organization_id)
    )
);


-- ==========================================
-- 3. KNOWLEDGE BASE POLICIES
-- ==========================================

CREATE POLICY "Members can view knowledge bases"
ON public.knowledge_bases
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


CREATE POLICY "Members can view knowledge documents"
ON public.knowledge_documents
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.knowledge_bases kb
        WHERE kb.id = knowledge_documents.knowledge_base_id
        AND public.is_org_member(kb.organization_id)
    )
);


CREATE POLICY "Members can view knowledge chunks"
ON public.knowledge_chunks
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.knowledge_documents kd
        JOIN public.knowledge_bases kb
            ON kb.id = kd.knowledge_base_id
        WHERE kd.id = knowledge_chunks.document_id
        AND public.is_org_member(kb.organization_id)
    )
);


CREATE POLICY "Members can view document embeddings"
ON public.document_embeddings
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.knowledge_chunks kc
        JOIN public.knowledge_documents kd
            ON kd.id = kc.document_id
        JOIN public.knowledge_bases kb
            ON kb.id = kd.knowledge_base_id
        WHERE kc.id = document_embeddings.chunk_id
        AND public.is_org_member(kb.organization_id)
    )
);


-- ==========================================
-- 4. HELPDESK POLICIES
-- ==========================================

CREATE POLICY "Members can view organization tickets"
ON public.tickets
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


CREATE POLICY "Members can view ticket comments"
ON public.ticket_comments
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.tickets t
        WHERE t.id = ticket_comments.ticket_id
        AND public.is_org_member(t.organization_id)
    )
);


CREATE POLICY "Members can view ticket assignments"
ON public.ticket_assignments
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.tickets t
        WHERE t.id = ticket_assignments.ticket_id
        AND public.is_org_member(t.organization_id)
    )
);


-- ==========================================
-- 5. AI MANAGEMENT POLICIES
-- ==========================================

CREATE POLICY "Members can view AI configurations"
ON public.ai_configurations
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


CREATE POLICY "Members can view AI usage logs"
ON public.ai_usage_logs
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


CREATE POLICY "Members can view AI execution logs"
ON public.ai_execution_logs
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


-- ==========================================
-- END OF TASK 3.8
-- ==========================================