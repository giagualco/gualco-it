# gualco.it — sito "Gianluca Gualco Energia"

Hub unico di canale YouTube, articoli Substack, post LinkedIn e tool gratuiti, con il design system GG (mondo "notte"). Il sito è statico e viene rigenerato ogni notte da GitHub Actions, anche a computer spenti.

## Come funziona

```
config/   sito.json (link, testi) · temi.json (playlist = temi, rubriche, parole chiave) · tools.json
fetch/    youtube.py · substack.py → data/*.json (cache cumulativa: se una fonte è giù resta l'ultima lettura)
data/     youtube.json · substack.json · linkedin.json (quest'ultimo lo aggiorna la pubblicazione del giovedì)
src/      sito.css · sito.js · og.html (sorgente di docs/og.png)
build.py  → docs/ (index.html, og.png, favicon, sitemap, robots, CNAME)
strumenti/aggiorna_linkedin.py   passo "aggiorna-sito-linkedin" del giovedì
.github/workflows/aggiorna.yml   ogni notte alle 04:00 (ora legale) + a mano + a ogni push su dati/design
```

Solo Python 3 standard, senza dipendenze da installare.

## Comandi in locale

```bash
python3 fetch/youtube.py && python3 fetch/substack.py   # legge le fonti
python3 build.py                                        # genera docs/
python3 -m http.server 4173 --directory docs            # anteprima su http://localhost:4173
```

## Fonti

- **YouTube.** Con credenziali in `.env` o nei GitHub Secrets (`YOUTUBE_API_KEY`, oppure `YT_CLIENT_ID` + `YT_CLIENT_SECRET` + `YT_REFRESH_TOKEN`) legge tutto il canale con le visualizzazioni. Senza credenziali usa il modo pubblico: feed RSS (ultimi 15 video, con views), pagine delle playlist e pagina canale. L'archivio si accumula giorno dopo giorno.
- **Substack.** Archivio pubblico `gualco.substack.com/api/v1/archive` (`sort=new` / `sort=top`). Dai server di GitHub Cloudflare risponde 403 a tutto, quindi di notte si scende a cascata: API → feed `/feed` → `api.rss2json.com` (servizio pubblico, nessuna chiave). La classifica «più apprezzati» si aggiorna solo quando l'API risponde, cioè lanciando `python3 fetch/substack.py` dal Mac e facendo push.
- **LinkedIn.** `data/linkedin.json`. Il giovedì, dopo il rilancio personale:
  ```bash
  python3 strumenti/aggiorna_linkedin.py post --id W41-2026 --data 2026-10-08 \
    --titolo "…" --estratto "…" --url <post personale> --url-3i <post 3i group> --push
  python3 strumenti/aggiorna_linkedin.py stats --file stats.json --push
  ```
- **Temi.** Sono le playlist tematiche del canale. I video vengono assegnati per appartenenza alla playlist; articoli, post e tool per parole chiave (`config/temi.json`). Per correggere un caso singolo: `"override": {"<id>": ["casa"]}`.

## Pubblicazione

Online dal 06/10/2026 su https://giagualco.github.io/gualco-it/ (Pages da GitHub Actions). Push dal Mac con `gh` già autenticato. Restano da fare i passi 4–5 (dominio).

### Passi

1. Repo `giagualco/gualco-it`, push, Settings → Pages → Source: **GitHub Actions**.
2. Nessun Secret: per scelta il sito usa solo dati pubblici (deciso il 06/10/2026). Il supporto alle credenziali resta nel codice ma è spento.
3. Actions → "Aggiorna sito" → Run workflow, poi verifica su `giagualco.github.io/gualco-it`.
4. DNS Aruba (solo record web, **mai MX/PEC**): togliere il redirect attuale; record A `@` → 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153; CNAME `www` → `giagualco.github.io`.
5. `config/sito.json` → `"cname_attivo": true`, push, poi Settings → Pages → Custom domain `gualco.it` + Enforce HTTPS.
