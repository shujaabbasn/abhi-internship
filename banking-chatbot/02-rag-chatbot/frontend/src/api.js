/**
 * api.js — thin client for the ABHI Banking Assistant FastAPI backend.
 */

const BASE_URL = "http://localhost:8000";

/**
 * Send a chat message.
 * @param {string} message
 * @param {string|null} sessionId
 * @returns {Promise<{reply: string, session_id: string, intent: string|null, awaiting_field: string|null, complete: boolean}>}
 */
export async function sendMessage(message, sessionId = null) {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Check backend health.
 * @returns {Promise<{status: string}>}
 */
export async function checkHealth() {
  const response = await fetch(`${BASE_URL}/api/health`);
  return response.json();
}
