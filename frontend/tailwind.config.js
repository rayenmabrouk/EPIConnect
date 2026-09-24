/*
 * Tailwind CSS build configuration.
 * The original templates loaded the Tailwind "Play CDN" script, which compiles
 * CSS in the browser at runtime. That is explicitly not meant for production
 * and forces a CSP that allows third-party script. The same configuration is
 * now compiled once at image build time (see Dockerfile, stage "assets").
 */
const plugin = require('tailwindcss/plugin');

module.exports = {
    content: [
        '../templates/**/*.html',
        '../*/forms.py',      // repository layout
        '../forms/*.py',      // Docker build stage layout
        '../static/js/**/*.js',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                primary: {
                    50:'#fef2f2',100:'#fee2e2',200:'#fecaca',300:'#fca5a5',
                    400:'#f87171',500:'#ef4444',600:'#dc2626',700:'#b91c1c',
                    800:'#991b1b',900:'#7f1d1d',950:'#450a0a'
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.5s ease-out',
                'slide-down': 'slideDown 0.3s ease-out',
                'float': 'float 6s ease-in-out infinite',
            },
            keyframes: {
                fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
                slideUp: { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
                slideDown: { '0%': { opacity: '0', transform: 'translateY(-10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
                float: { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-10px)' } },
            }
        }
    },
    plugins: [
        plugin(function({ addComponents, theme }) {
            addComponents({
                '.btn-primary': {
                    backgroundColor: theme('colors.primary.500'),
                    color: '#fff',
                    fontWeight: '500',
                    borderRadius: theme('borderRadius.xl'),
                    boxShadow: '0 1px 2px 0 rgba(239,68,68,0.25)',
                    transition: 'all 0.2s',
                    '&:hover': {
                        backgroundColor: theme('colors.primary.600'),
                        boxShadow: '0 4px 6px -1px rgba(239,68,68,0.3)',
                    },
                },
                '.btn-secondary': {
                    backgroundColor: theme('colors.stone.50'),
                    border: '1px solid ' + theme('colors.stone.300'),
                    color: theme('colors.gray.700'),
                    fontWeight: '500',
                    borderRadius: theme('borderRadius.xl'),
                    transition: 'all 0.2s',
                    '&:hover': {
                        backgroundColor: theme('colors.stone.200'),
                    },
                },
                '.card': {
                    backgroundColor: theme('colors.stone.50'),
                    border: '1px solid ' + theme('colors.stone.200'),
                    borderRadius: theme('borderRadius.2xl'),
                    boxShadow: theme('boxShadow.sm'),
                    transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)',
                    '&:hover': {
                        boxShadow: theme('boxShadow.lg'),
                        transform: 'translateY(-2px)',
                    },
                },
                '.card-static': {
                    backgroundColor: theme('colors.stone.50'),
                    border: '1px solid ' + theme('colors.stone.200'),
                    borderRadius: theme('borderRadius.2xl'),
                    boxShadow: theme('boxShadow.sm'),
                },
                '.nav-link': {
                    padding: theme('spacing[2]') + ' ' + theme('spacing[3.5]'),
                    borderRadius: theme('borderRadius.xl'),
                    fontSize: theme('fontSize.sm'),
                    fontWeight: '500',
                    color: theme('colors.gray.600'),
                    transition: 'all 0.2s',
                    '&:hover': {
                        color: theme('colors.primary.500'),
                        backgroundColor: theme('colors.stone.200'),
                    },
                },
            });
        }),
        plugin(function({ addComponents, theme }) {
            addComponents({
                '.dark .btn-secondary': {
                    backgroundColor: theme('colors.slate.800'),
                    borderColor: theme('colors.slate.700'),
                    color: theme('colors.slate.300'),
                    '&:hover': {
                        backgroundColor: theme('colors.slate.700'),
                    },
                },
                '.dark .card': {
                    backgroundColor: theme('colors.slate.800'),
                    borderColor: theme('colors.slate.700'),
                    '&:hover': {
                        boxShadow: '0 10px 15px -3px rgba(15,23,42,0.5)',
                    },
                },
                '.dark .card-static': {
                    backgroundColor: theme('colors.slate.800'),
                    borderColor: theme('colors.slate.700'),
                },
                '.dark .nav-link': {
                    color: theme('colors.slate.400'),
                    '&:hover': {
                        color: theme('colors.primary.400'),
                        backgroundColor: theme('colors.slate.800'),
                    },
                },
            });
        }),
    ],
};
