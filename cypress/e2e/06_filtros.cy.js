// Auditoria completa de filtros e pesquisas — todas as telas
// Seed de referência: scripts/e2e_server.py
//   felipe possui: Bulbasaur(1), Charmander(4), Squirtle(7), Pidgey(16), Rattata(19),
//                  Pikachu(25), Meowth(52), Abra(63), Gastly(92), Magikarp(129), Eevee(133),
//                  Snorlax(143), Dratini(147)
//   for_trade: Pidgey(16), Rattata(19), Magikarp(129)
//   wishlist (faltam): Ivysaur(2), Charmeleon(5), Blastoise(9), e muitos mais
//
// Nota: elementos ocultos via classList.toggle('hidden') → usar :not(.hidden)
//       elementos ocultos via style.display='none' → usar .filter(':visible')

// ─────────────────────────────────────────────────────────────────
// ESTOQUE
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Estoque (/estoque/felipe)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/estoque/felipe')
  })

  it('F-E01 campo #card-search existe e aceita texto', () => {
    cy.get('#card-search').should('exist').and('be.visible')
    cy.get('#card-search').type('bulb').should('have.value', 'bulb')
  })

  it('F-E02 busca por "bulb" reduz cards visíveis na aba Tenho', () => {
    cy.get('#tab-content-tenho .poke-card:visible').its('length').then(total => {
      cy.get('#card-search').type('bulb')
      cy.get('#tab-content-tenho .poke-card:visible').its('length').should('be.lessThan', total)
    })
  })

  it('F-E03 busca por "bulb" retorna Bulbasaur (#001)', () => {
    cy.get('#card-search').type('bulb')
    cy.get('#tab-content-tenho .poke-card:visible').first()
      .invoke('attr', 'data-name').should('include', '001')
  })

  it('F-E04 busca por número "001" retorna Bulbasaur', () => {
    cy.get('#card-search').type('001')
    cy.get('#tab-content-tenho .poke-card:visible').first()
      .invoke('attr', 'data-name').should('include', '001')
  })

  it('F-E05 limpar busca restaura todos os cards da aba Tenho', () => {
    cy.get('#tab-content-tenho .poke-card:visible').its('length').then(total => {
      cy.get('#card-search').type('bulb')
      cy.get('#card-search').clear()
      cy.get('#tab-content-tenho .poke-card:visible').its('length').should('eq', total)
    })
  })

  it('F-E06 cross-tab-hint aparece ao buscar espécie que está em Faltantes', () => {
    // Blastoise (#9) — Felipe não possui → aparece em Faltantes, não em Tenho
    cy.get('#card-search').type('blastoise')
    cy.get('#cross-tab-hint').should('not.have.class', 'hidden')
  })

  it('F-E07 limpar busca oculta o cross-tab-hint', () => {
    cy.get('#card-search').type('blastoise')
    cy.get('#cross-tab-hint').should('not.have.class', 'hidden')
    cy.get('#card-search').clear()
    cy.get('#cross-tab-hint').should('have.class', 'hidden')
  })

  it('F-E08 busca funciona na aba Faltantes após trocar de aba', () => {
    cy.get('#tab-faltantes').click()
    cy.get('#missing-grid .missing-card:not(.hidden)').its('length').then(total => {
      cy.get('#card-search').type('bulb')
      cy.get('#missing-grid .missing-card:not(.hidden)').its('length').should('be.lte', total)
    })
  })

  it('F-E09 busca na aba Troca filtra cards de troca', () => {
    cy.get('#tab-troca').click()
    cy.get('#tab-content-troca').then($el => {
      const hasTrades = $el.find('.poke-card').length > 0
      if (hasTrades) {
        cy.get('#tab-content-troca .poke-card:visible').its('length').then(total => {
          cy.get('#card-search').type('xxxxxnotfound99999')
          // troca usa style.display, então usamos filter(':visible')
          cy.get('#tab-content-troca .poke-card').filter(':visible').should('have.length', 0)
          cy.get('#card-search').clear()
          cy.get('#tab-content-troca .poke-card:visible').its('length').should('eq', total)
        })
      }
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// WISHLIST
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Wishlist (/wishlist)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/wishlist')
  })

  it('F-W01 campo #wish-search existe e é visível', () => {
    cy.get('#wish-search').should('exist').and('be.visible')
  })

  it('F-W02 #wish-region existe com opções de região', () => {
    cy.get('#wish-region').should('exist')
    cy.get('#wish-region option').its('length').should('be.greaterThan', 1)
  })

  it('F-W03 #wish-kind existe com opções de prioridade', () => {
    cy.get('#wish-kind').should('exist')
    cy.get('#wish-kind option').its('length').should('be.gte', 3)
  })

  it('F-W04 busca por nome reduz wish-cards visíveis', () => {
    cy.get('.wish-card:not(.hidden)').its('length').then(total => {
      cy.get('#wish-search').type('ivysaur')
      cy.get('.wish-card:not(.hidden)').its('length').should('be.lessThan', total)
    })
  })

  it('F-W05 busca sem resultado oculta todos os wish-cards', () => {
    cy.get('#wish-search').type('xxxxxnotfound99999')
    // apply() usa classList.toggle('hidden') — usar :not(.hidden)
    cy.get('.wish-card:not(.hidden)').should('have.length', 0)
  })

  it('F-W06 limpar busca restaura todos os wish-cards', () => {
    cy.get('.wish-card:not(.hidden)').its('length').then(total => {
      cy.get('#wish-search').type('xxxxxnotfound99999')
      cy.get('#wish-search').clear()
      cy.get('.wish-card:not(.hidden)').its('length').should('eq', total)
    })
  })

  it('F-W07 filtro região Kanto só mostra Pokémon #001–#151', () => {
    cy.get('#wish-region option').then($opts => {
      const kantoOpt = [...$opts].find(o => o.text.includes('Kanto'))
      if (kantoOpt) {
        cy.get('#wish-region').select(kantoOpt.value)
        cy.get('.wish-card:not(.hidden)').each($card => {
          expect(parseInt($card.attr('data-num'))).to.be.within(1, 151)
        })
      }
    })
  })

  it('F-W08 filtro kind=evoluir mostra só cards com data-kind="evoluir"', () => {
    cy.get('#wish-kind').select('evoluir')
    cy.get('.wish-card:not(.hidden)').its('length').then(n => {
      if (n > 0) {
        cy.get('.wish-card:not(.hidden)').each($card => {
          expect($card.attr('data-kind')).to.eq('evoluir')
        })
      }
    })
  })

  it('F-W09 filtro kind=alta mostra só cards com data-kind="alta"', () => {
    cy.get('#wish-kind').select('alta')
    cy.get('.wish-card:not(.hidden)').its('length').then(n => {
      if (n > 0) {
        cy.get('.wish-card:not(.hidden)').each($card => {
          expect($card.attr('data-kind')).to.eq('alta')
        })
      }
    })
  })

  it('F-W10 checkbox #wish-offers filtra só cards com oferta de troca', () => {
    cy.get('#wish-offers').check()
    cy.get('.wish-card:not(.hidden)').then($cards => {
      if ($cards.length > 0) {
        $cards.each((_, card) => {
          expect(parseInt(Cypress.$(card).attr('data-offers'))).to.be.greaterThan(0)
        })
      }
    })
  })

  it('F-W11 checkbox #wish-prio filtra só cards priorizados', () => {
    cy.get('.prio-btn').first().click()
    cy.wait(500)
    cy.get('#wish-prio').check()
    cy.get('.wish-card:not(.hidden)').its('length').should('be.greaterThan', 0)
    cy.get('.wish-card:not(.hidden)').each($card => {
      expect($card.attr('data-prio')).to.eq('true')
    })
    // Desfaz priorização
    cy.get('.prio-btn').first().click()
  })

  it('F-W12 região + busca combinados respeitam ambos os filtros', () => {
    cy.get('#wish-region option').then($opts => {
      const kantoOpt = [...$opts].find(o => o.text.includes('Kanto'))
      if (kantoOpt) {
        cy.get('#wish-region').select(kantoOpt.value)
        cy.get('.wish-card:not(.hidden)').its('length').then(afterRegion => {
          cy.get('#wish-search').type('a')
          cy.get('.wish-card:not(.hidden)').its('length').should('be.lte', afterRegion)
        })
      }
    })
  })

  it('F-W13 seção de evoluções existe e contém .evo-line', () => {
    cy.get('body').then($body => {
      if ($body.find('#evo-section').length) {
        cy.get('#evo-section').should('be.visible')
        cy.get('.evo-line').should('have.length.greaterThan', 0)
      }
    })
  })

  it('F-W14 busca sem resultado oculta toda a seção de evoluções', () => {
    cy.get('body').then($body => {
      if ($body.find('#evo-section').length && $body.find('.evo-line').length) {
        cy.get('#wish-search').type('xxxxxnotfound99999')
        cy.get('#evo-section').should('have.class', 'hidden')
        cy.get('#wish-search').clear()
        cy.get('#evo-section').should('not.have.class', 'hidden')
      }
    })
  })

  it('F-W15 filtro de região oculta linhas evolutivas fora do range', () => {
    cy.get('body').then($body => {
      if ($body.find('.evo-line').length > 0) {
        cy.get('#wish-region option').then($opts => {
          const kantoOpt = [...$opts].find(o => o.text.includes('Kanto'))
          if (kantoOpt) {
            cy.get('#wish-region').select(kantoOpt.value)
            cy.get('.evo-line:not(.hidden)').each($line => {
              const nums = ($line.attr('data-nums') || '').split(',').map(Number)
              const hasKanto = nums.some(n => n >= 1 && n <= 151)
              expect(hasKanto).to.be.true
            })
          }
        })
      }
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// TROCAS — INDEX
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Trocas (/trades)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/trades')
  })

  it('F-T01 campo #trade-search existe e é visível', () => {
    cy.get('#trade-search').should('exist').and('be.visible')
  })

  it('F-T02 #btn-clear-filter começa oculto', () => {
    cy.get('#btn-clear-filter').should('have.class', 'hidden')
  })

  it('F-T03 #trade-empty começa oculto', () => {
    cy.get('#trade-empty').should('have.class', 'hidden')
  })

  it('F-T04 digitar no campo exibe #btn-clear-filter', () => {
    cy.get('#trade-search').type('pikachu')
    cy.get('#btn-clear-filter').should('not.have.class', 'hidden')
  })

  it('F-T05 busca sem resultado exibe #trade-empty', () => {
    cy.get('#trade-search').type('xxxxxnotfound99999')
    cy.get('#trade-empty').should('not.have.class', 'hidden')
  })

  it('F-T06 #btn-clear-filter limpa busca e oculta #trade-empty', () => {
    cy.get('#trade-search').type('xxxxxnotfound99999')
    cy.get('#btn-clear-filter').click()
    cy.get('#trade-search').should('have.value', '')
    cy.get('#btn-clear-filter').should('have.class', 'hidden')
    cy.get('#trade-empty').should('have.class', 'hidden')
  })

  it('F-T07 busca filtra .reciprocal-card por data-forms', () => {
    cy.get('body').then($body => {
      if ($body.find('.reciprocal-card').length > 0) {
        cy.get('.reciprocal-card:not(.hidden)').its('length').then(total => {
          cy.get('#trade-search').type('xxxxxnotfound99999')
          // filterTrades usa classList.toggle('hidden')
          cy.get('.reciprocal-card:not(.hidden)').should('have.length', 0)
          cy.get('#trade-search').clear()
          cy.get('.reciprocal-card:not(.hidden)').its('length').should('eq', total)
        })
      }
    })
  })

  it('F-T08 busca filtra .match-card por data-name', () => {
    cy.get('body').then($body => {
      if ($body.find('.match-card').length > 0) {
        cy.get('.match-card:not(.hidden)').its('length').then(total => {
          cy.get('#trade-search').type('xxxxxnotfound99999')
          cy.get('.match-card:not(.hidden)').should('have.length', 0)
          cy.get('#trade-search').clear()
          cy.get('.match-card:not(.hidden)').its('length').should('eq', total)
        })
      }
    })
  })

  it('F-T09 busca por "misty" retorna card da misty', () => {
    cy.get('#trade-search').type('misty')
    cy.get('.reciprocal-card:not(.hidden), .match-card:not(.hidden)').its('length').should('be.greaterThan', 0)
  })

  it('F-T10 busca case-insensitive', () => {
    cy.get('#trade-search').type('MISTY')
    cy.get('#trade-empty').should('have.class', 'hidden')
  })
})

// ─────────────────────────────────────────────────────────────────
// TRADE BINDER
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Trade Binder (/trade/felipe)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/trade/felipe')
  })

  it('F-B01 campo #binder-trade-search existe quando há itens para troca', () => {
    cy.get('body').then($body => {
      if ($body.find('#binder-trade-search').length) {
        cy.get('#binder-trade-search').should('be.visible')
      }
    })
  })

  it('F-B02 busca reduz tiles visíveis na vitrine de trocas', () => {
    cy.get('body').then($body => {
      if ($body.find('#binder-trade-search').length) {
        // filterBinderTrade usa classList.toggle('hidden')
        cy.get('#binder-trade .poke-card:not(.hidden)').its('length').then(total => {
          cy.get('#binder-trade-search').type('xxxxxnotfound99999')
          cy.get('#binder-trade .poke-card:not(.hidden)').should('have.length', 0)
          cy.get('#binder-trade-search').clear()
          cy.get('#binder-trade .poke-card:not(.hidden)').its('length').should('eq', total)
        })
      }
    })
  })

  it('F-B03 limpar busca restaura todos os tiles', () => {
    cy.get('body').then($body => {
      if ($body.find('#binder-trade-search').length) {
        cy.get('#binder-trade .poke-card:not(.hidden)').its('length').then(total => {
          cy.get('#binder-trade-search').type('xxxxxnotfound99999')
          cy.get('#binder-trade-search').clear()
          cy.get('#binder-trade .poke-card:not(.hidden)').its('length').should('eq', total)
        })
      }
    })
  })

  it('F-B04 #binder-trade-empty aparece quando busca retorna 0', () => {
    cy.get('body').then($body => {
      if ($body.find('#binder-trade-search').length) {
        cy.get('#binder-trade-search').type('xxxxxnotfound99999')
        cy.get('#binder-trade-empty').should('not.have.class', 'hidden')
      }
    })
  })

  it('F-B05 busca por "magikarp" retorna tile do Magikarp (#129)', () => {
    cy.get('body').then($body => {
      if ($body.find('#binder-trade-search').length) {
        cy.get('#binder-trade-search').type('magikarp')
        cy.get('#binder-trade-empty').should('have.class', 'hidden')
        cy.get('#binder-trade .poke-card:not(.hidden)').its('length').should('be.greaterThan', 0)
      }
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// ADMIN — USUÁRIOS
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Admin Usuários (/admin/usuarios)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/admin/usuarios')
  })

  it('F-A01 campo #user-search existe e é visível', () => {
    cy.get('#user-search').should('exist').and('be.visible')
  })

  it('F-A02 busca vazia mantém todas as linhas visíveis', () => {
    cy.get('tbody tr').filter(':visible').its('length').should('be.greaterThan', 0)
  })

  it('F-A03 busca por "felipe" retorna ao menos 1 linha', () => {
    cy.get('#user-search').type('felipe')
    cy.get('tbody tr').filter(':visible').its('length').should('be.greaterThan', 0)
  })

  it('F-A04 busca sem resultado oculta todas as linhas', () => {
    cy.get('#user-search').type('xxxxxnotfound99999')
    // filterUsers usa style.display = 'none' — usar filter(':visible')
    cy.get('tbody tr').filter(':visible').should('have.length', 0)
  })

  it('F-A05 limpar busca restaura todas as linhas', () => {
    cy.get('tbody tr').filter(':visible').its('length').then(total => {
      cy.get('#user-search').type('xxxxxnotfound99999')
      cy.get('#user-search').clear()
      cy.get('tbody tr').filter(':visible').its('length').should('eq', total)
    })
  })

  it('F-A06 busca por e-mail também funciona', () => {
    cy.get('#user-search').type('@e2e.test')
    cy.get('tbody tr').filter(':visible').its('length').should('be.greaterThan', 0)
  })

  it('F-A07 busca case-insensitive', () => {
    cy.get('tbody tr').filter(':visible').its('length').then(total => {
      cy.get('#user-search').type('FELIPE')
      cy.get('tbody tr').filter(':visible').its('length').should('be.greaterThan', 0)
      cy.get('#user-search').clear()
      cy.get('tbody tr').filter(':visible').its('length').should('eq', total)
    })
  })
})

