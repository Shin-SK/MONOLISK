/* .eslintrc.cjs */
module.exports = {
  root: true,
  env : { browser: true, es2021: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  rules: {
    'vue/valid-template-root': 'error'
  }
};
