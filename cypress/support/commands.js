// Login via formulário — hardcoded defaults para Cypress 16 (Cypress.env() removido)
Cypress.Commands.add('login', (username = 'felipe', password = 'livia8731') => {
  cy.session([username, password], () => {
    cy.visit('/auth/login')
    cy.get('input[name="username"]').type(username)
    cy.get('input[name="password"]').type(password)
    cy.get('button[type="submit"]').click()
    cy.url().should('not.include', '/auth/login')
  })
})
