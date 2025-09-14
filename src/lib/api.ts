// src/lib/api.ts
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function safeFetch(endpoint: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export const testConnection = async () => {
  try {
    const data = await safeFetch("/api/health");
    console.log("Backend connection test:", data);
    return data;
  } catch (error) {
    console.error("Backend connection failed:", error);
    throw error;
  }
};
