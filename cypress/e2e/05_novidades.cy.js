// Wishlist automática, 100% IV, exemplares, duplo clique, fraquezas, painel e cabeçalho mobile.
// Cenário semeado por scripts/e2e_server.py (felipe tem Bulbasaur 100%; Misty oferece Lapras etc.)

describe('Cabeçalho mobile (deslogado)', () => {
  [320, 360, 390].forEach(w => {
    it(`${w}px — sem rolagem horizontal e botão Cadastrar visível`, () => {
      cy.viewport(w, 740)
      cy.visit('/')
      cy.document().then(doc => {
        expect(doc.documentElement.scrollWidth, 'scrollWidth').to.be.at.most(w)
      })
      cy.contains('header a', 'Cadastrar').then($a => {
        const r = $a[0].getBoundingClientRect()
        expect(r.right, 'borda direita do Cadastrar').to.be.at.most(w)
      })
    })
  })
})

describe('Wishlist automática', () => {
  beforeEach(() => cy.login())

  it('lista faltantes sem cadastro e classifica Alta x Evoluir', () => {
    cy.visit('/wishlist/')
    cy.contains('Adicionar à wishlist').should('not.exist')
    // Ivysaur: tem Bulbasaur → Evoluir com doces
    cy.get('.wish-card[data-num="2"]').should('have.attr', 'data-kind', 'evoluir')
      .and('contain', 'Bulbasaur')
    // Lapras: nada da família → Alta, com oferta da Misty
    cy.get('.wish-card[data-num="131"]').should('have.attr', 'data-kind', 'alta')
      .and('contain', 'p/ troca')
    // possuído não aparece
    cy.get('.wish-card[data-num="1"]').should('not.exist')
  })

  it('filtro por prioridade e link ?kind=evoluir', () => {
    cy.visit('/wishlist/?kind=evoluir')
    cy.get('.wish-card:visible').each($c => expect($c.attr('data-kind')).to.eq('evoluir'))
    cy.get('#wish-kind').select('alta')
    cy.get('.wish-card:visible').each($c => expect($c.attr('data-kind')).to.eq('alta'))
  })

  it('⭐ prioriza e leva o card ao topo após recarregar', () => {
    cy.visit('/wishlist/')
    cy.get('.wish-card[data-num="150"] .prio-btn').click()
    cy.get('.wish-card[data-num="150"]').should('have.attr', 'data-prio', 'true')
    cy.reload()
    cy.get('.wish-card').first().should('have.attr', 'data-num', '150')
    cy.get('.wish-card[data-num="150"] .prio-btn').click()  // desfaz
    cy.get('.wish-card[data-num="150"]').should('have.attr', 'data-prio', 'false')
  })
})

describe('100% IV e exemplares', () => {
  beforeEach(() => cy.login())

  it('coleção mostra selo 100 e o toggle preserva o shiny', () => {
    cy.visit('/collection/?q=pikachu')
    cy.get('.poke-card[data-poke-id="25"]').as('pika')
    cy.get('@pika').should('have.attr', 'data-shiny', 'true')
    cy.get('@pika').find('.perfect-btn').click()
    cy.get('@pika').should('have.attr', 'data-perfect', 'true')
    cy.get('@pika').find('.perfect-badge').should('be.visible')
    // ajustar quantidade NÃO pode apagar shiny nem 100% (bug antigo)
    cy.get('@pika').find('button').contains('+').click()
    cy.get('@pika').should('have.attr', 'data-shiny', 'true').and('have.attr', 'data-perfect', 'true')
    cy.get('@pika').find('.perfect-btn').click()  // desfaz
    cy.get('@pika').find('button').contains('−').click()
  })

  it('duplo clique abre a carta expandida com exemplares e fraquezas', () => {
    cy.visit('/collection/?q=bulbasaur')
    cy.get('.poke-card[data-poke-id="1"] img').dblclick()
    cy.get('#poke-modal').should('be.visible')
    cy.get('#modal-individuals').should('have.attr', 'open')
    cy.get('#ind-list').should('contain', 'CP 1102').and('contain', '💯 100%').and('contain', 'Vine Whip')
    cy.contains('Fraquezas e resistências').parent('details').should('have.attr', 'open')
    cy.contains('Como defensor').parent().should('contain', 'Fogo')   // planta/veneno leva 1,6× de fogo
    cy.contains('Como atacante').should('be.visible')
  })

  it('clique simples abre o modal normal (exemplares recolhidos)', () => {
    cy.visit('/collection/?q=bulbasaur')
    cy.get('.poke-card[data-poke-id="1"] img').click()
    cy.get('#modal-individuals').should('not.have.attr', 'open')
  })

  it('cadastro rápido de exemplar 15/15/15 marca 100% sozinho', () => {
    cy.visit('/collection/?q=squirtle')
    cy.get('.poke-card[data-poke-id="7"]').should('have.attr', 'data-perfect', 'false')
    cy.get('.poke-card[data-poke-id="7"] img').dblclick()
    cy.get('#ind-form input[name="cp"]').type('900')
    cy.get('#ind-form').contains('15/15/15').click()
    cy.get('#ind-form').submit()
    cy.get('#ind-list').should('contain', 'CP 900').and('contain', '💯 100%')
    cy.get('.modal-perfect').should('contain', 'Tenho 100%')
    // remove para não poluir
    cy.on('window:confirm', () => true)
    cy.get('#ind-list button[title="Remover exemplar"]').first().click()
    cy.get('.modal-perfect').should('contain', '100%?')
  })
})

describe('Painel e trocas', () => {
  beforeEach(() => cy.login())

  it('painel mostra Vitórias rápidas com link para a Wishlist filtrada', () => {
    cy.visit('/')
    cy.contains('Vitórias rápidas')
    cy.contains('a', 'na Wishlist').should('have.attr', 'href').and('include', 'kind=evoluir')
  })

  it('Trocas busca matches sozinha e mostra "Propor troca"', () => {
    cy.visit('/trades/')
    cy.contains('misty')
    cy.contains('Propor troca')
  })
})
