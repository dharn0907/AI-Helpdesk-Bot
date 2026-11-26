const BASE = 'http://127.0.0.1:8000'
const tokenKey = 'orbit_internal_token'

export const isDemo = !BASE
export const getToken = () => sessionStorage.getItem(tokenKey)
export const setToken = value => value ? sessionStorage.setItem(tokenKey,value) : sessionStorage.removeItem(tokenKey)

export async function api(path, options={}) {
  if (!BASE) throw new Error('API base URL is not configured.')
  const response = await fetch(`${BASE.replace(/\/$/,'')}${path}`, {
    ...options,
    headers: {'Content-Type':'application/json', ...(getToken()?{Authorization:`Bearer ${getToken()}`} : {}), ...options.headers}
  })
  if (!response.ok) {
    const body = await response.json().catch(()=>({detail:'Request failed'}))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.status === 204 ? null : response.json()
}

export async function loadPlatformData() {
  const [overview, companies, chatbots, tickets, conversations] = await Promise.all([
    api('/api/internal/overview'),
    api('/api/internal/companies'),
    api('/api/internal/chatbots'),
    api('/api/internal/tickets'),
    api('/api/internal/conversations')
  ])

  const companyNames = new Map(companies.map(c => [c.id, c.name]))

  return {
    overview,
    companies: companies.map(c => ({
      id: `ORG-${c.id}`, name: c.name, email: c.email || '—',
      status: c.is_active ? 'Active' : 'Inactive',
      bots: c.bots, conversations: c.conversations, tickets: c.tickets,
      joined: c.created_at ? c.created_at.slice(0,10) : '—', last: '—'
    })),
    chatbots: chatbots.map(b => ({
      id: `BOT-${b.id}`, name: b.bot_name, company: b.company,
      deployment: String(b.status).toLowerCase() === 'active' ? 'Deployed' : 'Paused',
      status: String(b.status), conversations: b.conversations,
      today: '—', last: '—'
    })),
    tickets: tickets.map(t => ({
      id: t.ticket_id || `TKT-${t.id}`, company: t.company,
      customer: t.customer_email || '—', subject: t.customer_message || '—',
      category: t.category || '—', priority: t.priority || '—',
      agent: 'Not available', status: t.status || '—',
      created: t.created_at ? new Date(t.created_at).toLocaleString() : '—'
    })),
    conversations: conversations.map(c => ({
      id: c.session_id || `CONV-${c.id}`, company: c.company,
      bot: c.bot, customer: c.customer_id || c.customer_email || '—',
      started: c.started_at ? new Date(c.started_at).toLocaleString() : '—',
      last: c.last_activity ? new Date(c.last_activity).toLocaleString() : '—',
      status: c.status, messages: c.messages
    }))
  }
}

