import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        space: {
          bg: '#0a0a0f',
          orbit: 'rgba(255, 255, 255, 0.15)',
          sun: '#FDB813',
          earth: '#6B93D6',
          mars: '#C1440E',
          venus: '#FFC649',
          mercury: '#B7B8B9',
          jupiter: '#D8CA9D',
          saturn: '#F4D59E',
          uranus: '#D1E7E7',
          neptune: '#5B5DDF',
        },
        phase: {
          departure: '#3B82F6',
          transfer: '#F97316',
          flyby: '#EF4444',
          return: '#22C55E',
          arrival: '#3B82F6',
        },
        tier: {
          bronze: '#CD7F32',
          silver: '#C0C0C0',
          gold: '#FFD700',
          platinum: '#E5E4E2',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
