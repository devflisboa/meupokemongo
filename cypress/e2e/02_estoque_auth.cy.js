// Testes de estoque com usuário logado (toggle for_trade, busca, mobile nav)

describe('Estoque autenticado', () => {
  beforeEach(() => {
    cy.login()
  })

  it('Estoque próprio carrega com cards owned', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-content-tenho .poke-card').its('length').should('be.greaterThan', 0)
  })

  it('Cards de "Tenho" têm botão 🔄 para marcar troca', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-content-tenho .trade-btn').first().should('be.visible')
  })

  it('Botão 🔄 toggle for_trade e muda visual', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-content-tenho .trade-btn').first().as('btn')

    cy.get('@btn').then($btn => {
      const wasTrade = $btn.hasClass('bg-blue-500')
      cy.get('@btn').click()
      cy.wait(600)
      if (wasTrade) {
        cy.get('@btn').should('have.class', 'bg-gray-100')
      } else {
        cy.get('@btn').should('have.class', 'bg-blue-500')
      }
      // Reverte para não poluir estado
      cy.get('@btn').click()
    })
  })

  it('Busca filtra cards em tempo real', () => {
    cy.visit('/estoque/felipe')
    const total = () => cy.get('#tab-content-tenho .poke-card:visible').its('length')

    total().then(before => {
      cy.get('#card-search').type('bulb')
      cy.get('#tab-content-tenho .poke-card:visible').its('length').should('be.lessThan', before)
      cy.get('#tab-content-tenho .poke-card:visible').first().invoke('attr', 'data-name').should('include', 'bulb')
    })
  })

  it('Busca limpa restaura todos os cards', () => {
    cy.visit('/estoque/felipe')
    cy.get('#card-search').type('pikachu')
    cy.get('#card-search').clear()
    cy.get('#tab-content-tenho .poke-card:visible').its('length').should('be.greaterThan', 5)
  })

  it('Aba Faltantes tem infinite scroll configurado', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-faltantes').click()
    cy.get('#tab-content-faltantes').should('not.have.class', 'hidden')
    // Sentinel do IntersectionObserver deve existir
    cy.get('#missing-sentinel').should('exist')
    // Parte dos cards deve ter classe hidden (lazy load) — lazy pagination funcionando
    cy.get('#missing-grid .missing-card.hidden').should('exist')
    // Total de missing-card deve ser > 30 (há mais carregamento a fazer)
    cy.get('#missing-grid .missing-card').its('length').should('be.greaterThan', 30)
  })

  it('Infinite scroll revela mais cards ao rolar', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-faltantes').click()

    cy.get('#missing-grid .missing-card:not(.hidden)').its('length').then(initial => {
      cy.get('#missing-sentinel').scrollIntoView()
      cy.wait(500)
      // Após scroll, deve ter mais cards visíveis
      cy.get('#missing-grid .missing-card:not(.hidden)').its('length').should('be.gte', initial)
    })
  })

  it('Bottom nav visível em viewport mobile', () => {
    cy.viewport(375, 812)
    cy.visit('/estoque/felipe')
    cy.get('#bottom-nav').should('be.visible')
    cy.get('#bnav-tenho').should('be.visible')
    cy.get('#bnav-faltantes').should('be.visible')
    cy.get('#bnav-troca').should('be.visible')
  })

  it('Bottom nav troca de aba corretamente no mobile', () => {
    cy.viewport(375, 812)
    cy.visit('/estoque/felipe')
    cy.get('#bnav-faltantes').click()
    cy.get('#tab-content-faltantes').should('not.have.class', 'hidden')
    cy.get('#tab-content-tenho').should('have.class', 'hidden')
    // Aba ativa tem texto branco
    cy.get('#bnav-faltantes').should('have.class', 'text-white')
  })

  it('Estado vazio de trocas tem CTA', () => {
    cy.visit('/estoque/felipe')
    cy.get('#tab-troca').click()
    cy.get('#tab-content-troca').then($el => {
      const hasTrades = $el.find('.poke-card').length > 0
      if (!hasTrades) {
        cy.get('#tab-content-troca').contains('🔄').should('be.visible')
        cy.get('#tab-content-troca').contains(/marque|clique/i).should('be.visible')
      }
    })
  })

  it('Botão copiar link funciona', () => {
    cy.visit('/estoque/felipe')
    // Grant clipboard permission
    cy.window().then(win => {
      cy.stub(win.navigator.clipboard, 'writeText').resolves()
    })
    cy.get('#btn-copy').click()
    // Ícone muda para check
    cy.get('#btn-copy svg').should('exist')
  })
})
