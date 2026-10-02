// Testes da tela /collection/catalogar

describe('Catalogar por região', () => {
  beforeEach(() => {
    cy.login()
  })

  it('Rota /collection/catalogar carrega com Kanto default', () => {
    cy.visit('/collection/catalogar')
    cy.contains('Catalogar Coleção').should('be.visible')
    cy.contains('Kanto').should('be.visible')
    cy.get('.poke-card').its('length').should('be.greaterThan', 0)
  })

  it('Seletor de região exibe todas as 10 regiões', () => {
    cy.visit('/collection/catalogar')
    const regioes = ['Kanto','Johto','Hoenn','Sinnoh','Unova','Kalos','Alola','Galar','Hisui','Paldea']
    regioes.forEach(r => cy.contains(r).should('be.visible'))
  })

  it('Troca de região carrega novos cards', () => {
    cy.visit('/collection/catalogar')
    cy.get('.poke-card').its('length').then(kantoCount => {
      cy.contains('a', 'Johto').click()
      cy.url().should('include', 'regiao=Johto')
      cy.get('.poke-card').its('length').should('be.greaterThan', 0)
      cy.get('.poke-card').its('length').should('not.eq', kantoCount)
    })
  })

  it('Kalos carrega os 72 Pokémon (ou menos se faltam no DB)', () => {
    cy.visit('/collection/catalogar?regiao=Kalos')
    cy.get('.poke-card').its('length').should('be.greaterThan', 40)
    cy.contains('#650').should('be.visible')
  })

  it('Toggle modo FALTA / TENHO funciona', () => {
    cy.visit('/collection/catalogar')
    // Default é FALTA (ativo)
    cy.get('#btn-modo-falta').should('have.class', 'bg-red-500')
    cy.get('#btn-modo-tenho').should('not.have.class', 'bg-green-500')
    // Muda para TENHO
    cy.get('#btn-modo-tenho').click()
    cy.get('#btn-modo-tenho').should('have.class', 'bg-green-500')
    cy.get('#btn-modo-falta').should('not.have.class', 'bg-red-500')
    // Texto muda
    cy.get('#modo-desc').should('contain', 'TENHO')
  })

  it('Clicar em card seleciona com ring vermelho (modo FALTA)', () => {
    cy.visit('/collection/catalogar')
    cy.get('#btn-modo-falta').click() // garante modo falta
    cy.get('.poke-card').first().click()
    cy.get('.poke-card').first().should('have.class', 'ring-2')
    cy.get('#count-selected').should('contain', '1')
  })

  it('Clicar novamente desseleciona o card', () => {
    cy.visit('/collection/catalogar')
    cy.get('.poke-card').first().click()
    cy.get('.poke-card').first().click()
    cy.get('.poke-card').first().should('not.have.class', 'ring-2')
    cy.get('#count-selected').should('contain', '0')
  })

  it('Barra de confirmação aparece ao selecionar e some ao limpar', () => {
    cy.visit('/collection/catalogar')
    cy.get('#confirm-bar').should('have.class', 'hidden')
    cy.get('.poke-card').first().click()
    cy.get('#confirm-bar').should('not.have.class', 'hidden')
    cy.contains('Limpar').click()
    cy.get('#confirm-bar').should('have.class', 'hidden')
  })

  it('Botão Selecionar todos seleciona todos os visíveis', () => {
    cy.visit('/collection/catalogar')
    cy.contains('Selecionar todos').click()
    cy.get('#count-selected').invoke('text').then(n => {
      expect(parseInt(n)).to.be.greaterThan(0)
    })
  })

  it('Busca filtra cards por nome', () => {
    cy.visit('/collection/catalogar')
    cy.get('#search-input').type('bulb')
    cy.get('.poke-card:visible').its('length').should('be.lessThan', 10)
  })

  it('POST /collection/regiao aceita JSON e retorna ok', () => {
    cy.visit('/collection/catalogar?regiao=Kanto')
    cy.getCookie('session').then(cookie => {
      // Pega o CSRF token da página
      cy.get('meta[name="csrf-token"]').invoke('attr', 'content').then(csrf => {
        cy.request({
          method: 'POST',
          url: '/collection/regiao',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf,
          },
          body: { start: 1, end: 151, modo: 'falta', ids: [] },
        }).then(res => {
          expect(res.status).to.eq(200)
          expect(res.body.ok).to.be.true
          expect(res.body).to.have.keys(['ok', 'owned', 'missing'])
        })
      })
    })
  })

  it('Confirmar salva seleção e recarrega página', () => {
    cy.visit('/collection/catalogar?regiao=Hoenn')
    // Seleciona 3 cards
    cy.get('.poke-card').eq(0).click()
    cy.get('.poke-card').eq(1).click()
    cy.get('.poke-card').eq(2).click()

    cy.intercept('POST', '/collection/regiao').as('salvar')
    cy.contains('Confirmar').click()
    cy.wait('@salvar').its('response.body.ok').should('be.true')
    // Página recarrega
    cy.url().should('include', '/collection/catalogar')
  })
})
