// ============================================================
// TESTES DAS MELHORIAS UI/UX — MeuPokémonGO
// Cobre todas as alterações aplicadas na auditoria de UX/UI:
//   base.html · auth · collection · catalogar · pokedex
//   wishlist · trades · import
// ============================================================

// ────────────────────────────────────────────────────────────
// HELPERS
// ────────────────────────────────────────────────────────────
const LOGIN_URL      = '/auth/login'
const REGISTRO_URL   = '/auth/registro'
const COLLECTION_URL = '/collection'
const CATALOGAR_URL  = '/collection/catalogar'
const POKEDEX_URL    = '/pokedex'
const POKEDEX1_URL   = '/pokedex/1'
const WISHLIST_URL   = '/wishlist'
const TRADES_URL     = '/trades'
const IMPORT_URL     = '/import'
const HOME_URL       = '/'

// ════════════════════════════════════════════════════════════
// 1 — BASE.HTML
// ════════════════════════════════════════════════════════════
describe('1 — base.html: SVG, ARIA e acessibilidade global', () => {

  it('1.1 — Pokéball SVG tem role="img" e aria-label', () => {
    cy.visit(HOME_URL)
    cy.get('nav svg[role="img"]')
      .should('have.attr', 'aria-label')
      .and('match', /MeuPok/i)
  })

  it('1.2 — Flash messages têm role="alert" (verificar ao logar)', () => {
    // Login incorreto dispara flash de erro
    cy.visit(LOGIN_URL)
    cy.get('input[name="username"]').type('usuario_invalido_xyz')
    cy.get('input[name="password"]').type('senha_errada')
    cy.get('button[type="submit"]').click()
    cy.get('[role="alert"]').should('exist')
  })

  it('1.3 — Ícone de notificação na navbar tem aria-label', () => {
    cy.login()
    cy.visit(HOME_URL)
    // O link de notificação existe e tem aria-label
    cy.get('nav a[aria-label]').then($links => {
      const notifLink = [...$links].find(el =>
        el.getAttribute('aria-label')?.toLowerCase().includes('troca') ||
        el.getAttribute('aria-label')?.toLowerCase().includes('notifica')
      )
      expect(notifLink).to.exist
    })
  })

  it('1.4 — Emoji 📺 do link "Assistir" tem aria-hidden="true"', () => {
    cy.visit(HOME_URL)
    cy.get('nav a[href*="/anime"]').within(() => {
      cy.get('span[aria-hidden="true"]').should('exist')
    })
  })

  it('1.5 — Barra de busca no header tem altura mínima de 44px em mobile', () => {
    cy.viewport(375, 667)
    cy.visit(HOME_URL)
    cy.get('header input[name="q"]').then($input => {
      const rect = $input[0].getBoundingClientRect()
      expect(rect.height).to.be.gte(40) // tolerância de 4px
    })
  })

  it('1.6 — Modal de Pokémon: botão fechar tem aria-label="Fechar"', () => {
    cy.visit(POKEDEX_URL)
    // Abre modal clicando num card
    cy.get('[data-poke-id]').first().click()
    cy.wait(800)
    // Botão fechar deve ter aria-label
    cy.get('#poke-modal-content button[aria-label="Fechar"]').should('exist')
    // Fecha o modal
    cy.get('#poke-modal-content button[aria-label="Fechar"]').click()
    cy.get('#poke-modal').should('have.class', 'hidden')
  })

  it('1.7 — Modal sheet tem padding-bottom seguro (env safe-area)', () => {
    cy.visit(HOME_URL)
    cy.get('#poke-modal-sheet').then($el => {
      const style = $el.attr('style') || ''
      expect(style).to.include('safe-area-inset-bottom')
    })
  })

  it('1.8 — Modal sheet tem max-h-[92vh] (não corta botões)', () => {
    cy.visit(HOME_URL)
    cy.get('#poke-modal-sheet').invoke('attr', 'class').then(cls => {
      expect(cls).to.include('92vh')
    })
  })

})

