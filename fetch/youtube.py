"""YouTube -> data/youtube.json

Modo "api": YouTube Data API v3 con YOUTUBE_API_KEY, oppure OAuth
(YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN). Legge tutto il canale.
Modo "pubblico" (nessuna credenziale): feed RSS del canale (ultimi 15, con views),
pagine delle playlist (appartenenza ai temi) e pagina canale (iscritti).
Il file è cumulativo: ogni giro aggiunge/aggiorna, non perde i video già noti.
"""
import json
import os
import re
import sys
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comune import ROOT, adesso, leggi, log, scarica, scrivi  # noqa: E402

SITO = leggi("config/sito.json")
CFG = leggi("config/temi.json")
CH = SITO["youtube"]["channelId"]
SHORT_MAX = 180  # secondi
PLAYLIST = [x for x in CFG["temi"] + CFG["rubriche"] if x.get("playlist")]

store = leggi("data/youtube.json") or {}
store.setdefault("video", {})
store.setdefault("playlist", {})
store.setdefault("canale", {})


def unisci(v):
    nuovo = dict(store["video"].get(v["id"], {}))
    nuovo.update({k: x for k, x in v.items() if x not in (None, "", [])})
    store["video"][v["id"]] = nuovo


def secondi_iso(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + int(m[3] or 0) if m else None


def secondi_testo(t):
    if not t:
        return None
    s = 0
    for x in t.split(":"):
        s = s * 60 + int(x)
    return s


# ---------------- modo API ----------------
def autorizzazione():
    if os.environ.get("YOUTUBE_API_KEY"):
        return {"key": os.environ["YOUTUBE_API_KEY"]}, {}
    cid, sec, rt = (os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and rt):
        return None
    tok = scarica("https://oauth2.googleapis.com/token", json_=True, dati={
        "client_id": cid, "client_secret": sec, "refresh_token": rt, "grant_type": "refresh_token"})
    return {}, {"Authorization": f"Bearer {tok['access_token']}"}


def modo_api(auth):
    q0, h = auth

    def api(path, **params):
        params.update(q0)
        from urllib.parse import urlencode
        return scarica(f"https://www.googleapis.com/youtube/v3/{path}?{urlencode(params)}", json_=True, header=h)

    def tutti(pl, pagine=20):
        ids, tok = [], None
        for _ in range(pagine):
            r = api("playlistItems", part="contentDetails", playlistId=pl, maxResults=50, **({"pageToken": tok} if tok else {}))
            ids += [x["contentDetails"]["videoId"] for x in r["items"]]
            tok = r.get("nextPageToken")
            if not tok:
                break
        return ids

    ch = api("channels", part="statistics,contentDetails", id=CH)["items"][0]
    store["canale"] = {
        "iscritti": int(ch["statistics"].get("subscriberCount", 0)) or None,
        "video": int(ch["statistics"].get("videoCount", 0)) or None,
    }
    uploads = tutti(ch["contentDetails"]["relatedPlaylists"]["uploads"])
    for i in range(0, len(uploads), 50):
        r = api("videos", part="snippet,statistics,contentDetails", id=",".join(uploads[i:i + 50]))
        for v in r["items"]:
            sec = secondi_iso(v["contentDetails"]["duration"])
            unisci({
                "id": v["id"], "titolo": v["snippet"]["title"], "desc": v["snippet"]["description"][:600],
                "data": v["snippet"]["publishedAt"], "views": int(v["statistics"].get("viewCount", 0)),
                "secondi": sec, "short": sec is not None and sec <= SHORT_MAX,
                "tags": (v["snippet"].get("tags") or [])[:15],
            })
    for pl in PLAYLIST:
        try:
            store["playlist"][pl["playlist"]] = tutti(pl["playlist"], 6)
        except Exception as e:
            log("youtube", f"playlist {pl['nome']}: {e} (tengo la precedente)")
    log("youtube", f"API: {len(uploads)} upload, {store['canale'].get('iscritti')} iscritti")


# ---------------- modo pubblico ----------------
def dati_iniziali(html):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    return json.loads(m[1]) if m else {}


def cerca(o, chiave, out=None):
    out = [] if out is None else out
    if isinstance(o, list):
        for x in o:
            cerca(x, chiave, out)
    elif isinstance(o, dict):
        if chiave in o:
            out.append(o[chiave])
        for x in o.values():
            cerca(x, chiave, out)
    return out


def rss():
    x = scarica(f"https://www.youtube.com/feeds/videos.xml?channel_id={CH}")
    voci = x.split("<entry>")[1:]
    for e in voci:
        def g(pat):
            m = re.search(pat, e, re.S)
            return m[1] if m else None
        unisci({
            "id": g(r"<yt:videoId>(.*?)<"),
            "titolo": unescape(g(r"<title>(.*?)</title>") or ""),
            "desc": unescape(g(r"<media:description>(.*?)</media:description>") or "")[:600],
            "data": g(r"<published>(.*?)<"),
            "views": int(g(r'views="(\d+)"') or 0) or None,
            "short": "/shorts/" in (g(r'rel="alternate" href="(.*?)"') or ""),
        })
    log("youtube", f"RSS: {len(voci)} video recenti")


def playlist_pubbliche():
    for pl in PLAYLIST:
        try:
            d = dati_iniziali(scarica(f"https://www.youtube.com/playlist?list={pl['playlist']}&hl=it&gl=IT"))
            ids = []
            for l in cerca(d, "lockupViewModel"):
                vid = l.get("contentId")
                if l.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO" or vid in ids:
                    continue
                ids.append(vid)
                mv = re.search(r'"content":"([\d.,]+)( mila| Mln| mln)? visualizzazioni"', json.dumps(l, ensure_ascii=False))
                if mv:
                    n = float(mv[1].replace(".", "").replace(",", "."))
                    unisci({"id": vid, "views": int(n * {" mila": 1e3, " Mln": 1e6, " mln": 1e6}.get(mv[2], 1))})
                if vid not in store["video"] or not store["video"][vid].get("titolo"):
                    m = re.search(r'"thumbnailBadgeViewModel":\{"text":"(\d{1,2}:\d{2}(?::\d{2})?)"', json.dumps(l))
                    sec = secondi_testo(m[1] if m else None)
                    unisci({
                        "id": vid,
                        "titolo": l.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}).get("content"),
                        "secondi": sec, "short": sec is not None and sec <= SHORT_MAX,
                    })
            # le playlist di short usano un altro blocco: id nel comando, titolo e views nel testo accessibile
            for s in cerca(d, "shortsLockupViewModel"):
                vid = s.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {}).get("videoId")
                if not vid or vid in ids:
                    continue
                ids.append(vid)
                m = re.match(r"^(.*), ([\d.,]+)( mila| mln)? visualizzazion", s.get("accessibilityText", ""), re.S)
                views = None
                if m:
                    n = float(m[2].replace(".", "").replace(",", "."))
                    views = int(n * {" mila": 1e3, " mln": 1e6}.get(m[3], 1))
                prima = vid not in store["video"]
                unisci({"id": vid, "short": True, "views": views,
                        **({"titolo": m[1]} if m and prima else {})})
            if ids:
                store["playlist"][pl["playlist"]] = ids
        except Exception as e:
            log("youtube", f"playlist {pl['nome']}: {e} (tengo la precedente)")
    log("youtube", f"playlist lette: {len(store['playlist'])}")


