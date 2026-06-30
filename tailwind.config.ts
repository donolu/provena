import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        mist:      '#F4F7F4',
        forest:    '#1B2B1E',
        meadow:    '#4C8B6B',
        marigold:  '#E8B84B',
        hoarfrost: '#CDD5CE',
        soil:      '#7C6E5B',
      },
      fontFamily: {
        display: ['var(--font-fraunces)', 'Georgia', 'serif'],
        sans:    ['var(--font-plus-jakarta)', 'system-ui', 'sans-serif'],
        mono:    ['var(--font-dm-mono)', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