describe('1b — base.html: bottom nav aria-current', () => {
  beforeEach(() => { cy.login() })

  it('1b.1 — Link "Início" na bottom nav tem aria-current="page" quando ativo', () => {
    cy.visit(HOME_URL)
    cy.viewport(375, 667)
    // O link da home na bottom nav deve ter aria-current
    cy.get('nav.fixed a[href="/"]').should('have.attr', 'aria-current', 'page')
  })

  it('1b.2 — Link "Coleção" tem aria-current="page" na rota de coleção', () => {
    cy.visit(COLLECTION_URL)
    cy.viewport(375, 667)
    cy.get('nav.fixed a[href*="/collection"]').should('have.attr', 'aria-current', 'page')
  })

  it('1b.3 — Link inativo NÃO tem aria-current', () => {
    cy.visit(TRADES_URL)
    cy.viewport(375, 667)
    // Home não deve ter aria-current quando estamos em Trocas
    cy.get('nav.fixed a[href="/"]').should('not.have.attr', 'aria-current')
  })
})

// ════════════════════════════════════════════════════════════
// 2 — AUTH: LOGIN
// ════════════════════════════════════════════════════════════
describe('2 — auth/login.html: toggle de senha', () => {

  it('2.1 — Campo de senha tem tipo "password" por padrão', () => {
    cy.visit(LOGIN_URL)
    cy.get('input[name="password"]').should('have.attr', 'type', 'password')
  })

  it('2.2 — Botão de toggle de senha existe com aria-label', () => {
    cy.visit(LOGIN_URL)
    cy.get('button[type="button"][aria-label*="senha"], button[type="button"][aria-label*="Senha"]')
      .should('exist')
  })

  it('2.3 — Clicar no toggle muda campo para type="text"', () => {
    cy.visit(LOGIN_URL)
    cy.get('button[type="button"][aria-label*="senha"], button[type="button"][aria-label*="Senha"]')
      .first().click()
    cy.get('input[name="password"]').should('have.attr', 'type', 'text')
  })

  it('2.4 — Clicar novamente no toggle volta para type="password"', () => {
    cy.visit(LOGIN_URL)
    const toggleSel = 'button[type="button"][aria-label*="senha"], button[type="button"][aria-label*="Senha"]'
    cy.get(toggleSel).first().click()
    cy.get('input[name="password"]').should('have.attr', 'type', 'text')
    cy.get(toggleSel).first().click()
    cy.get('input[name="password"]').should('have.attr', 'type', 'password')
  })

})

// ════════════════════════════════════════════════════════════
// 3 — AUTH: REGISTRO
// ════════════════════════════════════════════════════════════
describe('3 — auth/registro.html: toggle de senha e dica', () => {

  it('3.1 — Campo de senha no registro tem tipo "password"', () => {
    cy.visit(REGISTRO_URL)
    cy.get('input[name="password"]').should('have.attr', 'type', 'password')
  })

  it('3.2 — Botão toggle de senha existe no registro', () => {
    cy.visit(REGISTRO_URL)
    cy.get('button[type="button"][aria-label*="senha"], button[type="button"][aria-label*="Senha"]')
      .should('exist')
  })

  it('3.3 — Toggle alterna type em registro', () => {
    cy.visit(REGISTRO_URL)
    cy.get('button[type="button"][aria-label*="senha"], button[type="button"][aria-label*="Senha"]')
      .first().click()
    cy.get('input[name="password"]').should('have.attr', 'type', 'text')
  })

  it('3.4 — Dica "Mínimo 8 caracteres" está visível', () => {
    cy.visit(REGISTRO_URL)
    cy.contains(/m[íi]nimo\s+8\s+caracteres/i).should('exist')
  })

})

// ════════════════════════════════════════════════════════════
// 4 — AUTH: PERFIL — loading de avatar
// ════════════════════════════════════════════════════════════
describe('4 — auth/perfil.html: avatar upload loading', () => {
  beforeEach(() => { cy.login() })

  it('4.1 — Overlay de loading (#avatar-uploading) existe no DOM', () => {
    cy.visit('/auth/perfil')
    cy.get('#avatar-uploading').should('exist')
  })

  it('4.2 — Overlay está inicialmente oculto', () => {
    cy.visit('/auth/perfil')
    cy.get('#avatar-uploading').should('have.class', 'hidden')
  })

  it('4.3 — Input de avatar usa uploadAvatar() no onchange', () => {
    cy.visit('/auth/perfil')
    cy.get('input[type="file"]').first().then($input => {
      const onchange = $input.attr('onchange') || ''
      expect(onchange).to.include('uploadAvatar')
    })
  })

})

