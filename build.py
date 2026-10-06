"""Genera docs/ (sito statico) da config/ + data/. Solo libreria standard.

    python3 build.py
"""
import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent / "fetch"))
from comune import ROOT, etichetta, leggi  # noqa: E402

SITO = leggi("config/sito.json")
CFG = leggi("config/temi.json")
TOOLS = leggi("config/tools.json", [])
YT = leggi("data/youtube.json", {"video": {}, "playlist": {}, "canale": {}})
SS = leggi("data/substack.json", {"post": [], "top": []})
LI = leggi("data/linkedin.json", {"post": []})
OUT = ROOT / "docs"
ROMA = ZoneInfo("Europe/Rome")
MESI = "gen feb mar apr mag giu lug ago set ott nov dic".split()
MESI_LUNGHI = ("gennaio febbraio marzo aprile maggio giugno luglio agosto "
               "settembre ottobre novembre dicembre").split()

e = lambda s: escape(str(s or ""), quote=True)  # noqa: E731
NOMI_TEMA = {t["slug"]: t["nome"] for t in CFG["temi"]}
NOMI_RUB = {r["slug"]: r["nome"] for r in CFG["rubriche"]}


# ---------------- formati ----------------
def data_it(iso, lunga=False):
    if not iso:
        return ""
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")) if "T" in iso else datetime.fromisoformat(iso)
    if d.tzinfo:
        d = d.astimezone(ROMA)
    return f"{d.day} {(MESI_LUNGHI if lunga else MESI)[d.month - 1]} {d.year}"


def numero(n):
    return f"{n:,}".replace(",", ".") if n is not None else ""


def compatto(n):
    if n is None:
        return ""
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}".replace(".", ",").replace(",0", "") + " mln"
    if n >= 10_000:
        return f"{round(n / 1000)} mila"
    if n >= 1000:
        return f"{n / 1000:.1f}".replace(".", ",").replace(",0", "") + " mila"
    return str(n)


def durata(sec):
    if not sec:
        return ""
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def primo_paragrafo(t, n=240):
    t = (t or "").strip().split("\n\n")[0].replace("\n", " ")
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


# ---------------- icone e marchio ----------------
def marchio(c="#FFE14D"):
    return (f'<svg viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="{c}" stroke-linecap="round">'
            f'<path d="M21 44.5A32 32 0 0 1 79 44.5" stroke-width="10" opacity=".3"/>'
            f'<path d="M21 44.5A32 32 0 0 1 44.4 26.5" stroke-width="10"/><path d="M50 58 63 35.5" stroke-width="11"/></g>'
            f'<circle cx="50" cy="58" r="7" fill="{c}"/><path d="M50 72v14" stroke="{c}" stroke-width="10" stroke-linecap="round"/></svg>')


ICONE = {
    "youtube": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 .5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8ZM9.7 15.1V8.9l5.8 3.1-5.8 3.1Z"/></svg>',
    "substack": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 3h18v2.5H3zm0 4.7h18v2.5H3zM3 12.4h18V22l-9-5-9 5z"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.5h4v11H3zm7 0h3.8v1.6h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6v5.4h-4v-4.8c0-1.2 0-2.7-1.6-2.7s-1.9 1.3-1.9 2.6v4.9h-4z"/></svg>',
    "tool": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M4 20h16M7 16V9m5 7V5m5 11v-4"/></svg>',
    "occhio": '<svg viewBox="0 0 24 24" aria-label="visualizzazioni"><path fill="none" stroke="currentColor" stroke-width="2.2" d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>',
    "freccia": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6-6 6 6-6 6"/></svg>',
}
NOME_FONTE = {"youtube": "YouTube", "substack": "Substack", "linkedin": "LinkedIn", "tool": "Tool"}


def fonte(f, extra=""):
    return f'<span class="fonte">{ICONE[f]}{NOME_FONTE[f]}{extra}</span>'


def rub_badge(slug):
    return f'<span class="rub rub-{slug}">{e(NOMI_RUB[slug])}</span>' if slug else ""


# ---------------- normalizzazione contenuti ----------------
def membri(pl):
    return set(YT["playlist"].get(pl, []))


