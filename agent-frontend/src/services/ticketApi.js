const API_BASE_URL = "http://127.0.0.1:8000";

const getAgent = () => {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");

  if (!agent?.email || !agent?.company_id) {
    throw new Error("Agent session or company not found. Please log in again.");
  }

  return agent;
};

const getAgentEmail = () => getAgent().email;

const getAgentHeaders = () => {
  const agent = getAgent();
  return {
    "X-Agent-Email": agent.email,
    "X-Company-ID": String(agent.company_id),
  };
};

// Fetch only tickets belonging to the logged-in agent's company
export const getTickets = async () => {
  const response = await fetch(`${API_BASE_URL}/tickets/agents/tickets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email: getAgentEmail(), company_id: getAgent().company_id }),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Failed to fetch company tickets");
  }

  return result;
};

// Fetch a particular ticket
export const getTicketById = async (ticketId) => {
  const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}`, { headers: getAgentHeaders() });

  if (!response.ok) {
    throw new Error("Failed to fetch ticket details");
  }

  return await response.json();
};

// Update ticket status and agent reply
export const updateTicket = async (ticketId, data) => {
  const response = await fetch(`${API_BASE_URL}/tickets/${ticketId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAgentHeaders(),
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to update ticket");
  }

  return await response.json();
};

// Submit the agent's YES/NO decision for reusable resolution
export const reviewTicketResolution = async (ticketId, data) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}/resolution-review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAgentHeaders() },
      body: JSON.stringify(data),
    }
  );

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Failed to submit resolution review");
  }

  return result;
};

// Fetch the existing reusable-solution approval status
export const getTicketResolutionReview = async (ticketId) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}/resolution-review`,
    { headers: getAgentHeaders() }
  );

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Failed to fetch resolution review");
  }

  return result;
};

// AI ticket summarization
export const summarizeTicket = async (ticketId, mode) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}/summarize`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAgentHeaders() },
      body: JSON.stringify({ mode }),
    }
  );

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Failed to summarize ticket.");
  }

  return result;
};

// Fetch similar tickets
export const getSimilarTickets = async (ticketId) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}/similar`,
    { headers: getAgentHeaders() }
  );

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Failed to fetch similar tickets");
  }

  return result;
};
