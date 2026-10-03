// Login via formulário. Credenciais SÓ de teste, semeadas por scripts/e2e_server.py
Cypress.Commands.add('login', (username = 'felipe', password = 'e2e-senha-teste') => {
  cy.session([username, password], () => {
    cy.visit('/auth/login')
    cy.get('input[name="username"]').type(username)
    cy.get('input[name="password"]').type(password)
    cy.get('button[type="submit"]').click()
    cy.url().should('not.include', '/auth/login')
  })
})
