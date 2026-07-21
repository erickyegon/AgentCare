import { getStoredToken } from "./auth";
import type { TraceEvent } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const API_V1 = `${API_URL}/api/v1`;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getStoredToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_V1}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>(path, { method: "GET" }),
  post: <T,>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }, auth),
  patch: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  upload: <T,>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

/**
 * Execute a workflow run and stream agent trace events over SSE.
 * Uses fetch (not EventSource) so we can send the Authorization header.
 */
export async function streamWorkflow(
  runId: number,
  onEvent: (evt: TraceEvent) => void,
): Promise<void> {
  const token = getStoredToken();
  const res = await fetch(`${API_V1}/workflows/${runId}/stream`, {
    method: "POST",
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
      Accept: "text/event-stream",
    },
  });
  if (!res.ok || !res.body) {
    throw new ApiError("Failed to start workflow stream", res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line. sse-starlette uses CRLF, so accept both.
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const dataLine = frame
        .split(/\r?\n/)
        .find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as TraceEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
