import { NextResponse, type NextRequest } from "next/server";

// Pages reachable without a session. Everything else requires one.
const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];

function isPublic(pathname: string) {
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

/**
 * Optimistic gate: only checks that a session cookie exists. The backend still
 * validates every API call, and the app shell redirects if the session turns out
 * to be expired or revoked.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (isPublic(pathname) || request.cookies.has("access_token")) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  if (pathname !== "/") {
    loginUrl.searchParams.set("next", pathname + search);
  }
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
