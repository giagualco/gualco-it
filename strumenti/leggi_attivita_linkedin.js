// Estrae i post dalla pagina Attività del profilo LinkedIn (sola lettura).
// Si incolla così com'è in javascript_tool sulla pagina
// https://www.linkedin.com/in/gianluca-gualco-033474100/recent-activity/all/
// Restituisce {login, posts: [{id, url, data, testo, reazioni, impression}]}.
//
// Dall'ottobre 2026 LinkedIn non espone più data-urn né le classi
// .update-components-text / .social-details-social-counts__*: l'unico aggancio
// stabile è il link «Vedi analisi» (/analytics/post-summary/urn:li:activity:<id>).
// Il contenitore del post è l'antenato più alto che contiene un solo link di analisi.
// Le reazioni sono il primo dei quattro contatori (numero o vuoto) che precedono
// la riga «N impressioni».
await new Promise(r => setTimeout(r, 6000));
window.scrollTo(0, document.body.scrollHeight);
await new Promise(r => setTimeout(r, 3000));
const login = /\/(login|authwall|checkpoint|uas)/.test(location.pathname) || !!document.querySelector('#session_key');
const sel = 'a[href*="/analytics/post-summary/urn:li:activity:"]';
const visti = new Set();
const posts = [];
for (const a of document.querySelectorAll(sel)) {
  const id = a.href.match(/activity:(\d+)/)[1];
  if (visti.has(id)) continue;
  visti.add(id);
  let c = a;
  while (c.parentElement && c.parentElement.querySelectorAll('a[href*="/analytics/post-summary/"]').length === 1) c = c.parentElement;
  const grezze = c.innerText.split('\n');
  const righe = grezze.map(s => s.replace(/​/g, '').trim());
  const imp = righe.findIndex(s => /^[\d.]+ impression/.test(s));
  const contatori = [];
  for (let i = imp - 1; i >= 0 && contatori.length < 4; i--) {
    if (/^[\d.]*$/.test(righe[i]) && grezze[i] !== '') contatori.unshift(righe[i]);
    else if (righe[i] !== '') break;
  }
  const num = s => parseInt((s || '').replace(/\./g, ''), 10) || 0;
  const m = c.innerText.match(/\n(\d+ ?(h|min|g|sett|m)|\d+ \w{3}|Ieri)\n\n([\s\S]*?)(\n… altro|$)/);
  posts.push({
    id,
    url: `https://www.linkedin.com/feed/update/urn:li:activity:${id}/`,
    data: m ? m[1] : null,
    testo: (m ? m[3] : c.innerText).slice(0, 2000),
    reazioni: imp >= 0 ? num(contatori[0]) : null,
    impression: imp >= 0 ? num(righe[imp]) : null,
  });
}
({ login, posts })
