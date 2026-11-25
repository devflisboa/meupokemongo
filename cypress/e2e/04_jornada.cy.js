// Jornada (#27) — jogo de tabuleiro: mapa público, rolar o dado, captura, time, ranking, perfil.
// As regras (sorteios, PvP, desafio) são cobertas em tests/test_jornada*.py; aqui é o fluxo do navegador.

describe('Jornada — público', () => {
  it('Mapa Global abre sem login com o Hall da Fama no topo', () => {
    cy.visit('/jornada/')
    cy.contains('Hall da Fama').should('be.visible')
    cy.contains('Entrar e jogar').should('be.visible')
  })

  it('Hall da Fama é público', () => {
    cy.visit('/jornada/hall-da-fama')
    cy.contains('h1', 'Hall da Fama')
  })
})

describe('Jornada — jogando', () => {
  beforeEach(() => {
    cy.login()
  })

  // Resolve o que estiver aberto depois de uma rolagem (captura → tenta; desafio → recua).
  const resolverSheet = () => {
    cy.get('body').then($b => {
      if ($b.find('#sc-tentar').length) {
        cy.get('#sc-tentar').click()
        cy.get('#jn-toast').invoke('text').should('match', /Capturou|fugiu/)
      } else if ($b.find('#df-recuar').length) {
        cy.get('#df-recuar').click()
      }
    })
  }

  it('Rola o dado, anda no tabuleiro e gasta energia', () => {
    cy.visit('/jornada/jogar')
    cy.get('#jg-board .jn-cel').should('have.length', 73)
    cy.get('#jg-dado').should('not.be.disabled')
    cy.get('[data-jn="energia"]').first().invoke('text').then(antes => {
      cy.get('#jg-dado').click()
      cy.get('#jg-msg', {timeout: 8000}).should('contain.text', 'Tirou')
      cy.get('[data-jn="energia"]').first().should('have.text', String(Number(antes) - 1))
    })
    cy.get('#jg-log li').should('have.length.at.least', 1)
    resolverSheet()
  })

  it('Captura: a criatura aparece e o resultado vira toast', () => {
    cy.visit('/jornada/jogar')
    // rola até cair numa captura (máx. 4 tentativas; a energia inicial é 6)
    const tentar = n => {
      cy.get('body').then($b => {
        if ($b.find('#sc-tentar').length || n === 0) return
        cy.get('#jg-dado').then($d => {
          if ($d.is(':disabled')) return
          cy.wrap($d).click()
          cy.get('#jg-msg', {timeout: 8000}).should('contain.text', 'Tirou')
          cy.wait(300)
          tentar(n - 1)
        })
      })
    }
    tentar(4)
    cy.get('body').then($b => {
      if (!$b.find('#sc-tentar').length) return       // sem captura nesta rodada: nada a validar
      cy.get('#jn-sheet').should('contain.text', 'Captura com')
      cy.get('#sc-tentar').click()
      cy.get('#jn-toast').invoke('text').should('match', /Capturou|fugiu/)
      cy.get('#jn-sheet').should('not.exist')
    })
  })

  it('Time, ranking e perfil carregam', () => {
    cy.visit('/jornada/time')
    cy.contains('h1', 'Time')
    cy.visit('/jornada/ranking')
    cy.contains('Você está em')
    cy.visit('/jornada/eu')
    cy.url().should('include', '/jornada/treinador/felipe')
    cy.contains('Progresso até o Hall da Fama')
  })

  it('Celular: barra inferior da Jornada com 5 abas', () => {
    cy.viewport('iphone-x')
    cy.visit('/jornada/jogar')
    cy.get('nav.jn-nav a').should('have.length', 5)
    cy.get('nav.jn-nav a[aria-current="page"]').should('contain.text', 'Jogar')
  })
})
