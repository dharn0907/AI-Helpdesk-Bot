-- ==========================================
-- MIGRATION: 004_enable_rls
-- PROJECT: Omnichannel AI Support System
-- ==========================================

-- Enable RLS

ALTER TABLE public.organizations
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.organization_members
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.organization_settings
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.chatbots
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.chatbot_channels
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.chatbot_settings
ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.support_agents
ENABLE ROW LEVEL SECURITY;


-- ==========================================
-- ORGANIZATION MEMBERSHIP FUNCTION
-- ==========================================

CREATE OR REPLACE FUNCTION public.is_org_member(
    target_org_id UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY DEFINER
STABLE
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.organization_members om
        WHERE om.organization_id = target_org_id
          AND om.user_id = (SELECT auth.uid())
          AND om.status = 'active'
    );
$$;


-- ==========================================
-- ORGANIZATIONS
-- ==========================================

CREATE POLICY "Members can view their organizations"
ON public.organizations
FOR SELECT
TO authenticated
USING (
    public.is_org_member(id)
);


-- ==========================================
-- ORGANIZATION MEMBERS
-- ==========================================

CREATE POLICY "Members can view organization members"
ON public.organization_members
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


-- ==========================================
-- ORGANIZATION SETTINGS
-- ==========================================

CREATE POLICY "Members can view organization settings"
ON public.organization_settings
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


-- ==========================================
-- CHATBOTS
-- ==========================================

CREATE POLICY "Members can view organization chatbots"
ON public.chatbots
FOR SELECT
TO authenticated
USING (
    public.is_org_member(organization_id)
);


-- ==========================================
-- CHATBOT CHANNELS
-- ==========================================

CREATE POLICY "Members can view chatbot channels"
ON public.chatbot_channels
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_channels.chatbot_id
          AND public.is_org_member(cb.organization_id)
    )
);


-- ==========================================
-- CHATBOT SETTINGS
-- ==========================================

CREATE POLICY "Members can view chatbot settings"
ON public.chatbot_settings
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chatbots cb
        WHERE cb.id = chatbot_settings.chatbot_id
          AND public.is_org_member(cb.organization_id)
    )
);


-- ==========================================
-- SUPPORT AGENTS
-- ==========================================

CREATE POLICY "Members can view organization agents"
ON public.support_agents
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.organization_members om
        WHERE om.id = support_agents.organization_member_id
          AND public.is_org_member(om.organization_id)
    )
);