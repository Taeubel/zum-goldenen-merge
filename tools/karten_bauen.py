#!/usr/bin/env python3
"""Erzeugt aus den YAML-Dateien:
  - build/kartenuebersicht.pdf  jede Karte 1× (zum Anschauen/Spieltesten neuer Karten)
  - build/print-and-play.pdf    komplettes Spiel bis 4 Personen (9 Karten pro A4, 63 × 88 mm)
  - build/site/index.html Kartengalerie für GitHub Pages
  - build/KARTEN.md       Kartenliste als Markdown (für Release-Anhang und Wiki)

Kartentexte werden IMMER aus den Effekten generiert – nie von Hand geschrieben.
So bleiben Regeln und Karten garantiert konsistent.
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import effekte as fx  # noqa: E402
from engine.inhalte import lade_pakete  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TAG_NAMEN = {"geld": "Geld", "personal": "Personal", "gast": "Gast", "speise": "Speise", "getraenk": "Getränk"}
REGION_NAMEN = {"alle": "Österreich", "wien": "Wien", "niederoesterreich": "Niederösterreich",
                "oberoesterreich": "Oberösterreich", "salzburg": "Salzburg", "tirol": "Tirol",
                "vorarlberg": "Vorarlberg", "kaernten": "Kärnten", "steiermark": "Steiermark",
                "burgenland": "Burgenland"}
FARBEN = {"start": "#8a8a8a", "markt": "#b5121b", "ausbau": "#2f6b3a", "anlass": "#c7922b"}
TYP_NAMEN = {"start": "Startkarte", "markt": "Marktkarte", "ausbau": "Ausbau", "anlass": "Anlass"}


def satz(t: str) -> str:
    return t[:1].upper() + t[1:]


def kartentext(k: dict) -> list[str]:
    z = []
    if k.get("effekte"):
        z.append(satz(fx.text_fuer(k["effekte"])) + ".")
    if k.get("kombo"):
        ko = k["kombo"]
        karte_n = "Karte" if ko["mindestens"] == 1 else "Karten"
        z.append(f"Kombo – mind. {ko['mindestens']} andere {TAG_NAMEN[ko['tag']]}-{karte_n} gespielt: "
                 f"{fx.text_fuer(ko['effekte'])}.")
    if k.get("jede_runde"):
        z.append(f"Zu Beginn jedes deiner Züge: {fx.text_fuer(k['jede_runde'])}.")
    if k.get("beim_bau"):
        z.append(f"Sofort beim Bau: {fx.text_fuer(k['beim_bau'])}.")
    if k.get("endwertung"):
        e = k["endwertung"]
        z.append(f"Spielende: +{e['ruf']} Ruf je {e['je']} {TAG_NAMEN[e['tag']]}-Karten in deinem Deck.")
    if k.get("fuer_alle"):
        z.append(f"Alle, zu Beginn ihres Zugs: {fx.text_fuer(k['fuer_alle'])}.")
    if k.get("tag_bonus"):
        t = k["tag_bonus"]
        z.append(f"Jede gespielte {TAG_NAMEN[t['tag']]}-Karte: zusätzlich {fx.text_fuer(t['effekte'])}.")
    if k.get("ablegen"):
        z.append(f"Alle legen zu Beginn ihres Zugs {k['ablegen']} Handkarte ab.")
    if k.get("fuehrender_ablegen"):
        z.append(f"Wer beim Zugbeginn allein oder geteilt am meisten Ruf hat, legt {k['fuehrender_ablegen']} Handkarte ab.")
    if k.get("bau_rabatt"):
        z.append(f"Ausbauten kosten diese Runde {k['bau_rabatt']} Arbeit weniger.")
    if k.get("kein_bau"):
        z.append("Diese Runde darf niemand bauen.")
    return z


def kopfzeile(k: dict) -> str:
    teile = [TYP_NAMEN[k["typ"]]]
    if k.get("tags"):
        teile.append(" · ".join(TAG_NAMEN[t] for t in k["tags"]))
    teile.append(REGION_NAMEN[k["region"]])
    return " | ".join(teile)


def kostenzeile(k: dict) -> str:
    if k["typ"] == "markt":
        return f"{k['kosten']} Geld"
    if k["typ"] == "ausbau":
        return f"{k['kosten']} Arbeit · {k['ruf']} Ruf"
    if k["typ"] == "start":
        return f"{k['anzahl']}× pro Person"
    return ""


def sortiert(pakete):
    reihenfolge = {"start": 0, "markt": 1, "ausbau": 2, "anlass": 3}
    for pid, p in pakete.items():
        for k in sorted(p["karten"].values(), key=lambda c: (reihenfolge[c["typ"]], c.get("kosten", 0), c["name"])):
            yield p, k


# --- Ausgaben ---------------------------------------------------------------------

def markdown(pakete) -> str:
    z = ["# Kartenliste", "", "_Automatisch erzeugt von `tools/karten_bauen.py` – bitte nicht von Hand bearbeiten._", ""]
    # Bundesland-Fortschritt: wo fehlen noch Karten?
    zaehler = {r: 0 for r in REGION_NAMEN}
    for _, k in sortiert(pakete):
        zaehler[k["region"]] += 1
    z += ["## Karten je Bundesland", "", "| Region | Karten | |", "|---|---|---|"]
    for r, n in sorted(zaehler.items(), key=lambda x: -x[1]):
        z.append(f"| {REGION_NAMEN[r]} | {n} | {'🍺' * min(n, 10)} |")
    z.append("")
    aktuell = None
    for p, k in sortiert(pakete):
        if p["id"] != aktuell:
            aktuell = p["id"]
            z += [f"## {p['name']} (`{p['id']}`, v{p['version']}, {p['status']})", "",
                  "| Karte | Art | Kosten | Text | Region | von |", "|---|---|---|---|---|---|"]
        text = " ".join(kartentext(k)).replace("|", "/")
        z.append(f"| **{k['name']}** | {TYP_NAMEN[k['typ']]} | {kostenzeile(k)} | {text} | "
                 f"{REGION_NAMEN[k['region']]} | @{k['autor']} |")
    z.append("")
    return "\n".join(z)


def html_seite(pakete) -> str:
    karten = []
    for p, k in sortiert(pakete):
        text = "".join(f"<p>{html.escape(t)}</p>" for t in kartentext(k))
        flavor = f"<p class='fl'>{html.escape(k.get('flavor', ''))}</p>" if k.get("flavor") else ""
        karten.append(
            f"<article class='karte' data-paket='{p['id']}' data-typ='{k['typ']}' data-region='{k['region']}' "
            f"style='--f:{FARBEN[k['typ']]}'><header><h3>{html.escape(k['name'])}</h3>"
            f"<span class='k'>{html.escape(kostenzeile(k))}</span></header>"
            f"<div class='kopf'>{html.escape(kopfzeile(k))}</div><div class='t'>{text}</div>{flavor}"
            f"<footer>{html.escape(p['name'])} · von <a href='https://github.com/{k['autor']}'>@{html.escape(k['autor'])}</a>"
            f"</footer></article>")
    regionen = "".join(f"<option value='{r}'>{n}</option>" for r, n in REGION_NAMEN.items())
    paket_opts = "".join(f"<option value='{pid}'>{html.escape(p['name'])}</option>" for pid, p in pakete.items())
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zum Goldenen Merge – Kartengalerie</title>
<style>
:root{{--bg:#f6f1e7;--ink:#2a1d14}}
body{{margin:0;font-family:Georgia,serif;background:var(--bg);color:var(--ink)}}
.top{{padding:24px 20px 8px;max-width:1100px;margin:auto}}
h1{{margin:0;font-size:30px}} .sub{{opacity:.75}}
.filter{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}} select{{padding:6px;font:inherit}}
.raster{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;padding:0 20px 40px;max-width:1100px;margin:auto}}
.karte{{background:#fffdf8;border:3px solid var(--f);border-radius:12px;padding:12px;display:flex;flex-direction:column;min-height:300px}}
.karte header{{display:flex;justify-content:space-between;gap:8px;border-bottom:2px solid var(--f);padding-bottom:6px}}
.karte h3{{margin:0;font-size:18px}} .k{{font-weight:bold;color:var(--f);white-space:nowrap;font-size:14px}}
.kopf{{font-size:12px;opacity:.7;margin:6px 0}} .t{{flex:1;font-size:15px}} .t p{{margin:4px 0}}
.fl{{font-style:italic;font-size:13px;opacity:.75}} footer{{font-size:11px;opacity:.6;margin-top:6px}}
a{{color:inherit}}
</style></head><body>
<div class="top"><h1>🍺 Zum Goldenen Merge</h1>
<div class="sub">Das Open-Source-Wirtshausspiel aus Österreich – alle Karten, von der Community gebaut.</div>
<div class="filter">
<select id="p"><option value="">Alle Pakete</option>{paket_opts}</select>
<select id="t"><option value="">Alle Arten</option><option value="markt">Marktkarten</option><option value="ausbau">Ausbauten</option><option value="anlass">Anlässe</option><option value="start">Startkarten</option></select>
<select id="r"><option value="">Alle Regionen</option>{regionen}</select>
</div></div>
<main class="raster">{''.join(karten)}</main>
<script>
const f=()=>{{const p=document.getElementById('p').value,t=document.getElementById('t').value,r=document.getElementById('r').value;
document.querySelectorAll('.karte').forEach(k=>{{k.style.display=(!p||k.dataset.paket===p)&&(!t||k.dataset.typ===t)&&(!r||k.dataset.region===r)?'':'none'}})}};
['p','t','r'].forEach(i=>document.getElementById(i).addEventListener('change',f));
</script></body></html>"""


