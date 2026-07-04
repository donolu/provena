import { withSentryConfig } from '@sentry/nextjs'

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      // Local Django dev server
      { protocol: 'http', hostname: 'localhost', port: '8000', pathname: '/media/**' },
      // Production S3 / R2 bucket — set NEXT_PUBLIC_MEDIA_URL at build time
      ...(process.env.NEXT_PUBLIC_MEDIA_URL
        ? (() => {
            const { protocol, hostname, port } = new URL(process.env.NEXT_PUBLIC_MEDIA_URL)
            return [
              {
                protocol: /** @type {'http'|'https'} */ (protocol.slice(0, -1)),
                hostname,
                ...(port ? { port } : {}),
                pathname: '/**',
              },
            ]
          })()
        : []),
    ],
  },
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
