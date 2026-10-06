"""Aggiorna data/linkedin.json — passo 'aggiorna-sito-linkedin' della pubblicazione del giovedì.

Aggiunge (o aggiorna) il rilancio personale della settimana:
    python3 strumenti/aggiorna_linkedin.py post --id W41-2026 --data 2026-10-08 \
        --titolo "..." --estratto "..." --url <URL post personale> --url-3i <URL post 3i group>

Aggiorna i numeri letti dalla pagina Attività (file JSON {id_o_url: {"reazioni": n, "impression": n}}):
    python3 strumenti/aggiorna_linkedin.py stats --file /percorso/stats.json

Aggiungere --push per fare commit e push (il push fa partire subito la ricostruzione del sito).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fetch"))
from comune import ROOT, adesso, leggi, scrivi  # noqa: E402

FILE = "data/linkedin.json"


def salva(dati, push, messaggio):
    dati["aggiornato"] = adesso()
    scrivi(FILE, dati)
    print(f"[linkedin] salvato {FILE}: {len(dati['post'])} post")
    if push:
        git = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], check=True)  # noqa: E731
        git("add", FILE)
        if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode:
            git("commit", "-m", messaggio)
            git("pull", "--rebase", "--autostash")
            git("push")
            print("[linkedin] push fatto: il sito si ricostruisce in un paio di minuti")
        else:
            print("[linkedin] nessuna modifica da pubblicare")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post")
    for k in ("id", "data", "titolo", "estratto"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--url", help="post personale (giovedì)")
    p.add_argument("--url-3i", dest="url_3i", help="post 3i group (martedì)")
    s = sub.add_parser("stats")
    s.add_argument("--file", required=True)
    for x in (p, s):
        x.add_argument("--push", action="store_true")
    a = ap.parse_args()

    dati = leggi(FILE) or {"post": []}
    if a.cmd == "post":
        nuovo = {"id": a.id, "titolo": a.titolo, "estratto": a.estratto, "data": a.data,
                 "url": a.url, "url_3i": a.url_3i, "reazioni": None, "impression": None}
        vecchio = next((x for x in dati["post"] if x["id"] == a.id), None)
        if vecchio:
            vecchio.update({k: v for k, v in nuovo.items() if v is not None})
        else:
            dati["post"].insert(0, nuovo)
        dati["post"].sort(key=lambda x: x.get("data") or "", reverse=True)
        salva(dati, a.push, f"LinkedIn: {a.id}")
    else:
        numeri = json.loads(Path(a.file).read_text())
        n = 0
        for x in dati["post"]:
            for chiave in (x["id"], x.get("url"), x.get("url_3i")):
                if chiave and chiave in numeri:
                    x.update({k: numeri[chiave].get(k) for k in ("reazioni", "impression") if numeri[chiave].get(k) is not None})
                    n += 1
                    break
        print(f"[linkedin] numeri aggiornati per {n} post")
        salva(dati, a.push, "LinkedIn: numeri aggiornati")


if __name__ == "__main__":
    main()
