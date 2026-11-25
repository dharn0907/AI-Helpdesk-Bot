const BASE = import.meta.env.VITE_API_BASE_URL || ''
const tokenKey = 'orbit_internal_token'
// Keep demo labelling enabled until real data loaders and the protected internal API are implemented.
export const isDemo = true
export const getToken = () => sessionStorage.getItem(tokenKey)
export const setToken = value => value ? sessionStorage.setItem(tokenKey,value) : sessionStorage.removeItem(tokenKey)

export async function api(path, options={}) {
  if (!BASE) throw new Error('API base URL is not configured. Running in demo mode.')
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
