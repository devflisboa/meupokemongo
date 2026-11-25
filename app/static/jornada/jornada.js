/* Jornada (#27) — helpers compartilhados pelas páginas. */
window.JN = (() => {
  const MAPA_ESC = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'};
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => MAPA_ESC[c]);

  function avatar(r, px = 40) {
    const inner = r.avatar ? `<img src="${esc(r.avatar)}" alt="" loading="lazy">` : esc(r.inicial || '?');
    return `<span class="jn-av" style="width:${px}px;height:${px}px;font-size:${Math.round(px * .42)}px" title="${esc(r.username)}">${inner}${r.online ? '<span class="jn-on"></span>' : ''}</span>`;
  }

  let toastT;
  function toast(html, ms = 3500) {
    let box = document.getElementById('jn-toast');
    if (!box) { box = document.createElement('div'); box.id = 'jn-toast'; document.body.appendChild(box); }
    box.innerHTML = `<div>${html}</div>`;
    clearTimeout(toastT);
    toastT = setTimeout(() => { box.innerHTML = ''; }, ms);
  }

  async function post(url, body) {
    const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})});
    const j = await r.json().catch(() => ({ok: false, erro: r.status === 429 ? 'Calma! Muitas ações seguidas.' : 'Erro inesperado.'}));
    if (!j.ok) toast('⚠️ ' + esc(j.erro || 'Não foi possível.'));
    return j;
  }

  function sheet(html) {
    fecharSheet();
    const bg = document.createElement('div');
    bg.className = 'jn-sheet-bg'; bg.id = 'jn-sheet';
    bg.innerHTML = `<div class="jn-sheet" role="dialog" aria-modal="true">
      <div class="flex justify-end"><button class="text-2xl leading-none text-gray-400 px-2" aria-label="Fechar" data-fechar>×</button></div>${html}</div>`;
    bg.addEventListener('click', e => { if (e.target === bg || e.target.hasAttribute('data-fechar')) fecharSheet(); });
    document.body.appendChild(bg);
    return bg.querySelector('.jn-sheet');
  }
  function fecharSheet() { document.getElementById('jn-sheet')?.remove(); }

  function criatura(c, extra = '') {
    return `<span class="inline-flex items-center justify-center rounded-full flex-shrink-0" style="width:40px;height:40px;background:${esc(c.cor)};font-size:20px">${esc(c.emoji)}</span>
      <span class="min-w-0 text-left"><b class="block truncate">${esc(c.nome)}</b><span class="text-xs text-gray-500">${esc(c.tipo)} · Atk ${c.ataque}${extra}</span></span>`;
  }

  /* Polling: 5 s com a aba visível, 30 s em segundo plano. */
  function poll(fn, visivel = 5000, oculto = 30000) {
    let t;
    const tick = async () => {
      try { await fn(); } catch (e) { /* rede instável: tenta no próximo ciclo */ }
      t = setTimeout(tick, document.hidden ? oculto : visivel);
    };
    document.addEventListener('visibilitychange', () => { if (!document.hidden) { clearTimeout(t); tick(); } });
    t = setTimeout(tick, visivel);
  }

  return {esc, avatar, toast, post, sheet, fecharSheet, criatura, poll};
})();
