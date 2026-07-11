/**
 * Sanitise a `next` redirect target read from the URL.
 *
 * Only same-origin absolute paths are allowed. Anything else (an absolute URL
 * like `https://evil.com`, a protocol-relative `//evil.com`, or a non-path
 * value) falls back to `fallback`, preventing an open redirect via
 * `router.push(next)`.
 */
export function safeNext(next: string | null | undefined, fallback: string): string {
  if (!next || !next.startsWith('/') || next.startsWith('//')) return fallback
  return next
}
