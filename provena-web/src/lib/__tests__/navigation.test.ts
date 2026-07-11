import { describe, expect, it } from 'vitest'
import { safeNext } from '../navigation'

describe('safeNext', () => {
  it('allows same-origin absolute paths', () => {
    expect(safeNext('/catalogue', '/home')).toBe('/catalogue')
    expect(safeNext('/orders/123', '/home')).toBe('/orders/123')
  })

  it('falls back for absolute and protocol-relative URLs (open-redirect guard)', () => {
    expect(safeNext('https://evil.com', '/home')).toBe('/home')
    expect(safeNext('http://evil.com', '/home')).toBe('/home')
    expect(safeNext('//evil.com', '/home')).toBe('/home')
  })

  it('falls back for backslash forms browsers normalise to external URLs', () => {
    expect(safeNext('/\\evil.com', '/home')).toBe('/home')
    expect(safeNext('/\\/evil.com', '/home')).toBe('/home')
    expect(safeNext('\\\\evil.com', '/home')).toBe('/home')
  })

  it('falls back for missing or non-path values', () => {
    expect(safeNext(null, '/home')).toBe('/home')
    expect(safeNext(undefined, '/home')).toBe('/home')
    expect(safeNext('', '/home')).toBe('/home')
    expect(safeNext('catalogue', '/home')).toBe('/home')
  })
})