def video():
    temi_pl = {t["slug"]: membri(t["playlist"]) for t in CFG["temi"] if t.get("playlist")}
    rub_pl = {r["slug"]: membri(r["playlist"]) for r in CFG["rubriche"] if r.get("playlist")}
    out = []
    for v in YT["video"].values():
        if not v.get("titolo"):
            continue
        temi = [s for s, ids in temi_pl.items() if v["id"] in ids]
        rub = next((s for s, ids in rub_pl.items() if v["id"] in ids), None)
        if not temi or not rub:
            _, r2 = etichetta(f"{v['titolo']} {v.get('desc', '')[:300]}", CFG)
            temi = temi or etichetta(v["titolo"], CFG)[0]
            rub = rub or r2
        temi = CFG["override"].get(v["id"], temi)
        short = bool(v.get("short"))
        out.append({
            "fonte": "youtube", "id": v["id"], "titolo": v["titolo"], "desc": v.get("desc", ""),
            "url": f"https://www.youtube.com/{'shorts/' if short else 'watch?v='}{v['id']}",
            "data": v.get("data"), "views": v.get("views"), "secondi": v.get("secondi"),
            "short": short, "temi": temi, "rubrica": rub,
            "img": f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg",
        })
    return out


def articoli():
    out = []
    for p in SS["post"]:
        temi, rub = etichetta(f"{p['titolo']} {p['sottotitolo']}", CFG)
        tag = " ".join(p.get("tag", [])).lower()
        rub = next((r["slug"] for r in CFG["rubriche"] if r["nome"].lower() in tag), rub)
        out.append({"fonte": "substack", "id": p["id"], "titolo": p["titolo"], "desc": p["sottotitolo"],
                    "url": p["url"], "data": p["data"], "img": p.get("cover"), "temi": CFG["override"].get(str(p["id"]), temi),
                    "rubrica": rub, "reazioni": p.get("reazioni", 0) + p.get("commenti", 0) + p.get("restack", 0)})
    return out


def post_li():
    out = []
    for p in LI["post"]:
        temi, _ = etichetta(f"{p['titolo']} {p.get('estratto', '')}", CFG)
        out.append({"fonte": "linkedin", "id": p["id"], "titolo": p["titolo"], "desc": p.get("estratto", ""),
                    "url": p.get("url") or p.get("url_3i"), "su_3i": not p.get("url"), "data": p.get("data"),
                    "temi": CFG["override"].get(p["id"], temi), "rubrica": None,
                    "reazioni": p.get("reazioni"), "impression": p.get("impression")})
    return out


def strumenti():
    return [{"fonte": "tool", "id": t["id"], "titolo": t["nome"], "desc": t["desc"], "url": t["url"],
             "data": None, "temi": t.get("temi", []), "rubrica": None} for t in TOOLS]


per_data = lambda x: x.get("data") or ""  # noqa: E731

VIDEO = video()
LONG = sorted([v for v in VIDEO if not v["short"]], key=per_data, reverse=True)
SHORT = [v for v in VIDEO if v["short"]]
# short: prima quelli datati (RSS/API), poi l'ordine delle playlist (dal più recente)
ordine_pl = {vid: i for r in CFG["rubriche"] for i, vid in enumerate(YT["playlist"].get(r["playlist"], []))}
SHORT.sort(key=lambda v: (v["data"] or "", -ordine_pl.get(v["id"], 999)), reverse=True)
ART = sorted(articoli(), key=per_data, reverse=True)
LIN = sorted(post_li(), key=per_data, reverse=True)
TOOL = strumenti()


