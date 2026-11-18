-- ==========================================
-- TASK 3.9: ROLE-BASED ACCESS CONTROL
-- ==========================================

CREATE OR REPLACE FUNCTION public.has_org_role(
    target_org_id UUID,
    allowed_roles TEXT[]
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.organization_members om
        WHERE om.organization_id = target_org_id
          AND om.user_id = auth.uid()
          AND om.status = 'active'
          AND om.role = ANY(allowed_roles)
    );
$$;

-- Restrict function execution
REVOKE ALL ON FUNCTION public.has_org_role(UUID, TEXT[])
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.has_org_role(UUID, TEXT[])
TO authenticated;



CREATE POLICY "Admins can insert organization settings"
ON public.organization_settings
FOR INSERT
TO authenticated
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can update organization settings"
ON public.organization_settings
FOR UPDATE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
)
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can delete organization settings"
ON public.organization_settings
FOR DELETE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can create chatbots"
ON public.chatbots
FOR INSERT
TO authenticated
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can update chatbots"
ON public.chatbots
FOR UPDATE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
)
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can delete chatbots"
ON public.chatbots
FOR DELETE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


-- CHATBOT CHANNELS

CREATE POLICY "Admins can manage chatbot channels"
ON public.chatbot_channels
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_channels.chatbot_id
        AND public.has_org_role(
            cb.organization_id,
            ARRAY['owner', 'admin']
        )
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_channels.chatbot_id
        AND public.has_org_role(
            cb.organization_id,
            ARRAY['owner', 'admin']
        )
    )
);


-- CHATBOT SETTINGS

CREATE POLICY "Admins can manage chatbot settings"
ON public.chatbot_settings
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_settings.chatbot_id
        AND public.has_org_role(
            cb.organization_id,
            ARRAY['owner', 'admin']
        )
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_settings.chatbot_id
        AND public.has_org_role(
            cb.organization_id,
            ARRAY['owner', 'admin']
        )
    )
);

CREATE POLICY "Admins can create AI configurations"
ON public.ai_configurations
FOR INSERT
TO authenticated
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can update AI configurations"
ON public.ai_configurations
FOR UPDATE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
)
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);


CREATE POLICY "Admins can delete AI configurations"
ON public.ai_configurations
FOR DELETE
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);

CREATE POLICY "Admins can manage knowledge bases"
ON public.knowledge_bases
FOR ALL
TO authenticated
USING (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
)
WITH CHECK (
    public.has_org_role(
        organization_id,
        ARRAY['owner', 'admin']
    )
);