-- AGENT CONVERSATION ACCESS

CREATE POLICY "Agents can view assigned conversations"
ON public.conversations
FOR SELECT
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
    OR (
        public.has_org_role(
            organization_id,
            ARRAY['agent']
        )
        AND EXISTS (
            SELECT 1
            FROM public.support_agents sa
            WHERE sa.id = conversations.assigned_agent_id
              AND sa.organization_member_id IN (
                  SELECT om.id
                  FROM public.organization_members om
                  WHERE om.user_id = auth.uid()
                    AND om.organization_id = conversations.organization_id
                    AND om.status = 'active'
              )
        )
    )
);

CREATE POLICY "Agents can view assigned conversation messages"
ON public.messages
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.conversations c
        JOIN public.support_agents sa
            ON sa.id = c.assigned_agent_id
        JOIN public.organization_members om
            ON om.id = sa.organization_member_id
        WHERE c.id = messages.conversation_id
          AND om.user_id = auth.uid()
          AND om.status = 'active'
          AND om.role = 'agent'
    )
);

CREATE POLICY "Agents can view assigned tickets"
ON public.tickets
FOR SELECT
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
    OR (
        public.has_org_role(
            organization_id,
            ARRAY['agent']
        )
        AND EXISTS (
            SELECT 1
            FROM public.support_agents sa
            JOIN public.organization_members om
                ON om.id = sa.organization_member_id
            WHERE sa.id = tickets.assigned_agent_id
              AND om.user_id = auth.uid()
              AND om.status = 'active'
        )
    )
);

CREATE POLICY "Authorized users can update tickets"
ON public.tickets
FOR UPDATE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
    OR EXISTS (
        SELECT 1
        FROM public.support_agents sa
        JOIN public.organization_members om
            ON om.id = sa.organization_member_id
        WHERE sa.id = tickets.assigned_agent_id
          AND om.user_id = auth.uid()
          AND om.organization_id = tickets.organization_id
          AND om.role = 'agent'
          AND om.status = 'active'
    )
)
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
    OR EXISTS (
        SELECT 1
        FROM public.support_agents sa
        JOIN public.organization_members om
            ON om.id = sa.organization_member_id
        WHERE sa.id = tickets.assigned_agent_id
          AND om.user_id = auth.uid()
          AND om.organization_id = tickets.organization_id
          AND om.role = 'agent'
          AND om.status = 'active'
    )
);

CREATE POLICY "Agents can comment on assigned tickets"
ON public.ticket_comments
FOR INSERT
TO authenticated
WITH CHECK (
    author_type = 'agent'
    AND EXISTS (
        SELECT 1
        FROM public.tickets t
        JOIN public.support_agents sa
            ON sa.id = t.assigned_agent_id
        JOIN public.organization_members om
            ON om.id = sa.organization_member_id
        WHERE t.id = ticket_comments.ticket_id
          AND om.user_id = auth.uid()
          AND om.status = 'active'
          AND om.role = 'agent'
          AND ticket_comments.author_member_id = om.id
    )
);