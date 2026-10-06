"""Substack -> data/substack.json (archivio pubblico, nessuna credenziale)."""
import re
import sys
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comune import adesso, leggi, log, scarica, scrivi  # noqa: E402

BASE = leggi("config/sito.json")["substack"]["url"]


def archivio(sort, offset, limit):
    return scarica(f"{BASE}/api/v1/archive?sort={sort}&offset={offset}&limit={limit}", json_=True,
                   header={"Accept": "application/json", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}, tentativi=2)


def voce(x):
    return {
        "id": x["id"],
        "titolo": x["title"],
        "sottotitolo": x.get("subtitle") or x.get("search_engine_description") or "",
        "url": x["canonical_url"],
        "data": x["post_date"],
        "cover": x.get("cover_image"),
        "tag": [t["name"] for t in x.get("postTags") or []],
        "reazioni": x.get("reaction_count") or 0,
        "commenti": x.get("comment_count") or 0,
        "restack": x.get("restacks") or 0,
        "pagamento": x.get("audience") != "everyone",
    }


def da_rss():
    """Ripiego: Substack blocca spesso l'API dai server cloud (403). Il feed dà gli ultimi ~20 articoli."""
    cache = {p["url"]: p for p in (leggi("data/substack.json") or {}).get("post", [])}
    try:
        x = scarica(f"{BASE}/feed", header={"Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}, tentativi=2)
    except Exception as e:
        # Cloudflare blocca anche il feed dagli IP dei data center: passo da rss2json.com (servizio pubblico, senza chiave)
        log("substack", f"feed diretto non disponibile ({e}), uso rss2json")
        return da_rss2json(cache)
    nuovi = []
    for it in x.split("<item>")[1:]:
        g = lambda tag: (re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", it, re.S) or [None, ""])[1]  # noqa: E731
        url = g("link").strip()
        vecchio = cache.get(url, {})
        cover = re.search(r'<enclosure url="([^"]+)"', it)
        nuovi.append({**vecchio,
                      "id": vecchio.get("id", url), "titolo": unescape(g("title")).strip(),
                      "sottotitolo": unescape(re.sub("<[^>]+>", "", g("description"))).strip() or vecchio.get("sottotitolo", ""),
                      "url": url, "data": parsedate_to_datetime(g("pubDate")).isoformat(),
                      "cover": vecchio.get("cover") or (cover[1] if cover else None)})
    visti = {p["url"] for p in nuovi}
    return nuovi + [p for p in cache.values() if p["url"] not in visti]


def da_rss2json(cache):
    from urllib.parse import quote
    from datetime import datetime, timezone
    r = scarica(f"https://api.rss2json.com/v1/api.json?rss_url={quote(BASE + '/feed', safe='')}", json_=True)
    if r.get("status") != "ok":
        raise RuntimeError(f"rss2json: {r.get('message', r.get('status'))}")
    nuovi = []
    for it in r.get("items", []):
        url = it["link"].split("?")[0]
        vecchio = cache.get(url, {})
        data = datetime.strptime(it["pubDate"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).isoformat()
        cover = (it.get("enclosure") or {}).get("link") or it.get("thumbnail") or None
        nuovi.append({**vecchio, "id": vecchio.get("id", url), "titolo": unescape(it["title"]).strip(),
                      "sottotitolo": vecchio.get("sottotitolo") or unescape(re.sub("<[^>]+>", "", it.get("description", ""))).strip()[:300],
                      "url": url, "data": data, "cover": vecchio.get("cover") or cover})
    visti = {p["url"] for p in nuovi}
    return nuovi + [p for p in cache.values() if p["url"] not in visti]


def main():
    try:
        principale()
    except Exception as e:
        log("substack", f"API non disponibile ({e}), uso il feed RSS")
        post = da_rss()
        if not post:
            raise RuntimeError("feed vuoto")
        post.sort(key=lambda p: p["data"], reverse=True)
        vecchio = leggi("data/substack.json") or {}
        scrivi("data/substack.json", {"aggiornato": adesso(), "post": post, "top": vecchio.get("top", []), "fonte": "rss"})
        log("substack", f"ok (rss): {len(post)} articoli")


def principale():
    post = []
    for off in range(0, 500, 50):
        r = archivio("new", off, 50)
        post += [voce(x) for x in r]
        if len(r) < 50:
            break
    if not post:
        raise RuntimeError("archivio vuoto")
    top = [x["id"] for x in archivio("top", 0, 12)]
    scrivi("data/substack.json", {"aggiornato": adesso(), "post": post, "top": top, "fonte": "api"})
    log("substack", f"ok: {len(post)} articoli, top {len(top)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("substack", f"ERRORE: {e} — resta la cache precedente")
