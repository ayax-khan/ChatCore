const API_BASE = "/api/v1";

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      fetchAPI("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
    register: (email: string, password: string, business_name: string) =>
      fetchAPI("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, business_name }),
      }),
  },
  sites: {
    list: () => fetchAPI("/sites/"),
    create: (data: { url: string; name: string }) =>
      fetchAPI("/sites/", { method: "POST", body: JSON.stringify(data) }),
    get: (id: number) => fetchAPI(`/sites/${id}`),
    delete: (id: number) => fetchAPI(`/sites/${id}`, { method: "DELETE" }),
  },
  chat: {
    send: (siteId: number, sessionId: string, question: string) =>
      fetchAPI("/chat/", {
        method: "POST",
        body: JSON.stringify({ site_id: siteId, session_id: sessionId, question }),
      }),
  },
  analytics: {
    usage: () => fetchAPI("/analytics/usage"),
  },
};
