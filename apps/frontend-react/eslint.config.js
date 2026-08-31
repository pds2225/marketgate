import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      // No eslint-plugin-react here, so JSX usage isn't tracked by no-unused-vars.
      // PascalCase names are ignored (components/icons used only in JSX); `motion`
      // is the framer-motion namespace used as <motion.*>. argsIgnorePattern covers
      // renamed destructured params like `.map(({ icon: Icon }) => <Icon/>)`.
      'no-unused-vars': ['error', {
        varsIgnorePattern: '^[A-Z_]|^motion$',
        argsIgnorePattern: '^[A-Z_]',
      }],
    },
  },
  {
    // Vercel serverless functions run on Node, not in the browser.
    files: ['api/**/*.js'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
])
