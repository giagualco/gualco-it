"""Utility condivise da fetcher e build (solo libreria standard)."""
import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Certificati: certifi se c'è, altrimenti il bundle di sistema (il Python di python.org su macOS non lo trova da solo)
try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if Path("/etc/ssl/cert.pem").exists() else ssl.create_default_context()

# .env locale; in cloud le variabili arrivano dai GitHub Secrets
_env = ROOT / ".env"
if _env.exists():
    for riga in _env.read_text().splitlines():
        if "=" in riga and not riga.lstrip().startswith("#"):
            k, v = riga.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def leggi(rel, vuoto=None):
    f = ROOT / rel
    try:
        return json.loads(f.read_text())
    except Exception:
        return vuoto


def scrivi(rel, dati):
    (ROOT / rel).write_text(json.dumps(dati, ensure_ascii=False, indent=2) + "\n")


def scarica(url, json_=False, dati=None, header=None, tentativi=3):
    h = {"User-Agent": "Mozilla/5.0 (gualco.it aggiornamento)", "Accept-Language": "it-IT,it;q=0.9"}
    h.update(header or {})
    corpo = urllib.parse.urlencode(dati).encode() if dati else None
    errore = None
    for i in range(tentativi):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=h), timeout=25, context=_SSL) as r:
                testo = r.read().decode("utf-8")
                return json.loads(testo) if json_ else testo
        except Exception as e:
            errore = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"{errore} su {url.split('?')[0]}")


def etichetta(testo, cfg):
    """Temi e rubrica per parole chiave (articoli, post, tool; ripiego per i video)."""
    t = f" {testo.lower()} "
    temi = [x["slug"] for x in cfg["temi"] if any(k in t for k in x["kw"])]
    rub = next((x["slug"] for x in cfg["rubriche"] if any(k in t for k in x["kw"])), None)
    return temi, rub


def adesso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(fonte, *m):
    print(f"[{fonte}]", *m, flush=True)
