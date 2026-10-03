const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5001',
    viewportWidth: 1280,
    viewportHeight: 800,
    defaultCommandTimeout: 12000,
    pageLoadTimeout: 30000,
    requestTimeout: 12000,
    responseTimeout: 12000,
    video: false,
    screenshotOnRunFailure: true,
    screenshotsFolder: 'cypress/screenshots',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',
    // Roda contra o servidor isolado: python scripts/e2e_server.py (SQLite descartável)
    env: {
      username: 'felipe',
      password: 'e2e-senha-teste',
    },
  },
})