def iscritti_pubblici():
    try:
        html = scarica(f"https://www.youtube.com/channel/{CH}?hl=it&gl=IT")
        m = re.search(r'"accessibilityLabel":"([\d.,]+(?: mila| mln)? iscritti)"', html)
        if m:
            store["canale"]["iscritti_testo"] = m[1]
        m = re.search(r'"content":"([\d.]+) video"', html)
        if m:
            store["canale"]["video"] = int(m[1].replace(".", ""))
    except Exception as e:
        log("youtube", f"iscritti: {e}")


def seme_locale():
    """Primo popolamento in locale dal catalogo long mantenuto dalla pipeline Gufo Reale."""
    f = Path(os.environ.get("SEED_CATALOG", ROOT.parent / "GUFO REALE" / "pipeline" / "longs_catalog.json"))
    if not f.exists():
        return
    for v in json.loads(f.read_text()).get("longs", []):
        unisci({"id": v["id"], "titolo": v["title"], "desc": v.get("desc", "")[:600], "data": v["date"],
                "views": v.get("views"), "secondi": v.get("seconds"), "short": False, "tags": v.get("tags")})
    log("youtube", "seme locale caricato")


def main():
    modo = "pubblico"
    try:
        auth = autorizzazione()
    except Exception as e:
        log("youtube", f"credenziali non valide: {e}")
        auth = None
    if auth:
        try:
            modo_api(auth)
            modo = "api"
        except Exception as e:
            log("youtube", f"API fallita ({e}), passo al modo pubblico")
    if modo == "pubblico":
        if len(store["video"]) < 30:
            seme_locale()
        rss()
        playlist_pubbliche()
        iscritti_pubblici()
    store["modo"] = modo
    store["aggiornato"] = adesso()
    scrivi("data/youtube.json", store)
    log("youtube", f"ok ({modo}): {len(store['video'])} video in archivio")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # un fetcher fallito non ferma la build: resta la cache
        log("youtube", f"ERRORE: {e} — resta la cache precedente")
