const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Request failed");
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res;
}

export const api = {
  getSettings: () => request("/settings"),
  updateSettings: (payload) => request("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  getDailyState: (date) => request(`/daily-state${date ? `?date=${date}` : ""}`),
  listTasks: (status) => request(`/tasks${status ? `?status=${status}` : ""}`),
  createTask: (payload) => request("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (id, payload) => request(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  completeTask: (id) => request(`/tasks/${id}/complete`, { method: "POST" }),
  listSessions: (from, to) => request(`/sessions?from=${from}&to=${to}`),
  startSession: (payload) => request("/sessions/start", { method: "POST", body: JSON.stringify(payload) }),
  planSession: (payload) => request("/sessions/plan", { method: "POST", body: JSON.stringify(payload) }),
  startPlannedSession: (id) => request(`/sessions/${id}/start`, { method: "POST" }),
  stopSession: (id) => request(`/sessions/${id}/stop`, { method: "POST" }),
  skipSession: (id) => request(`/sessions/${id}/skip`, { method: "POST" }),
  adjustSession: (id, payload) => request(`/sessions/${id}/adjust`, { method: "POST", body: JSON.stringify(payload) }),
  mergeNext: (id) => request(`/sessions/${id}/merge-next`, { method: "POST" }),
  updateSession: (id, payload) => request(`/sessions/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  resetSession: (id) => request(`/sessions/${id}/reset`, { method: "POST" }),
  resetDay: (date, mode) => request(`/sessions/reset-day?date=${date}&mode=${mode}`, { method: "POST" }),
  listPauseCards: () => request("/pause-cards"),
  createPauseCard: (payload) => request("/pause-cards", { method: "POST", body: JSON.stringify(payload) }),
  updatePauseCard: (id, payload) => request(`/pause-cards/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  consumePause: (payload) => request("/pause/consume", { method: "POST", body: JSON.stringify(payload) })
};

export function downloadExport() {
  window.location.href = `${API_BASE}/export/sqlite`;
}