# ---------------- componenti ----------------
def card(x, lazy=True, cls=""):
    lz = ' loading="lazy" decoding="async"' if lazy else ""
    f = x["fonte"]
    temi_attr = " ".join(x["temi"] + ([x["rubrica"]] if x.get("rubrica") else []))
    titolo = e(x["titolo"])
    if f == "youtube":
        img = (f'<div class="img"><img src="{e(x["img"])}" alt=""{lz}>{rub_badge(x["rubrica"])}'
               f'{f"<span class=durata>{durata(x["secondi"])}</span>" if x.get("secondi") else ""}</div>')
        meta = " · ".join(filter(None, [data_it(x["data"]), f'{compatto(x["views"])} visualizzazioni' if x.get("views") else ""]))
        if "mini" in cls:
            meta = data_it(x["data"])
            if x.get("views"):
                img = img.replace("</div>", f'<span class="vis">{ICONE["occhio"]}{compatto(x["views"])}</span></div>', 1)
        testo = ""
        piede = f'{fonte("youtube", " · Short" if x["short"] else "")}'
    elif f == "substack":
        img = (f'<div class="img"><img src="{e(x["img"])}" alt=""{lz}>{rub_badge(x["rubrica"])}</div>' if x.get("img")
               else "")
        meta = " · ".join(filter(None, [data_it(x["data"]), NOMI_RUB.get(x.get("rubrica"), "") if not x.get("img") else ""]))
        testo = f'<p>{e(x["desc"])}</p>' if x.get("desc") else ""
        piede = fonte("substack")
    elif f == "linkedin":
        img = ""
        meta = " · ".join(filter(None, [data_it(x["data"]),
                                        f'{numero(x["reazioni"])} reazioni' if x.get("reazioni") else ""]))
        testo = f'<p>{e(x["desc"])}</p>'
        piede = fonte("linkedin", " · 3i group" if x.get("su_3i") else "")
    else:
        return card_tool(x, temi_attr)
    return (f'<article class="card {cls}" data-fonte="{f}" data-f="{e(temi_attr)}">{img}<div class="corpo">'
            f'<span class="meta">{meta}</span><h3><a class="tutta" href="{e(x["url"])}" target="_blank" rel="noopener">{titolo}</a></h3>'
            f'{testo}<div class="piede">{piede}</div></div></article>')


def card_tool(x, temi_attr=None):
    temi_attr = temi_attr if temi_attr is not None else " ".join(x["temi"])
    return (f'<article class="card tool" data-fonte="tool" data-f="{e(temi_attr)}"><div class="img"><span class="badge">TOOL GRATIS</span></div>'
            f'<div class="corpo"><h3><a class="tutta" href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["titolo"])}</a></h3>'
            f'<p>{e(x["desc"])}</p><div class="piede">{fonte("tool")}<span class="vai">Apri il tool →</span></div></div></article>')


def btn_yt(testo="Iscriviti al canale"):
    return f'<a class="btn btn-yt" href="{e(SITO["youtube"]["iscriviti"])}" target="_blank" rel="noopener">{ICONE["youtube"]}{testo}</a>'


def btn_li(testo="Seguimi su LinkedIn"):
    return f'<a class="btn btn-li" href="{e(SITO["linkedin"]["profilo"])}" target="_blank" rel="noopener">{ICONE["linkedin"]}{testo}</a>'


# ---------------- sezioni ----------------
def sez_hero():
    can = YT.get("canale", {})
    iscritti = compatto(can["iscritti"]) if can.get("iscritti") else (can.get("iscritti_testo") or "").replace(" iscritti", "")
    ultimo_art = ART[0]["titolo"] if ART else ""
    tiles = [
        ("linkedin", "linkedin", "LinkedIn", "Energia e impresa", "Un post ogni giovedì"),
        ("video", "youtube", "YouTube", "Un video ogni martedì",
         f"{iscritti} iscritti · {numero(can.get('video') or len(VIDEO))} video" if iscritti else f"{numero(len(VIDEO))} video"),
        ("articoli", "substack", "Substack", "Gli articoli e la newsletter", f"{len(ART)} articoli · ultimo il {data_it(ART[0]['data'])}" if ART else ""),
        ("tool", "tool", "Tool gratis", "Fai i conti da solo", f"{len(TOOL)} calcolatori online"),
    ]
    t = "".join(
        f'<a class="tile tile-{f}" href="#{a}"><span class="ic">{ICONE[f]}</span>'
        f'<span class="tt"><b>{n}</b><span>{sub}</span><small>{e(info)}</small></span>'
        f'<span class="giu" aria-hidden="true">↓</span></a>' for a, f, n, sub, info in tiles)
    return f'''<header class="hero" id="top"><div class="wrap">
<div class="hero-top">
  <div class="hero-txt">
    <p class="kick">Energy manager · Divulgazione</p>
    <h1>Gianluca Gualco</h1>
    <p class="intro">Spiego l'energia in quattro posti diversi: i post su LinkedIn, i video su YouTube, gli articoli su Substack e i calcolatori gratuiti. Qui li trovi tutti insieme, aggiornati ogni giorno.</p>
    <p class="riga">Scegli da dove partire</p>
  </div>
  <img class="ritratto" src="assets/ritratto.png" width="720" height="756" alt="Gianluca Gualco" fetchpriority="high">
</div>
<nav class="tiles" aria-label="Vai ai contenuti">{t}</nav>
</div></header>'''


