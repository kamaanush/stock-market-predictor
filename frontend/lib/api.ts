const API = "http://localhost:8000/api";

export async function api<T>(
  url: string,
  options?: RequestInit
): Promise<T> {

  const response = await fetch(`${API}${url}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}