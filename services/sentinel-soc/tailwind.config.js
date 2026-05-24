/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'brand-primary':    '#004953',
        'brand-secondary':  '#F9F7F2',
        'brand-accent':     '#F0ECE6',
        'text-primary':     '#3E2723',
        'text-secondary':   '#5D4037',
        'text-on-primary':  '#F9F7F2',
        'clinical-danger':  '#C0392B',
        'clinical-warning': '#D68910',
        'clinical-success': '#1E8449',
        'clinical-teal':    '#14b8a6',
        'clinical-purple':  '#a855f7',
        'clinical-blue':    '#3b82f6',
        'clinical-amber':   '#f59e0b',
      },
      borderRadius: {
        'custom': '18.8px',
        'btn':    '117px',
      },
      boxShadow: {
        'card':        '0 20px 40px rgba(62,39,35,0.05)',
        'card-active': '0 8px 20px rgba(0,0,0,0.1)',
        'cta':         '0 10px 30px rgba(0,73,83,0.2)',
      },
      fontFamily: {
        'primary':   ['"Playfair Display"', 'serif'],
        'secondary': ['"Inter Tight"', 'sans-serif'],
        'body':      ['"Albert Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