def sez_video():
    if not LONG:
        return ""
    u = LONG[0]
    top = sorted([v for v in LONG if v.get("views")], key=lambda v: -v["views"])[:6]
    gia = {v["id"] for v in top} | {u["id"]}
    recenti = [v for v in LONG if v["id"] not in gia][:6]
    meta = " · ".join(filter(None, [data_it(u["data"], True), f'{numero(u["views"])} visualizzazioni' if u.get("views") else ""]))
    return f'''<section class="sez sez-alt" id="video"><div class="wrap">
<div class="testa"><div><p class="kick">Il video del martedì</p><h2>L'ultimo video</h2></div>
<a class="link" href="{e(SITO["youtube"]["url"])}/videos" target="_blank" rel="noopener">Tutti i video sul canale →</a></div>
<div class="ultimo">
  <button class="lite" data-id="{e(u["id"])}" aria-label="Guarda: {e(u["titolo"])}"><img src="https://i.ytimg.com/vi/{e(u["id"])}/sddefault.jpg" alt="" fetchpriority="high"><span class="play"></span></button>
  <div><span class="meta">{meta}</span><h3 style="margin-top:8px">{e(u["titolo"])}</h3>
  <p>{e(primo_paragrafo(u["desc"]))}</p>
  <div class="cta">{btn_yt("Iscriviti: un video ogni martedì")}</div></div>
</div>
<p class="sotto" style="margin-top:44px">I più visti</p>
<div class="riga6">{"".join(card(v, cls="mini") for v in top)}</div>
<p class="sotto" style="margin-top:34px">Usciti di recente</p>
<div class="riga6">{"".join(card(v, cls="mini") for v in recenti)}</div>
</div></section>'''


def sez_short():
    if not SHORT:
        return ""
    return f'''<section class="sez sez-alt" id="short"><div class="wrap">
<div class="testa"><div><p class="kick">Gufo Reale · Controcorrente · Short</p><h2>Un minuto, un numero verificato</h2>
<p class="lead">Il <b style="color:var(--gufo-ink)">Gufo Reale</b> controlla le dichiarazioni pubbliche con fonte e data. <b style="color:var(--cc-ink)">Controcorrente</b> smonta i miti della settimana.</p></div>
<a class="link" href="{e(SITO["youtube"]["url"])}/shorts" target="_blank" rel="noopener">Tutti gli short →</a></div>
<div class="riga-short">{"".join(card(v) for v in SHORT[:14])}</div>
</div></section>'''


def sez_articoli():
    if not ART:
        return ""
    g, resto = ART[0], ART[1:5]
    per_id = {a["id"]: a for a in ART}
    top = [per_id[i] for i in SS.get("top", []) if i in per_id and per_id[i] not in ART[:5]][:4]
    riga = lambda a: (f'<a href="{e(a["url"])}" target="_blank" rel="noopener"><span class="meta">{data_it(a["data"])}'  # noqa: E731
                      f'{" · " + e(NOMI_RUB[a["rubrica"]]) if a.get("rubrica") else ""}</span><h3>{e(a["titolo"])}</h3></a>')
    return f'''<section class="sez" id="articoli"><div class="wrap">
<div class="testa"><div><p class="kick">Substack · newsletter</p><h2>Gli articoli</h2>
<p class="lead">Quando un tema chiede più di un video: fonti, conti e decreti per esteso.</p></div>
<a class="link" href="{e(SITO["substack"]["url"])}/archive" target="_blank" rel="noopener">Archivio completo →</a></div>
<div class="art">{card(g, cls="grande")}<div class="elenco">{"".join(riga(a) for a in resto)}</div></div>
{f'<p class="sotto">I più apprezzati</p><div class="griglia">{"".join(card(a) for a in top)}</div>' if top else ""}
<div class="fascia"><div><b>Ricevi gli articoli per email</b><span>Gratis, nessuno spam. Ti cancelli con un clic.</span></div>
<a class="btn btn-sec" href="{e(SITO["substack"]["iscriviti"])}" target="_blank" rel="noopener">{ICONE["substack"]}Iscriviti alla newsletter</a></div>
</div></section>'''


