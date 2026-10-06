// gualco.it — player leggero, filtri per tema, "mostra altri". Nessuna dipendenza.
(() => {
  // Player YouTube: l'iframe (e i cookie) arrivano solo al click
  document.querySelectorAll('.lite').forEach((b) => b.addEventListener('click', () => {
    const f = document.createElement('iframe');
    f.src = `https://www.youtube-nocookie.com/embed/${b.dataset.id}?autoplay=1&rel=0`;
    f.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen';
    f.allowFullscreen = true;
    f.title = b.getAttribute('aria-label') || 'Video';
    b.replaceChildren(f);
  }, { once: true }));

  // Barra laterale: evidenzia la sezione in vista
  const rail = [...document.querySelectorAll('.rail a')];
  if (rail.length) {
    const sezioni = rail.map((a) => document.getElementById(a.dataset.s)).filter(Boolean);
    const attiva = () => {
      const y = innerHeight * 0.35;
      let cur = sezioni[0];
      for (const s of sezioni) if (s.getBoundingClientRect().top <= y) cur = s;
      rail.forEach((a) => a.classList.toggle('on', a.dataset.s === cur.id));
    };
    addEventListener('scroll', attiva, { passive: true });
    addEventListener('resize', attiva);
    attiva();
  }

  // Esplora per tema
  const sez = document.getElementById('esplora');
  if (!sez) return;
  const voci = [...sez.querySelectorAll('.griglia > .card')];
  const altri = sez.querySelector('.altri button');
  const vuoto = sez.querySelector('.vuoto');
  const PASSO = 12;
  let tema = 'tutti', fonte = 'tutte', mostra = PASSO;

  const disegna = () => {
    const ok = voci.filter((v) =>
      (tema === 'tutti' || v.dataset.f.split(' ').includes(tema)) &&
      (fonte === 'tutte' || v.dataset.fonte === fonte));
    voci.forEach((v) => { v.hidden = true; });
    ok.slice(0, mostra).forEach((v) => { v.hidden = false; });
    altri.parentElement.hidden = ok.length <= mostra;
    altri.querySelector('span').textContent = ok.length - mostra;
    vuoto.hidden = ok.length > 0;
  };

  const premi = (gruppo, btn) => {
    sez.querySelectorAll(gruppo).forEach((c) => c.setAttribute('aria-pressed', String(c === btn)));
  };
  sez.querySelectorAll('.chips .chip').forEach((c) => c.addEventListener('click', () => {
    tema = c.dataset.f; mostra = PASSO; premi('.chips .chip', c); disegna();
    history.replaceState(null, '', tema === 'tutti' ? location.pathname : `#tema-${tema}`);
  }));
  sez.querySelectorAll('.fonti .chip').forEach((c) => c.addEventListener('click', () => {
    fonte = c.dataset.fonte; mostra = PASSO; premi('.fonti .chip', c); disegna();
  }));
  altri.addEventListener('click', () => { mostra += PASSO; disegna(); });

  // link diretto a un tema: gualco.it/#tema-casa
  const h = location.hash.match(/^#tema-(.+)$/);
  const pre = h && sez.querySelector(`.chips .chip[data-f="${CSS.escape(h[1])}"]`);
  if (pre) { pre.click(); sez.scrollIntoView(); } else disegna();
})();
