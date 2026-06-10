/**
 * Best-effort, in-memory request rate limiting for the API routes.
 *
 * A per-instance floor against runaway spend: even a holder of the shared
 * UI_ACCESS_PASSWORD (or an ungated local instance) can't drive unbounded
 * Anthropic / engine calls in a tight loop. Two fixed-window counters — one
 * per client key (IP) and one global — bound the request rate; the global
 * counter is the cost circuit-breaker that also covers a many-IP burst.
 *
 * In-memory means per-instance (not shared across Render instances) and reset
 * on redeploy — a deliberate floor, not a distributed quota. Per-user tokens
 * (D.1) are the real accounting layer; this just stops the obvious abuse. Pure
 * logic with an injectable clock, so it unit-tests under `node --test` without
 * the Next.js runtime.
 */

export interface RateLimitRule {
  /** Max requests allowed per window. */
  limit: number;
  /** Window length in milliseconds. */
  windowMs: number;
}

export interface RateLimiterOptions {
  perKey: RateLimitRule;
  global: RateLimitRule;
  /** Injectable clock (defaults to Date.now), for deterministic tests. */
  now?: () => number;
}

export interface RateLimitResult {
  ok: boolean;
  /** Which limit was hit (only set when !ok). */
  scope?: "key" | "global";
  /** Milliseconds until the hit window resets (only set when !ok). */
  retryAfterMs?: number;
}

interface CounterWindow {
  count: number;
  resetAt: number;
}

/** Reset the window if the current one has elapsed. Idempotent for a fixed `t`. */
function roll(w: CounterWindow, rule: RateLimitRule, t: number): void {
  if (t >= w.resetAt) {
    w.count = 0;
    w.resetAt = t + rule.windowMs;
  }
}

export class RateLimiter {
  private readonly keyWindows = new Map<string, CounterWindow>();
  private readonly globalWindow: CounterWindow = { count: 0, resetAt: 0 };
  private readonly perKey: RateLimitRule;
  private readonly global: RateLimitRule;
  private readonly now: () => number;

  constructor(opts: RateLimiterOptions) {
    this.perKey = opts.perKey;
    this.global = opts.global;
    this.now = opts.now ?? (() => Date.now());
  }

  /**
   * Record one request against `key`. Returns ok=false (without consuming a
   * slot from either window) when either the global or the per-key limit is
   * already exhausted, so a rejected request never counts toward the cap.
   */
  check(key: string): RateLimitResult {
    const t = this.now();

    roll(this.globalWindow, this.global, t);
    let keyWindow = this.keyWindows.get(key);
    if (!keyWindow) {
      keyWindow = { count: 0, resetAt: 0 };
      this.keyWindows.set(key, keyWindow);
    }
    roll(keyWindow, this.perKey, t);

    // Check both before consuming, so a request blocked by one limit doesn't
    // burn a slot in the other.
    if (this.globalWindow.count >= this.global.limit) {
      return { ok: false, scope: "global", retryAfterMs: this.globalWindow.resetAt - t };
    }
    if (keyWindow.count >= this.perKey.limit) {
      return { ok: false, scope: "key", retryAfterMs: keyWindow.resetAt - t };
    }

    this.globalWindow.count++;
    keyWindow.count++;
    this.sweep(t);
    return { ok: true };
  }

  /** Drop expired per-key windows so the map can't grow without bound. */
  private sweep(t: number): void {
    if (this.keyWindows.size < 1024) return;
    for (const [k, w] of this.keyWindows) {
      if (t >= w.resetAt) this.keyWindows.delete(k);
    }
  }
}

/** Parse a positive-integer env var, falling back to `fallback`. */
function intEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

const WINDOW_MS = 60_000;

/**
 * Build a limiter from env. Defaults are generous for a human-driven beta but
 * cap a runaway loop. A per-route prefix gives each route an independent budget,
 * so a burst on one route can't exhaust another's global cap. Tunable via
 * <PREFIX>_RATE_LIMIT_PER_MIN / <PREFIX>_RATE_LIMIT_GLOBAL_PER_MIN.
 */
export function createRateLimiter(
  envPrefix: string,
  perKeyDefault: number,
  globalDefault: number,
): RateLimiter {
  return new RateLimiter({
    perKey: { limit: intEnv(`${envPrefix}_RATE_LIMIT_PER_MIN`, perKeyDefault), windowMs: WINDOW_MS },
    global: { limit: intEnv(`${envPrefix}_RATE_LIMIT_GLOBAL_PER_MIN`, globalDefault), windowMs: WINDOW_MS },
  });
}

// Independent per-instance counters. /api/chat drives paid Anthropic calls (the
// tighter budget); /api/render is read-only engine compute, no model spend, so a
// render burst gets its own looser budget and can't starve the chat cap.
export const chatRateLimiter = createRateLimiter("CHAT", 30, 90);
export const renderRateLimiter = createRateLimiter("RENDER", 60, 180);

/**
 * Best-effort client identifier from proxy headers. Uses the RIGHTMOST
 * x-forwarded-for hop — the value appended by the trusted proxy (Render) — because
 * a client controls everything to its left, so keying on the leftmost would let an
 * attacker mint a fresh bucket per request. Behind multiple proxy hops the rightmost
 * may be an infra IP (per-IP then coarsens toward the global cap, which is the real
 * bound); adjust if deployed behind a different topology.
 */
export function clientKey(req: Request): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) {
    const hops = xff.split(",").map((s) => s.trim()).filter(Boolean);
    if (hops.length) return hops[hops.length - 1]!;
  }
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

/** Build a 429 response with a Retry-After header from a failed check. */
export function tooManyRequests(result: RateLimitResult): Response {
  const retryAfterSec = Math.max(1, Math.ceil((result.retryAfterMs ?? WINDOW_MS) / 1000));
  return new Response(
    JSON.stringify({ error: "rate limit exceeded; slow down and retry shortly" }),
    {
      status: 429,
      headers: { "content-type": "application/json", "retry-after": String(retryAfterSec) },
    },
  );
}