def sez_linkedin():
    if not LIN:
        return ""
    con_stats = [p for p in LIN if p.get("reazioni")]
    top = sorted(con_stats, key=lambda p: -p["reazioni"])[:3]
    return f'''<section class="sez" id="linkedin"><div class="wrap">
<div class="testa"><div><p class="kick">LinkedIn · ogni giovedì</p><h2>Per chi decide in azienda</h2>
<p class="lead">Diagnosi, obblighi EED, incentivi e bandi: cosa cambia per le imprese, scritto da chi lo fa sul campo.</p></div>
<a class="link" href="{e(SITO["linkedin"]["profilo"])}/recent-activity/all/" target="_blank" rel="noopener">Tutti i post →</a></div>
<div class="griglia">{"".join(card(p) for p in LIN[:3])}</div>
{f'<p class="sotto">I più letti</p><div class="griglia">{"".join(card(p) for p in top)}</div>' if top and [p['id'] for p in top] != [p['id'] for p in LIN[:3]] else ""}
<div class="fascia"><div><b>Seguimi su LinkedIn</b><span>Un post a settimana su energia e impresa, senza slogan.</span></div>{btn_li("Segui")}</div>
</div></section>'''


def sez_tool():
    if not TOOL:
        return ""
    return f'''<section class="sez" id="tool"><div class="wrap">
<div class="testa"><div><p class="kick">Gratis, senza registrazione</p><h2>I tool per fare i conti</h2>
<p class="lead">Prima di firmare un preventivo o chiedere un incentivo, fai il conto da solo.</p></div></div>
<div class="griglia">{"".join(card_tool(t) for t in TOOL)}</div>
</div></section>'''


def sez_esplora():
    tutto = sorted(LONG + SHORT + ART + LIN, key=per_data, reverse=True) + TOOL
    conta = lambda s: sum(1 for x in tutto if s in x["temi"] or x.get("rubrica") == s)  # noqa: E731
    chip = lambda s, n, cls="": (f'<button class="chip {cls}" data-f="{s}" aria-pressed="false">{e(n)} <small>{conta(s)}</small></button>'  # noqa: E731
                                 if conta(s) else "")
    temi = "".join(chip(t["slug"], t["nome"]) for t in CFG["temi"])
    rub = "".join(chip(r["slug"], r["nome"], "chip-rub") for r in CFG["rubriche"])
    fonti = "".join(f'<button class="chip" data-fonte="{f}" aria-pressed="false">{n}</button>'
                    for f, n in [("youtube", "Video"), ("substack", "Articoli"), ("linkedin", "Post"), ("tool", "Tool")])
    return f'''<section class="sez" id="esplora"><div class="wrap">
<div class="testa"><div><p class="kick">Tutto quello che ho pubblicato</p><h2>Esplora per tema</h2>
<p class="lead">Gli stessi temi delle playlist del canale. Ogni contenuto si apre dove è stato pubblicato.</p></div></div>
<div class="chips" role="group" aria-label="Filtra per tema"><button class="chip" data-f="tutti" aria-pressed="true">Tutti <small>{len(tutto)}</small></button>{temi}<span class="sep" aria-hidden="true"></span>{rub}</div>
<div class="fonti" role="group" aria-label="Filtra per fonte"><button class="chip" data-fonte="tutte" aria-pressed="true">Tutte le fonti</button>{fonti}</div>
<div class="griglia">{"".join(card(x) for x in tutto)}</div>
<p class="vuoto" hidden>Nessun contenuto per questa combinazione.</p>
<div class="altri"><button class="btn btn-sec" type="button">Mostra altri (<span></span>)</button></div>
</div></section>'''


def sez_chi():
    az = SITO["azienda"]
    nome_az = f'<a class="link" href="{e(az["url"])}" target="_blank" rel="noopener">{e(az["nome"])}</a>' if az.get("url") else e(az["nome"])
    bio = e(SITO["bio"]).replace(e(az["nome"]), nome_az).replace("3i Efficientamento Energetico", nome_az, 1) if az.get("url") else e(SITO["bio"])
    return f'''<section class="sez sez-alt" id="chi"><div class="wrap chi">
<span class="gufo">{marchio()}</span>
<div><p class="kick">Chi sono</p><p>{bio}</p>
<div class="social">{btn_yt()}{btn_li()}<a class="btn btn-sec" href="{e(SITO["substack"]["url"])}" target="_blank" rel="noopener">{ICONE["substack"]}Substack</a></div></div>
</div></section>'''