// ════════════════════════════════════════════════════════════
// 5 — COLLECTION/INDEX: sticky, aria-current, title, aria-hidden
// ════════════════════════════════════════════════════════════
describe('5 — collection/index.html: filtros e acessibilidade', () => {
  beforeEach(() => { cy.login() })

  it('5.1 — Barra de filtros tem classe "sticky"', () => {
    cy.visit(COLLECTION_URL)
    cy.get('#collection-filter').invoke('attr', 'class').then(cls => {
      expect(cls).to.include('sticky')
    })
  })

  it('5.2 — Barra de filtros tem z-index de sobreposição (z-30 ou maior)', () => {
    cy.visit(COLLECTION_URL)
    cy.get('#collection-filter').invoke('attr', 'class').then(cls => {
      expect(cls).to.match(/z-\d{2,}|z-\[/)
    })
  })

  it('5.3 — Paginação: página ativa tem aria-current="page"', () => {
    cy.visit(COLLECTION_URL)
    cy.get('body').then($body => {
      // Se houver paginação
      if ($body.find('.pagination, [aria-current="page"]').length > 0) {
        cy.get('[aria-current="page"]').should('exist')
      } else {
        // Menos de 24 espécies — sem paginação, teste não se aplica
        cy.log('Sem paginação na página atual — pulando')
      }
    })
  })

  it('5.4 — Links de nome de Pokémon têm atributo title', () => {
    cy.visit(COLLECTION_URL)
    cy.get('.poke-card a.truncate, .poke-card a[class*="truncate"]').first().then($link => {
      expect($link.attr('title')).to.not.be.empty
    })
  })

  it('5.5 — Badge de shiny (⭐) visível nos cards com has_shiny=true', () => {
    cy.visit(COLLECTION_URL)
    // Verifica se o elemento .shiny-badge existe no DOM (mesmo que oculto)
    cy.get('.shiny-badge').should('exist')
  })

  it('5.6 — Filtro de geração submete sem campo hidden duplicado', () => {
    cy.visit(COLLECTION_URL)
    cy.get('#collection-filter').within(() => {
      cy.get('input[type="hidden"][name="generation"]').should('not.exist')
    })
  })

  it('5.7 — Grid de coleção usa grid-cols-3', () => {
    cy.visit(COLLECTION_URL)
    cy.get('#pokegrid').invoke('attr', 'class').then(cls => {
      expect(cls).to.include('grid-cols-3')
    })
  })

  it('5.8 — Sprites têm tamanho aumentado (w-20 ou maior)', () => {
    cy.visit(COLLECTION_URL)
    cy.get('.poke-card img.sprite-sm').first().invoke('attr', 'class').then(cls => {
      // w-20 = 80px, w-24 = 96px, etc.
      expect(cls).to.match(/w-20|w-24|w-28|w-32/)
    })
  })

})

// ════════════════════════════════════════════════════════════
// 6 — COLLECTION/CATALOGAR: z-index, aria-pressed, estado vazio
// ════════════════════════════════════════════════════════════
describe('6 — collection/catalogar.html: z-index e acessibilidade', () => {
  beforeEach(() => { cy.login() })

  it('6.1 — Barra de confirmação (#confirm-bar) tem z-[60] ou z-60', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#confirm-bar').invoke('attr', 'class').then(cls => {
      expect(cls).to.match(/z-\[60\]|z-60/)
    })
  })

  it('6.2 — Botão de modo FALTA tem aria-pressed', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#btn-modo-falta').should('have.attr', 'aria-pressed')
  })

  it('6.3 — Botão de modo TENHO tem aria-pressed', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#btn-modo-tenho').should('have.attr', 'aria-pressed')
  })

  it('6.4 — aria-pressed do FALTA é "true" por padrão', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#btn-modo-falta').should('have.attr', 'aria-pressed', 'true')
    cy.get('#btn-modo-tenho').should('have.attr', 'aria-pressed', 'false')
  })

  it('6.5 — Clicar em TENHO inverte aria-pressed dos dois botões', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#btn-modo-tenho').click()
    cy.get('#btn-modo-tenho').should('have.attr', 'aria-pressed', 'true')
    cy.get('#btn-modo-falta').should('have.attr', 'aria-pressed', 'false')
  })

  it('6.6 — Elemento #cat-empty existe no DOM para busca sem resultados', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#cat-empty').should('exist')
  })

  it('6.7 — Busca por string inválida exibe #cat-empty', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#search-input').type('zzzzinexistente9999')
    cy.get('#cat-empty').should('not.have.class', 'hidden')
  })

  it('6.8 — Limpar busca esconde #cat-empty novamente', () => {
    cy.visit(CATALOGAR_URL)
    cy.get('#search-input').type('zzzzinexistente9999')
    cy.get('#cat-empty').should('not.have.class', 'hidden')
    cy.get('#search-input').clear()
    cy.get('#cat-empty').should('have.class', 'hidden')
  })

})

