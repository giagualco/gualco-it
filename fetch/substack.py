"""Substack -> data/substack.json (archivio pubblico, nessuna credenziale)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comune import adesso, leggi, log, scarica, scrivi  # noqa: E402

BASE = leggi("config/sito.json")["substack"]["url"]


def archivio(sort, offset, limit):
    return scarica(f"{BASE}/api/v1/archive?sort={sort}&offset={offset}&limit={limit}", json_=True)


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


def main():
    post = []
    for off in range(0, 500, 50):
        r = archivio("new", off, 50)
        post += [voce(x) for x in r]
        if len(r) < 50:
            break
    if not post:
        raise RuntimeError("archivio vuoto")
    top = [x["id"] for x in archivio("top", 0, 12)]
    scrivi("data/substack.json", {"aggiornato": adesso(), "post": post, "top": top})
    log("substack", f"ok: {len(post)} articoli, top {len(top)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("substack", f"ERRORE: {e} — resta la cache precedente")
