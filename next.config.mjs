import { withSentryConfig } from '@sentry/nextjs'

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
}

export default withSentryConfig(nextConfig, {
  // Suppress the Sentry CLI output during build
  silent: !process.env.CI,
  // Upload source maps only in CI/production
  telemetry: false,
  // Disable auto-instrumentation file injection when DSN is not set
  autoInstrumentServerFunctions: false,
  hideSourceMaps: true,
})