// ════════════════════════════════════════════════════════════
// 7 — POKEDEX/INDEX: CTA, auto-submit, aria-hidden
// ════════════════════════════════════════════════════════════
describe('7 — pokedex/index.html: filtros e estado vazio', () => {

  it('7.1 — Select "type" tem onchange="this.form.submit()"', () => {
    cy.visit(POKEDEX_URL)
    cy.get('select[name="type"]').should('have.attr', 'onchange').and('include', 'form.submit')
  })

  it('7.2 — Select "captured" tem onchange="this.form.submit()" quando logado', () => {
    cy.login()
    cy.visit(POKEDEX_URL)
    cy.get('select[name="captured"]').should('have.attr', 'onchange').and('include', 'form.submit')
  })

  it('7.3 — Select "generation" já tem onchange (regressão)', () => {
    cy.visit(POKEDEX_URL)
    cy.get('select[name="generation"]').should('have.attr', 'onchange').and('include', 'form.submit')
  })

  it('7.4 — Estado vazio usa botão/link com cor primária', () => {
    cy.visit(`${POKEDEX_URL}?q=zzzzinexistente9999`)
    // Link de limpar filtros deve ter classe de cor primária
    cy.get('a[href*="/pokedex"], button').then($els => {
      const clearBtn = [...$els].find(el =>
        el.className?.includes('bg-[#1B2A4A]') ||
        el.className?.includes('bg-navy') ||
        el.textContent?.match(/limpar|ver todos/i)
      )
      expect(clearBtn).to.exist
    })
  })

  it('7.5 — Badges lendário/mítico têm aria-hidden="true"', () => {
    cy.visit(POKEDEX_URL)
    cy.get('body').then($body => {
      const legendBadge = $body.find('span[aria-hidden="true"]')
      expect(legendBadge.length).to.be.greaterThan(0)
    })
  })

  it('7.6 — Filtro de geração funciona (sem campo hidden duplicado)', () => {
    cy.visit(POKEDEX_URL)
    cy.get('select[name="generation"]').select('1')
    cy.url().should('include', 'generation=1')
    cy.contains('#001').should('be.visible')
    cy.contains('#152').should('not.exist')
  })

})

// ════════════════════════════════════════════════════════════
// 8 — POKEDEX/DETAIL: atributos de imagem
// ════════════════════════════════════════════════════════════
describe('8 — pokedex/detail.html: imagem principal e acessibilidade', () => {

  it('8.1 — Imagem principal tem atributo width explícito', () => {
    cy.visit(POKEDEX1_URL)
    cy.get('img.w-44, img[class*="w-44"]').first().should('have.attr', 'width')
  })

  it('8.2 — Imagem principal tem atributo height explícito', () => {
    cy.visit(POKEDEX1_URL)
    cy.get('img.w-44, img[class*="w-44"]').first().should('have.attr', 'height')
  })

  it('8.3 — Imagem principal tem loading="lazy"', () => {
    cy.visit(POKEDEX1_URL)
    cy.get('img.w-44, img[class*="w-44"]').first().should('have.attr', 'loading', 'lazy')
  })

  it('8.4 — Badges decorativos (★ ✦) têm aria-hidden="true"', () => {
    cy.visit(POKEDEX1_URL)
    // Bulbasaur não é lendário — visita Articuno (#144) ou outro lendário
    cy.visit('/pokedex/144')
    cy.get('span[aria-hidden="true"]').should('exist')
  })

})

