
const API_BASE_URL = "http://127.0.0.1:8000";

// Fetch all tickets from the backend
export const getTickets = async () => {
  const response = await fetch(`${API_BASE_URL}/tickets/`);

  if (!response.ok) {
    throw new Error("Failed to fetch tickets");
  }

  return await response.json();
};

// Fetch a particular ticket
export const getTicketById = async (ticketId) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch ticket details");
  }

  return await response.json();
};

// Update ticket status and agent reply
export const updateTicket = async (ticketId, data) => {
  const response = await fetch(
    `${API_BASE_URL}/tickets/${ticketId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to update ticket");
  }

  return await response.json();
};
