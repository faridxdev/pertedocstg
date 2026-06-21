/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './static/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Palette officielle Togo
        'togo-green': '#006B3F',
        'togo-yellow': '#FFCE00',
        'togo-red': '#D21034',
        'togo-white': '#FFFFFF',

        // Extended palette
        'togo': {
          50:  '#e6f4ec',
          100: '#c0e3ce',
          200: '#96d1ae',
          300: '#6cbf8d',
          400: '#4db176',
          500: '#2ea35f',
          600: '#006B3F',  // Primary
          700: '#005c35',
          800: '#004d2b',
          900: '#003d22',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        display: ['Sora', 'Plus Jakarta Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'xl': '0.875rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 107, 63, 0.08)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        'green-glow': '0 0 20px rgba(0, 107, 63, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'pulse-green': 'pulseGreen 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseGreen: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0, 107, 63, 0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(0, 107, 63, 0)' },
        },
      },
      backgroundImage: {
        'togo-gradient': 'linear-gradient(135deg, #006B3F 0%, #004d2b 100%)',
        'hero-pattern': 'radial-gradient(ellipse at top, #0d2b1f 0%, #000d07 100%)',
        'card-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    // Plugin personnalisé pour les composants PerteDocsTG
    function({ addComponents, addUtilities, theme }) {
      addComponents({
        // Boutons
        '.btn-primary': {
          '@apply inline-flex items-center justify-center gap-2 bg-togo-green hover:bg-emerald-700 text-white font-semibold px-6 py-3 rounded-xl transition-all hover:scale-105 hover:shadow-lg hover:shadow-togo-green/20 focus:outline-none focus:ring-2 focus:ring-togo-green/50 disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.btn-secondary': {
          '@apply inline-flex items-center justify-center gap-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-semibold px-6 py-3 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-gray-300': {},
        },
        '.btn-outline': {
          '@apply inline-flex items-center justify-center gap-2 border-2 border-togo-green text-togo-green hover:bg-togo-green hover:text-white font-semibold px-6 py-3 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-togo-green/50': {},
        },
        '.btn-danger': {
          '@apply inline-flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold px-6 py-3 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-red-500/50': {},
        },
        '.btn-sm': {
          '@apply px-4 py-2 text-sm rounded-lg': {},
        },
        '.btn-lg': {
          '@apply px-8 py-4 text-lg rounded-2xl': {},
        },

        // Navigation
        '.nav-link': {
          '@apply px-4 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-togo-green dark:hover:text-togo-green hover:bg-togo-green/5 transition-colors': {},
        },
        '.nav-link-active': {
          '@apply text-togo-green bg-togo-green/10': {},
        },
        '.mobile-nav-link': {
          '@apply block px-4 py-3 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-togo-green/10 hover:text-togo-green transition-colors': {},
        },
        '.dropdown-item': {
          '@apply flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors cursor-pointer': {},
        },

        // Cards
        '.card': {
          '@apply bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-card hover:shadow-card-hover transition-shadow': {},
        },
        '.card-flat': {
          '@apply bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700': {},
        },
        '.card-glass': {
          '@apply bg-white/60 dark:bg-gray-800/60 backdrop-blur-xl rounded-2xl border border-white/20 dark:border-gray-700/50 shadow-glass': {},
        },

        // Stat cards
        '.stat-card': {
          '@apply card p-6 flex items-start gap-4': {},
        },
        '.stat-icon': {
          '@apply w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0': {},
        },

        // Forms
        '.form-input': {
          '@apply w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-togo-green/50 focus:border-togo-green transition-colors text-sm': {},
        },
        '.form-select': {
          '@apply w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-togo-green/50 focus:border-togo-green transition-colors text-sm appearance-none': {},
        },
        '.form-textarea': {
          '@apply w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-togo-green/50 focus:border-togo-green transition-colors text-sm resize-none': {},
        },
        '.form-label': {
          '@apply block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5': {},
        },
        '.form-error': {
          '@apply mt-1 text-sm text-red-500 flex items-center gap-1': {},
        },
        '.form-help': {
          '@apply mt-1 text-xs text-gray-400': {},
        },

        // Status badges
        '.badge': {
          '@apply inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold': {},
        },
        '.badge-draft': {
          '@apply badge bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300': {},
        },
        '.badge-submitted': {
          '@apply badge bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800': {},
        },
        '.badge-in-progress': {
          '@apply badge bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800': {},
        },
        '.badge-validated': {
          '@apply badge bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800': {},
        },
        '.badge-rejected': {
          '@apply badge bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800': {},
        },
        '.badge-complement': {
          '@apply badge bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800': {},
        },

        // Table
        '.table-wrapper': {
          '@apply overflow-x-auto rounded-2xl border border-gray-100 dark:border-gray-700': {},
        },
        '.table-header': {
          '@apply px-6 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800/50': {},
        },
        '.table-cell': {
          '@apply px-6 py-4 text-sm text-gray-700 dark:text-gray-300': {},
        },
        '.table-row': {
          '@apply hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-t border-gray-50 dark:border-gray-700/50': {},
        },

        // Sidebar
        '.sidebar-link': {
          '@apply flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-togo-green hover:bg-togo-green/5 transition-all group': {},
        },
        '.sidebar-link-active': {
          '@apply text-togo-green bg-togo-green/10': {},
        },

        // Wizard progress
        '.wizard-step': {
          '@apply flex flex-col items-center gap-2': {},
        },
        '.wizard-step-circle': {
          '@apply w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all': {},
        },
        '.wizard-step-active': {
          '@apply bg-togo-green text-white shadow-lg shadow-togo-green/30 scale-110': {},
        },
        '.wizard-step-complete': {
          '@apply bg-togo-green text-white': {},
        },
        '.wizard-step-inactive': {
          '@apply bg-gray-100 dark:bg-gray-700 text-gray-400': {},
        },

        // Toast
        '.toast': {
          '@apply flex items-start gap-3 p-4 rounded-xl shadow-lg border max-w-sm': {},
        },
        '.toast-success': {
          '@apply toast bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200': {},
        },
        '.toast-error': {
          '@apply toast bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200': {},
        },
        '.toast-warning': {
          '@apply toast bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200': {},
        },
        '.toast-info': {
          '@apply toast bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200': {},
        },
      });

      addUtilities({
        '.text-balance': { 'text-wrap': 'balance' },
        '.scrollbar-hide': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        },
      });
    },
  ],
};