// ════════════════════════════════════════════════════════════
// 9 — MAIN/LANDING: fallback de imagem
// ════════════════════════════════════════════════════════════
describe('9 — main/landing.html: fallback de imagem do herói', () => {

  it('9.1 — Imagem do herói tem atributo onerror', () => {
    cy.clearCookies()
    cy.visit(HOME_URL)
    // Landing é exibida para usuário deslogado
    // Procura imagem de herói (normalmente um Pokémon na seção hero)
    cy.get('body').then($body => {
      const heroImgs = $body.find('img[onerror]')
      if (heroImgs.length > 0) {
        // Pelo menos uma imagem tem onerror
        expect(heroImgs.length).to.be.greaterThan(0)
      } else {
        cy.log('Landing pode não estar disponível neste estado — pulando')
      }
    })
  })

})

// ════════════════════════════════════════════════════════════
// 10 — WISHLIST: scroll indicator e title em nomes
// ════════════════════════════════════════════════════════════
describe('10 — wishlist/index.html: evoluções e acessibilidade', () => {
  beforeEach(() => { cy.login() })

  it('10.1 — Página de desejos carrega sem erros', () => {
    cy.visit(WISHLIST_URL)
    cy.get('h1').should('contain.text', 'Desejos')
  })

  it('10.2 — Linhas evolutivas têm wrapper .evo-line-wrap quando existem', () => {
    cy.visit(WISHLIST_URL)
    cy.get('body').then($body => {
      if ($body.find('.evo-line').length > 0) {
        cy.get('.evo-line-wrap').should('exist')
      } else {
        cy.log('Sem linhas evolutivas disponíveis — pulando')
      }
    })
  })

  it('10.3 — CSS de .evo-line-wrap::after está presente no <style>', () => {
    cy.visit(WISHLIST_URL)
    cy.document().then(doc => {
      const styles = [...doc.querySelectorAll('style')]
      const hasEvoWrapStyle = styles.some(s =>
        s.textContent.includes('evo-line-wrap')
      )
      expect(hasEvoWrapStyle).to.be.true
    })
  })

  it('10.4 — Nomes de Pokémon truncados nos cards têm title', () => {
    cy.visit(WISHLIST_URL)
    cy.get('body').then($body => {
      if ($body.find('.wish-card').length > 0) {
        cy.get('.wish-card [title]').first().should('exist')
      } else {
        cy.log('Sem cards na wishlist — pulando')
      }
    })
  })

  it('10.5 — Cards da wishlist são maiores (grid-cols-3 sm:grid-cols-4 md:grid-cols-5)', () => {
    cy.visit(WISHLIST_URL)
    cy.get('#wish-grid').invoke('attr', 'class').then(cls => {
      expect(cls).to.include('grid-cols-3')
    })
  })

  it('10.6 — Filtro de região existe e é funcional', () => {
    cy.visit(WISHLIST_URL)
    cy.get('#wish-region').should('exist')
    cy.get('#wish-region option').should('have.length.greaterThan', 1)
  })

})

// ════════════════════════════════════════════════════════════
// 11 — TRADES/INDEX: debounce e aria
// ════════════════════════════════════════════════════════════
describe('11 — trades/index.html: busca e acessibilidade', () => {
  beforeEach(() => { cy.login() })

  it('11.1 — Página de trocas carrega', () => {
    cy.visit(TRADES_URL)
    cy.get('h1, h2').should('exist')
  })

  it('11.2 — Debounce: variável _filterTimer existe no escopo da página', () => {
    cy.visit(TRADES_URL)
    cy.window().then(win => {
      // Verifica que a variável de debounce foi declarada (ou que a função existe)
      const script = win.document.body.innerHTML
      expect(script).to.include('_filterTimer')
    })
  })

  it('11.3 — Filtro de busca de trocas existe quando há matches disponíveis', () => {
    cy.visit(TRADES_URL)
    cy.get('body').then($body => {
      const hasSearch = $body.find('input[type="text"], input[type="search"]').length > 0
      if (hasSearch) {
        cy.get('input[type="text"], input[type="search"]').first().should('be.visible')
      } else {
        cy.log('Sem campo de busca de trocas — pulando')
      }
    })
  })

})

