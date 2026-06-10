import { NextRequest, NextResponse } from "next/server";

/**
 * Shared-password gate for the hosted web UI (HTTP Basic Auth).
 *
 * Covers the page and every API route — /api/chat and /api/render alike (the
 * matcher excludes only Next internals) — the APIs must be gated too, or a request
 * could hit chat and spend the ANTHROPIC_API_KEY, or render and spend engine
 * compute, straight past the page gate. This is distinct
 * from the engine's FRONTIER_MCP_TOKEN: that token authenticates the app→engine
 * connector call and is never exposed to UI users, so the UI needs its own gate.
 *
 * Disabled when UI_ACCESS_PASSWORD is unset (local dev / single-user self-host),
 * mirroring the engine's ungated-by-default behavior. Set it in production.
 * Username is optional: unset UI_ACCESS_USER = any username + correct password.
 */
export function middleware(req: NextRequest) {
  const expectedPass = process.env.UI_ACCESS_PASSWORD;
  if (!expectedPass) return NextResponse.next();

  const expectedUser = process.env.UI_ACCESS_USER;
  const header = req.headers.get("authorization");

  if (header) {
    const [scheme, encoded] = header.split(" ");
    if (scheme === "Basic" && encoded) {
      const decoded = atob(encoded);
      const sep = decoded.indexOf(":");
      const user = decoded.slice(0, sep);
      const pass = decoded.slice(sep + 1);
      if (pass === expectedPass && (!expectedUser || user === expectedUser)) {
        return NextResponse.next();
      }
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Frontier", charset="UTF-8"' },
  });
}

export const config = {
  // Gate everything except Next.js internals and static assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