def pdf(pakete, ziel: Path, nur_stabil: bool, vollstaendig: bool = False, spieler: int = 4):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    W, H = 63 * mm, 88 * mm
    seite_w, seite_h = A4
    rand_x = (seite_w - 3 * W) / 2
    rand_y = (seite_h - 3 * H) / 2
    c = canvas.Canvas(str(ziel), pagesize=A4)
    c.setTitle("Zum Goldenen Merge – Print & Play")

    def umbruch(text, font, groesse, breite):
        worte, zeilen, z = text.split(), [], ""
        for w in worte:
            probe = (z + " " + w).strip()
            if c.stringWidth(probe, font, groesse) <= breite:
                z = probe
            else:
                zeilen.append(z)
                z = w
        if z:
            zeilen.append(z)
        return zeilen

    druck = []
    for p, k in sortiert(pakete):
        if nur_stabil and p["status"] == "experimentell":
            continue
        exemplare = 1
        if vollstaendig and k["typ"] == "start":
            exemplare = k.get("anzahl", 1) * spieler
        elif vollstaendig and k["typ"] == "markt":
            from engine.spiel import PARAMETER
            exemplare = PARAMETER["kopien_je_stapel"][spieler]
        druck += [(p, k)] * exemplare
    for i, (p, k) in enumerate(druck):
        pos = i % 9
        if i and pos == 0:
            c.showPage()
        x = rand_x + (pos % 3) * W
        y = seite_h - rand_y - (pos // 3 + 1) * H
        farbe = HexColor(FARBEN[k["typ"]])
        c.setStrokeColor(HexColor("#bbbbbb"))
        c.setLineWidth(0.3)
        c.rect(x, y, W, H)  # Schnittlinie
        c.setStrokeColor(farbe)
        c.setLineWidth(2)
        c.roundRect(x + 3 * mm, y + 3 * mm, W - 6 * mm, H - 6 * mm, 3 * mm)
        c.setFillColor(farbe)
        c.rect(x + 3 * mm, y + H - 15 * mm, W - 6 * mm, 12 * mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 5 * mm, y + H - 9 * mm, k["name"][:26])
        c.setFont("Helvetica", 7.5)
        c.drawString(x + 5 * mm, y + H - 13 * mm, kostenzeile(k))
        c.setFillColor(HexColor("#2a1d14"))
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 5 * mm, y + H - 19 * mm, kopfzeile(k)[:60])
        ty = y + H - 26 * mm
        for absatz in kartentext(k):
            for zeile in umbruch(absatz, "Helvetica", 8.5, W - 10 * mm):
                c.setFont("Helvetica", 8.5)
                c.drawString(x + 5 * mm, ty, zeile)
                ty -= 4 * mm
            ty -= 1.5 * mm
        if k.get("flavor"):
            fy = y + 13 * mm
            for zeile in umbruch(k["flavor"], "Helvetica-Oblique", 7, W - 10 * mm)[:3]:
                c.setFont("Helvetica-Oblique", 7)
                c.drawString(x + 5 * mm, fy, zeile)
                fy -= 3.3 * mm
        c.setFont("Helvetica", 5.5)
        c.setFillColor(HexColor("#777777"))
        c.drawString(x + 5 * mm, y + 4.5 * mm, f"{p['name']} · @{k['autor']} · CC BY-SA 4.0")
    c.save()
    return len(druck)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur-stabil", action="store_true", help="experimentelle Pakete nicht drucken")
    args = ap.parse_args()
    pakete = lade_pakete()
    (ROOT / "build/site").mkdir(parents=True, exist_ok=True)
    (ROOT / "build/KARTEN.md").write_text(markdown(pakete), encoding="utf-8")
    (ROOT / "build/site/index.html").write_text(html_seite(pakete), encoding="utf-8")
    n1 = pdf(pakete, ROOT / "build/kartenuebersicht.pdf", args.nur_stabil)
    n2 = pdf(pakete, ROOT / "build/print-and-play.pdf", True, vollstaendig=True)
    print(f"build/KARTEN.md, build/site/index.html, build/kartenuebersicht.pdf ({n1} Karten) "
          f"und build/print-and-play.pdf ({n2} Karten, nur stabile Pakete, bis 4 Personen) erzeugt.")


if __name__ == "__main__":
    main()