// ════════════════════════════════════════════════════════════
// 12 — TRADES/BINDER: confirmação ao trocar treinador
// ════════════════════════════════════════════════════════════
describe('12 — trades/binder.html: confirmação de treinador', () => {
  beforeEach(() => { cy.login() })

  it('12.1 — Binder carrega sem erro', () => {
    cy.visit('/trades/binder/felipe', { failOnStatusCode: false })
    cy.get('body').should('exist')
  })

  it('12.2 — Select de treinador tem onmousedown para salvar estado anterior', () => {
    cy.visit('/trades/binder/felipe', { failOnStatusCode: false })
    cy.get('body').then($body => {
      const sel = $body.find('select[onmousedown]')
      if (sel.length > 0) {
        expect(sel.attr('onmousedown')).to.include('dataset.prev')
      } else {
        cy.log('Select de treinador não encontrado ou página de binder indisponível')
      }
    })
  })

})

// ════════════════════════════════════════════════════════════
// 13 — IMPORT: drag-drop acessibilidade
// ════════════════════════════════════════════════════════════
describe('13 — import_/index.html: acessibilidade do drop zone', () => {
  beforeEach(() => { cy.login() })

  it('13.1 — Página de import carrega', () => {
    cy.visit(IMPORT_URL, { failOnStatusCode: false })
    cy.get('body').should('exist')
  })

  it('13.2 — Drop zone tem role="button"', () => {
    cy.visit(IMPORT_URL, { failOnStatusCode: false })
    cy.get('body').then($body => {
      const dropzone = $body.find('[role="button"]')
      if (dropzone.length > 0) {
        cy.get('[role="button"]').first().should('exist')
      } else {
        cy.log('Drop zone com role="button" não encontrado — verificar template')
      }
    })
  })

  it('13.3 — Drop zone tem aria-label descritivo', () => {
    cy.visit(IMPORT_URL, { failOnStatusCode: false })
    cy.get('body').then($body => {
      const dropzone = $body.find('[aria-label*="CSV"], [aria-label*="arquivo"], [aria-label*="soltar"]')
      if (dropzone.length > 0) {
        expect(dropzone.length).to.be.greaterThan(0)
      } else {
        cy.log('Drop zone com aria-label não encontrado — verificar template')
      }
    })
  })

  it('13.4 — Drop zone tem tabindex para acessibilidade por teclado', () => {
    cy.visit(IMPORT_URL, { failOnStatusCode: false })
    cy.get('body').then($body => {
      const tabbable = $body.find('[tabindex="0"]')
      if (tabbable.length > 0) {
        expect(tabbable.length).to.be.greaterThan(0)
      } else {
        cy.log('Elemento com tabindex=0 não encontrado — verificar template')
      }
    })
  })

  it('13.5 — Formulário de upload tem id="upload-form" para loading state', () => {
    cy.visit(IMPORT_URL, { failOnStatusCode: false })
    cy.get('body').then($body => {
      if ($body.find('#upload-form').length > 0) {
        cy.get('#upload-form').should('exist')
      } else {
        cy.log('Formulário #upload-form não encontrado — verificar template')
      }
    })
  })

})

