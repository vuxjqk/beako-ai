/**
 * Thin fetch wrapper for the FastAPI backend (proxied under /api, see next.config.ts).
 *
 * Auth lives in httpOnly cookies. When an authenticated call gets a 401 we try one
 * token refresh and retry; if that fails too the session is over and we send the
 * user to the login page.
 */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    readonly retryAfter?: number,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/** The request never reached the server (offline, DNS, backend down, ...). */
export class NetworkError extends Error {
  constructor() {
    super("Network error");
    this.name = "NetworkError";
  }
}

export class SessionExpiredError extends Error {
  constructor() {
    super("Session expired");
    this.name = "SessionExpiredError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  json?: unknown;
  formData?: FormData;
  /**
   * false for endpoints where 401 means "wrong credentials" (login, register, ...),
   * so we must not try to refresh or redirect.
   */
  auth?: boolean;
};

async function send(path: string, { method = "GET", json, formData }: RequestOptions) {
  try {
    return await fetch(`/api${path}`, {
      method,
      credentials: "same-origin",
      headers: json !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: json !== undefined ? JSON.stringify(json) : formData,
    });
  } catch {
    throw new NetworkError();
  }
}

// Concurrent 401s share a single refresh call (the refresh token is single-use).
let refreshing: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  refreshing ??= send("/auth/refresh", { method: "POST" })
    .then((res) => res.ok)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

function redirectToLogin() {
  const { pathname, search } = window.location;
  const params = new URLSearchParams({ reason: "session-expired" });
  if (pathname !== "/") params.set("next", pathname + search);
  // This module lives outside React (no router), and a full reload also drops any
  // state that belonged to the expired session.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`/login?${params}`);
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail)) detail = body.detail[0]?.msg ?? detail;
  } catch {
    // Non-JSON error body (e.g. proxy error page)
  }
  const retryAfter = Number(res.headers.get("Retry-After")) || undefined;
  return new ApiError(res.status, detail, retryAfter);
}

export async function api<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true } = options;
  let res = await send(path, options);

  if (res.status === 401 && auth) {
    if (await refreshSession()) {
      res = await send(path, options);
    }
    if (res.status === 401) {
      redirectToLogin();
      throw new SessionExpiredError();
    }
  }

  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