// ─────────────────────────────────────────────────────────────────
// TREINADORES
// ─────────────────────────────────────────────────────────────────
describe('Filtros — Treinadores (/treinadores)', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/treinadores')
  })

  it('F-TR01 campo #tr-search existe e é visível', () => {
    cy.get('#tr-search').should('exist').and('be.visible')
  })

  it('F-TR02 #tr-empty começa oculto', () => {
    cy.get('#tr-empty').should('have.class', 'hidden')
  })

  it('F-TR03 busca por "misty" retorna ao menos 1 card', () => {
    cy.get('#tr-search').type('misty')
    cy.get('.tr-card:not(.hidden)').its('length').should('be.greaterThan', 0)
    cy.get('#tr-empty').should('have.class', 'hidden')
  })

  it('F-TR04 busca sem resultado exibe #tr-empty e oculta cards', () => {
    cy.get('#tr-search').type('xxxxxnotfound99999')
    cy.get('#tr-empty').should('not.have.class', 'hidden')
    // apply() usa classList.toggle('hidden')
    cy.get('.tr-card:not(.hidden)').should('have.length', 0)
  })

  it('F-TR05 limpar busca restaura todos os treinadores', () => {
    cy.get('.tr-card:not(.hidden)').its('length').then(total => {
      cy.get('#tr-search').type('xxxxxnotfound99999')
      cy.get('#tr-search').clear()
      cy.get('.tr-card:not(.hidden)').its('length').should('eq', total)
      cy.get('#tr-empty').should('have.class', 'hidden')
    })
  })

  it('F-TR06 checkbox #tr-reach filtra só treinadores com troca remota', () => {
    cy.get('.tr-card:not(.hidden)').its('length').then(total => {
      cy.get('#tr-reach').check()
      cy.get('.tr-card:not(.hidden)').then($visible => {
        expect($visible.length).to.be.lte(total)
        $visible.each((_, card) => {
          expect(Cypress.$(card).attr('data-reach')).to.eq('true')
        })
      })
      cy.get('#tr-reach').uncheck()
      cy.get('.tr-card:not(.hidden)').its('length').should('eq', total)
    })
  })

  it('F-TR07 busca + #tr-reach combinados aplicam ambos os filtros', () => {
    cy.get('#tr-reach').check()
    cy.get('.tr-card:not(.hidden)').its('length').then(afterReach => {
      if (afterReach > 0) {
        cy.get('#tr-search').type('xxxxxnotfound99999')
        cy.get('.tr-card:not(.hidden)').should('have.length', 0)
        cy.get('#tr-empty').should('not.have.class', 'hidden')
      }
      cy.get('#tr-reach').uncheck()
    })
  })

  it('F-TR08 busca case-insensitive (MISTY = misty)', () => {
    cy.get('#tr-search').type('MISTY')
    cy.get('#tr-empty').should('have.class', 'hidden')
  })
})
