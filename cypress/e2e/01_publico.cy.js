// Testes de rotas públicas — sem login obrigatório

describe('Páginas públicas', () => {
  it('Home carrega e exibe logo', () => {
    cy.visit('/')
    cy.contains('MeuPokémonGO').should('be.visible')
    // Título da home usa "{% block title %}Dashboard{% endblock %}" — subtítulo contém a marca
    cy.document().its('title').should('include', 'Sua coleção')
  })

  it('Status bar de debug foi removida', () => {
    cy.visit('/')
    cy.contains('Flask v3.1.3').should('not.exist')
    cy.contains('Olá, felipe').should('not.exist')
  })

  it('Navbar tem links corretos', () => {
    cy.visit('/')
    cy.get('nav').contains('Pokédex').should('have.attr', 'href').and('include', '/pokedex')
    cy.get('nav').contains('Entrar').should('be.visible')
  })

  it('Pokédex lista Pokémon com sprites', () => {
    cy.visit('/pokedex')
    cy.get('img').its('length').should('be.greaterThan', 5)
    cy.contains('#001').should('be.visible')
  })

  it('Pokédex — filtro de geração 1 mostra Kanto e não Johto', () => {
    cy.visit('/pokedex?generation=1')
    // #001 deve estar na página 1 (paginação de 24)
    cy.contains('#001').should('be.visible')
    // Johto começa em #152 — não deve existir no resultado
    cy.contains('#152').should('not.exist')
  })

  it('Pokédex — busca por nome retorna resultado', () => {
    cy.visit('/pokedex?q=pikachu')
    cy.contains('Pikachu').should('be.visible')
    // Deve haver poucos resultados (não a grade inteira de 24)
    cy.get('.grid').children().its('length').should('be.lessThan', 10)
  })

  it('Pokédex — busca por número retorna Pokémon correto', () => {
    cy.visit('/pokedex?q=25')
    cy.contains('#025').should('be.visible')
  })

  it('Detalhe de Pokémon carrega', () => {
    cy.visit('/pokedex/1')
    cy.contains('Bulbasaur').should('be.visible')
    cy.get('img').its('length').should('be.greaterThan', 0)
  })

  it('Estoque público de felipe carrega', () => {
    cy.visit('/estoque/felipe')
    cy.contains('felipe').should('be.visible')
  })

  it('Estoque — OG tags presentes', () => {
    cy.visit('/estoque/felipe')
    cy.get('meta[property="og:title"]')
      .should('have.attr', 'content')
      .and('include', 'felipe')
    cy.get('meta[property="og:url"]')
      .should('have.attr', 'content')
      .and('include', 'estoque/felipe')
  })

  it('Estoque — status bar removida', () => {
    cy.visit('/estoque/felipe')
    cy.contains('Flask v3.1.3').should('not.exist')
  })

  it('Estoque — 3 abas visíveis desktop', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-tenho').should('be.visible')
    cy.get('#tab-faltantes').should('be.visible')
    cy.get('#tab-troca').should('be.visible')
  })

  it('Estoque — aba Faltantes funciona', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-faltantes').click()
    cy.get('#tab-content-faltantes').should('not.have.class', 'hidden')
    cy.get('#tab-content-tenho').should('have.class', 'hidden')
  })

  it('Estoque — cards de faltantes são links clicáveis', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-faltantes').click()
    cy.get('#tab-content-faltantes a[href*="/pokedex/"]')
      .first()
      .should('be.visible')
      .and('have.attr', 'href')
  })

  it('Estoque — FAB de catalogar presente', () => {
    cy.visit('/estoque/felipe')
    cy.get('a[href*="/collection/catalogar"]')
      .should('be.visible')
      .and('have.class', 'rounded-full')
  })

  it('Estoque — progress bar CTA presente quando abaixo de 100%', () => {
    cy.visit('/estoque/felipe')
    cy.get('.bg-green-500').should('exist')
  })

  it('Usuário inexistente retorna 404', () => {
    cy.request({
      url: '/estoque/usuario_inexistente_xyz999',
      failOnStatusCode: false,
    }).its('status').should('eq', 404)
  })

  it('Login redireciona para home', () => {
    cy.visit('/auth/login')
    cy.get('input[name="username"]').type('felipe')
    cy.get('input[name="password"]').type('livia8731')
    cy.get('button[type="submit"]').click()
    cy.url().should('not.include', '/login')
  })
})