def pagina():
    ora = datetime.now(ROMA)
    agg = f"{ora.day} {MESI_LUNGHI[ora.month - 1]} {ora.year}, {ora:%H:%M}"
    css = (ROOT / "src/sito.css").read_text()
    js = (ROOT / "src/sito.js").read_text()
    persona = {
        "@context": "https://schema.org", "@type": "Person", "name": "Gianluca Gualco",
        "jobTitle": "Energy manager", "url": SITO["url"], "image": f'{SITO["url"]}/assets/ritratto.png',
        "worksFor": {"@type": "Organization", "name": SITO["azienda"]["nome"]},
        "sameAs": [SITO["youtube"]["url"], SITO["linkedin"]["profilo"], SITO["substack"]["url"]],
    }
    return f'''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(SITO["titolo_pagina"])}</title>
<meta name="description" content="{e(SITO["descrizione"])}">
<link rel="canonical" href="{e(SITO["url"])}/">
<meta name="theme-color" content="#080A0F">
<meta property="og:type" content="website">
<meta property="og:locale" content="it_IT">
<meta property="og:url" content="{e(SITO["url"])}/">
<meta property="og:title" content="{e(SITO["titolo_pagina"])}">
<meta property="og:description" content="{e(SITO["descrizione"])}">
<meta property="og:image" content="{e(SITO["url"])}/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preload" href="fonts/space-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preconnect" href="https://i.ytimg.com">
<style>{css}</style>
<script type="application/ld+json">{json.dumps(persona, ensure_ascii=False)}</script>
</head>
<body>
<a class="sr" href="#linkedin">Vai ai contenuti</a>
<nav class="nav" aria-label="Principale"><div class="wrap">
<a class="firma" href="#"><span class="mk">{marchio()}</span><span class="t">{e(SITO["firma"])}</span></a>
<ul><li><a href="#linkedin">LinkedIn</a></li><li><a href="#video">YouTube</a></li><li><a href="#articoli">Substack</a></li><li><a href="#tool">Tool</a></li><li><a href="#esplora">Temi</a></li></ul>
<a class="btn btn-yt" href="{e(SITO["youtube"]["iscriviti"])}" target="_blank" rel="noopener">{ICONE["youtube"]}Iscriviti</a>
</div></nav>
<nav class="rail" aria-label="Sezioni della pagina"><ol>
<li><a href="#" data-s="top"><i></i><span>Inizio</span></a></li>
<li><a href="#linkedin" data-s="linkedin"><i></i><span>LinkedIn</span></a></li>
<li><a href="#video" data-s="video"><i></i><span>YouTube</span></a></li>
<li><a href="#short" data-s="short"><i></i><span>Short</span></a></li>
<li><a href="#articoli" data-s="articoli"><i></i><span>Substack</span></a></li>
<li><a href="#tool" data-s="tool"><i></i><span>Tool</span></a></li>
<li><a href="#esplora" data-s="esplora"><i></i><span>Temi</span></a></li>
<li><a href="#chi" data-s="chi"><i></i><span>Chi sono</span></a></li>
</ol></nav>
{sez_hero()}
<main>
{sez_linkedin()}
{sez_video()}
{sez_short()}
{sez_articoli()}
{sez_tool()}
{sez_esplora()}
{sez_chi()}
</main>
<footer><div class="wrap">
<span class="firma"><span class="mk">{marchio()}</span>{e(SITO["firma"])}</span>
<span>Aggiornato il {agg} · <a href="{e(SITO["youtube"]["url"])}" target="_blank" rel="noopener">YouTube</a> · <a href="{e(SITO["linkedin"]["profilo"])}" target="_blank" rel="noopener">LinkedIn</a> · <a href="{e(SITO["substack"]["url"])}" target="_blank" rel="noopener">Substack</a></span>
</div></footer>
<script>{js}</script>
</body>
</html>
'''


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    html = pagina()
    (OUT / "index.html").write_text(html)
    (OUT / "favicon.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="#080A0F"/>'
                                     + re.sub(r"^<svg[^>]*>|</svg>$", "", marchio()) + "</svg>")
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITO['url']}/sitemap.xml\n")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{SITO["url"]}/</loc><lastmod>{datetime.now(ROMA):%Y-%m-%d}</lastmod><changefreq>daily</changefreq></url></urlset>\n')
    cname = OUT / "CNAME"
    if SITO.get("cname_attivo"):
        cname.write_text(SITO["dominio"] + "\n")
    elif cname.exists():
        cname.unlink()
    print(f"[build] ok: {len(LONG)} long, {len(SHORT)} short, {len(ART)} articoli, {len(LIN)} post, {len(TOOL)} tool "
          f"— index.html {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
