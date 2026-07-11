/**
 * Sanitise a `next` redirect target read from the URL.
 *
 * Only same-origin absolute paths are allowed. Anything else (an absolute URL
 * like `https://evil.com`, a protocol-relative `//evil.com`, a backslash form
 * like `/\evil.com` that browsers normalise to `//evil.com`, or a non-path
 * value) falls back to `fallback`, preventing an open redirect via
 * `router.push(next)`.
 */
export function safeNext(next: string | null | undefined, fallback: string): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.includes('\\')) {
    return fallback
  }
  return next
}
