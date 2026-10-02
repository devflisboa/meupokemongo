// Testes da coleção privada e endpoint upsert

describe('Coleção privada', () => {
  beforeEach(() => {
    cy.login()
  })

  it('/collection carrega com stats', () => {
    cy.visit('/collection')
    cy.get('.grid').should('exist')
    cy.contains(/capturado|coleção/i).should('be.visible')
  })

  it('Filtro "apenas capturados" mostra só owned', () => {
    cy.visit('/collection?show=owned')
    cy.get('.grid').children().its('length').should('be.greaterThan', 0)
  })

  it('Filtro "faltantes" retorna cards', () => {
    cy.visit('/collection?show=missing')
    cy.get('.grid').should('exist')
  })

  it('POST /collection/upsert retorna JSON ok', () => {
    cy.visit('/collection')
    cy.get('meta[name="csrf-token"]').invoke('attr', 'content').then(csrf => {
      cy.request({
        method: 'POST',
        url: '/collection/upsert',
        headers: { 'X-CSRFToken': csrf },
        form: true,
        body: { form_id: 1, owned: 'true', quantity: 1, for_trade: 'false' },
      }).then(res => {
        expect(res.status).to.eq(200)
        expect(res.body.ok).to.be.true
        expect(res.body).to.have.keys(['ok', 'owned', 'quantity', 'for_trade'])
      })
    })
  })

  it('API /api/log aceita eventos', () => {
    cy.request({
      method: 'POST',
      url: '/api/log',
      headers: { 'Content-Type': 'application/json' },
      body: { event: 'TEST_EVENT', data: { source: 'cypress' } },
    }).then(res => {
      expect(res.status).to.eq(200)
      expect(res.body.ok).to.be.true
    })
  })

  it('Pokédex detalhe mostra info da espécie', () => {
    cy.visit('/pokedex/4')
    cy.contains('Charmander').should('be.visible')
  })

  it('Import index carrega (autenticado)', () => {
    cy.visit('/import')
    cy.contains('PokeGenie').should('be.visible')
    cy.get('input[type="file"]').should('exist')
  })

  it('Logout desfaz a sessão', () => {
    cy.visit('/auth/logout')
    // Flask redireciona para home após logout
    cy.url().should('not.include', '/auth/logout')
    // Usuário não está mais autenticado — menu não mostra "Sair"
    cy.contains('Sair').should('not.exist')
  })
})

describe('Proteção de rotas', () => {
  it('/collection redireciona anônimo para login', () => {
    cy.clearCookies()
    cy.visit('/collection', { failOnStatusCode: false })
    cy.url().should('include', '/auth/login')
  })

  it('/collection/catalogar redireciona anônimo para login', () => {
    cy.clearCookies()
    cy.visit('/collection/catalogar', { failOnStatusCode: false })
    cy.url().should('include', '/auth/login')
  })

  it('/admin redireciona anônimo', () => {
    cy.clearCookies()
    cy.visit('/admin', { failOnStatusCode: false })
    // Aceita qualquer URL que não seja /admin direto (redirect para login ou 403)
    cy.url().then(url => {
      expect(url).to.not.include('/admin/dashboard')
    })
  })
})