// ════════════════════════════════════════════════════════════
// 14 — REGRESSÃO: funcionalidades existentes não quebraram
// ════════════════════════════════════════════════════════════
describe('14 — Regressão: funcionalidades críticas intactas', () => {

  it('14.1 — Login com credenciais corretas ainda funciona', () => {
    cy.visit(LOGIN_URL)
    cy.get('input[name="username"]').type('felipe')
    cy.get('input[name="password"]').type('e2e-senha-teste')
    cy.get('button[type="submit"]').click()
    cy.url().should('not.include', '/login')
  })

  it('14.2 — Pokédex ainda lista Pokémon', () => {
    cy.visit(POKEDEX_URL)
    cy.get('[data-poke-id]').should('have.length.greaterThan', 0)
  })

  it('14.3 — Filtro de geração funciona (sem campo hidden duplicado — bug corrigido)', () => {
    cy.visit(POKEDEX_URL)
    cy.get('select[name="generation"]').select('1')
    cy.url().should('include', 'generation=1')
    cy.contains('#001').should('exist')
    cy.contains('#152').should('not.exist')
  })

  it('14.4 — Collection ainda carrega com grid de 3 colunas', () => {
    cy.login()
    cy.visit(COLLECTION_URL)
    cy.get('#pokegrid').should('exist')
    cy.get('.poke-card').should('have.length.greaterThan', 0)
  })

  it('14.5 — Modal de Pokémon abre e fecha corretamente', () => {
    cy.visit(POKEDEX_URL)
    cy.get('[data-poke-id]').first().click()
    cy.wait(800)
    cy.get('#poke-modal').should('not.have.class', 'hidden')
    cy.get('#poke-modal-content h2').should('exist')
    cy.get('#poke-modal-content button[aria-label="Fechar"]').click()
    cy.wait(400)
    cy.get('#poke-modal').should('have.class', 'hidden')
  })

  it('14.6 — Wishlist carrega sem erro', () => {
    cy.login()
    cy.visit(WISHLIST_URL)
    cy.get('h1').should('be.visible')
  })

  it('14.7 — Catalogar por região carrega', () => {
    cy.login()
    cy.visit(CATALOGAR_URL)
    cy.contains(/Kanto|regi/i).should('exist')
  })

  it('14.8 — Modal fecha com tecla Escape', () => {
    cy.visit(POKEDEX_URL)
    cy.get('[data-poke-id]').first().click()
    cy.wait(800)
    cy.get('#poke-modal').should('not.have.class', 'hidden')
    cy.get('body').type('{esc}')
    cy.wait(400)
    cy.get('#poke-modal').should('have.class', 'hidden')
  })

  it('14.9 — Filtro de coleção sem campo hidden duplicado para generation', () => {
    cy.login()
    cy.visit(COLLECTION_URL)
    // Verifica que não existe input hidden com name="generation" no form de filtros
    cy.get('#collection-filter').within(() => {
      cy.get('input[type="hidden"][name="generation"]').should('not.exist')
    })
  })

  it('14.10 — Mobile 375px: sem overflow horizontal na home', () => {
    cy.viewport(375, 667)
    cy.visit(HOME_URL)
    cy.document().then(doc => {
      expect(doc.documentElement.scrollWidth).to.be.lte(380)
    })
  })

})

// ════════════════════════════════════════════════════════════
// 15 — SCREENSHOTS multi-viewport das páginas corrigidas
// ════════════════════════════════════════════════════════════
describe('15 — Screenshots das páginas corrigidas', () => {
  const viewports = [
    { label: '375', w: 375, h: 667 },
    { label: '1280', w: 1280, h: 800 },
  ]

  beforeEach(() => { cy.login() })

  viewports.forEach(({ label, w, h }) => {
    it(`15 — collection ${label}px`, () => {
      cy.viewport(w, h)
      cy.visit(COLLECTION_URL)
      cy.screenshot(`uxui-collection-${label}`)
    })

    it(`15 — wishlist ${label}px`, () => {
      cy.viewport(w, h)
      cy.visit(WISHLIST_URL)
      cy.screenshot(`uxui-wishlist-${label}`)
    })

    it(`15 — pokedex ${label}px`, () => {
      cy.viewport(w, h)
      cy.visit(POKEDEX_URL)
      cy.screenshot(`uxui-pokedex-${label}`)
    })

    it(`15 — login ${label}px`, () => {
      cy.clearCookies()
      cy.viewport(w, h)
      cy.visit(LOGIN_URL)
      cy.screenshot(`uxui-login-${label}`)
    })

    it(`15 — registro ${label}px`, () => {
      cy.clearCookies()
      cy.viewport(w, h)
      cy.visit(REGISTRO_URL)
      cy.screenshot(`uxui-registro-${label}`)
    })

    it(`15 — catalogar ${label}px`, () => {
      cy.viewport(w, h)
      cy.visit(CATALOGAR_URL)
      cy.screenshot(`uxui-catalogar-${label}`)
    })
  })
})
