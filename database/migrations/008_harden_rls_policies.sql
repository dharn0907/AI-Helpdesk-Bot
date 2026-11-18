CREATE OR REPLACE FUNCTION public.can_access_conversation(
    target_conversation_id UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.conversations c
        JOIN public.organization_members om
            ON om.organization_id = c.organization_id
        WHERE c.id = target_conversation_id
          AND om.user_id = auth.uid()
          AND om.status = 'active'
          AND (
              om.role IN ('owner', 'admin', 'member')
              OR (
                  om.role = 'agent'
                  AND EXISTS (
                      SELECT 1
                      FROM public.support_agents sa
                      WHERE sa.id = c.assigned_agent_id
                        AND sa.organization_member_id = om.id
                  )
              )
          )
    );
$$;

REVOKE ALL ON FUNCTION public.can_access_conversation(UUID)
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.can_access_conversation(UUID)
TO authenticated;

CREATE OR REPLACE FUNCTION public.can_access_ticket(
    target_ticket_id UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.tickets t
        JOIN public.organization_members om
            ON om.organization_id = t.organization_id
        WHERE t.id = target_ticket_id
          AND om.user_id = auth.uid()
          AND om.status = 'active'
          AND (
              om.role IN ('owner', 'admin', 'member')
              OR (
                  om.role = 'agent'
                  AND EXISTS (
                      SELECT 1
                      FROM public.support_agents sa
                      WHERE sa.id = t.assigned_agent_id
                        AND sa.organization_member_id = om.id
                  )
              )
          )
    );
$$;

REVOKE ALL ON FUNCTION public.can_access_ticket(UUID)
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.can_access_ticket(UUID)
TO authenticated;

-- CONVERSATIONS
DROP POLICY IF EXISTS
"Members can view organization conversations"
ON public.conversations;

DROP POLICY IF EXISTS
"Agents can view assigned conversations"
ON public.conversations;


-- MESSAGES
DROP POLICY IF EXISTS
"Members can view conversation messages"
ON public.messages;

DROP POLICY IF EXISTS
"Agents can view assigned conversation messages"
ON public.messages;


-- CONVERSATION SESSIONS
DROP POLICY IF EXISTS
"Members can view conversation sessions"
ON public.conversation_sessions;


-- TICKETS
DROP POLICY IF EXISTS
"Members can view organization tickets"
ON public.tickets;

DROP POLICY IF EXISTS
"Agents can view assigned tickets"
ON public.tickets;


-- TICKET COMMENTS
DROP POLICY IF EXISTS
"Members can view ticket comments"
ON public.ticket_comments;


-- TICKET ASSIGNMENTS
DROP POLICY IF EXISTS
"Members can view ticket assignments"
ON public.ticket_assignments;

-- CONVERSATIONS

CREATE POLICY "Authorized users can view conversations"
ON public.conversations
FOR SELECT
TO authenticated
USING (
    public.can_access_conversation(id)
);


-- MESSAGES

CREATE POLICY "Authorized users can view messages"
ON public.messages
FOR SELECT
TO authenticated
USING (
    public.can_access_conversation(conversation_id)
);


-- CONVERSATION SESSIONS

CREATE POLICY "Authorized users can view sessions"
ON public.conversation_sessions
FOR SELECT
TO authenticated
USING (
    public.can_access_conversation(conversation_id)
);


-- TICKETS

CREATE POLICY "Authorized users can view tickets"
ON public.tickets
FOR SELECT
TO authenticated
USING (
    public.can_access_ticket(id)
);


-- TICKET COMMENTS

CREATE POLICY "Authorized users can view ticket comments"
ON public.ticket_comments
FOR SELECT
TO authenticated
USING (
    public.can_access_ticket(ticket_id)
);


-- TICKET ASSIGNMENTS

CREATE POLICY "Authorized users can view ticket assignments"
ON public.ticket_assignments
FOR SELECT
TO authenticated
USING (
    public.can_access_ticket(ticket_id)
);
