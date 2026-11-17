#!/usr/bin/env python3
"""Balance-Simulation ("Vibe-Gaming").

Beispiele:
  python tools/simulieren.py                       # Gesamtbericht Grundspiel
  python tools/simulieren.py --karten koch,most    # Bericht für bestimmte Karten
  python tools/simulieren.py --geaendert origin/main --markdown bericht.md
"""
from __future__ import annotations

import argparse
import random
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bots import BOTS, Fokus  # noqa: E402
from engine.inhalte import alle_karten, lade_pakete  # noqa: E402
from engine.spiel import Spiel  # noqa: E402

# Grenzwerte – Überschreitung = Warnung im PR (kein harter Fehler)
GRENZEN = {
    "fokus_siegquote": (0.40, 0.60),   # Fokus-Bot vs. Gierig-Bot (2 Spieler)
    "startspieler_quote_2p": (0.44, 0.56),
    "runden": (10, 20),
}


def spiele(karten, n, spielerzahl=2, bots=("gierig", "gierig"), seed=1, markt_mit=None):
    rng = random.Random(seed)
    ergebnisse = []
    pool = sorted(k for k, c in karten.items() if c["typ"] == "markt")
    for i in range(n):
        markt = None
        if markt_mit:
            pflicht = [m for m in markt_mit if m in pool]
            rest = [m for m in pool if m not in pflicht]
            markt = pflicht + rng.sample(rest, max(0, 10 - len(pflicht)))
        bot_objs = [BOTS[bots[j % len(bots)]](random.Random(rng.random())) for j in range(spielerzahl)]
        sp = Spiel(karten, bot_objs, seed=rng.randrange(10**9), markt=markt)
        ergebnisse.append(sp.spielen())
    return ergebnisse


def gesamtbericht(ergebnisse, spielerzahl):
    runden = [e["runden"] for e in ergebnisse]
    punkte = [p for e in ergebnisse for p in e["punkte"]]
    sieg_pos = defaultdict(int)
    for e in ergebnisse:
        sieg_pos[e["sieger"]] += 1
    enden = defaultdict(int)
    for e in ergebnisse:
        enden[e["ende"]] += 1
    n = len(ergebnisse)
    return {
        "spiele": n,
        "runden_mittel": statistics.mean(runden),
        "runden_min_max": (min(runden), max(runden)),
        "punkte_mittel": statistics.mean(punkte),
        "siegquote_position": [sieg_pos[i] / n for i in range(spielerzahl)],
        "spielende": {k: v / n for k, v in enden.items()},
    }


def kartenbericht(karten, kid, n=600, spielerzahl=2, seed=7):
    """Duell: Fokus-Bot (kauft bevorzugt die Karte) gegen Gierig-Bots.

    Die Sitzposition wechselt, damit der Startspieler-Effekt herausfällt.
    """
    rng = random.Random(seed)
    pool = sorted(k for k, c in karten.items() if c["typ"] == "markt")
    rest = [m for m in pool if m != kid]
    siege = 0
    kaeufe = 0
    for i in range(n):
        markt = [kid] + rng.sample(rest, min(9, len(rest)))
        pos = i % spielerzahl
        bots = []
        for j in range(spielerzahl):
            r = random.Random(rng.random())
            bots.append(Fokus(r, kid) if j == pos else BOTS["gierig"](r))
        e = Spiel(karten, bots, seed=rng.randrange(10**9), markt=markt).spielen()
        siege += e["sieger"] == pos
        kaeufe += e["gekauft"][pos].count(kid)
    return {"karte": kid, "partien": n, "siegquote": siege / n, "kaeufe": kaeufe / n,
            "fair": 1 / spielerzahl}


def geaenderte_karten(basis: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{basis}...HEAD", "--", "inhalte/"],
                         capture_output=True, text=True, check=True).stdout
    return sorted({Path(p).stem for p in out.split() if p.endswith(".yaml") and not p.endswith("paket.yaml")})


def markdown(gesamt, karten_berichte, karten, warnungen) -> str:
    z = ["## 🍺 Balance-Bericht (Simulation)", ""]
    z.append(f"**{gesamt['spiele']} Partien** · Ø {gesamt['runden_mittel']:.1f} Runden "
             f"(min {gesamt['runden_min_max'][0]}, max {gesamt['runden_min_max'][1]}) · "
             f"Ø {gesamt['punkte_mittel']:.1f} Ruf")
    pos = " / ".join(f"{q:.0%}" for q in gesamt["siegquote_position"])
    z.append(f"Siegquote nach Startposition: {pos}")
    z.append("")
    if karten_berichte:
        z += ["Fokus-Duell: Ein Bot kauft bevorzugt die Karte (max. 3×), der andere spielt normal.",
              "Fair wäre eine Siegquote um 50 %.", "",
              "| Karte | Kosten | Siegquote Fokus | Ø gekauft | Bewertung |",
              "|---|---|---|---|---|"]
        lo, hi = GRENZEN["fokus_siegquote"]
        for b in karten_berichte:
            c = karten.get(b["karte"], {})
            q = b["siegquote"]
            flag = "✅ ausgewogen"
            if q > hi:
                flag = "⚠️ vermutlich zu stark"
            elif q < lo:
                flag = "⚠️ vermutlich zu schwach"
            z.append(f"| {c.get('name', b['karte'])} | {c.get('kosten', '–')} | {q:.0%} "
                     f"| {b['kaeufe']:.1f} | {flag} |")
        z.append("")
    if warnungen:
        z += ["**Hinweise:**"] + [f"- {w}" for w in warnungen] + [""]
    z.append("_Die Simulation ersetzt keinen echten Spieltest – sie zeigt nur grobe Ausreißer. "
             "Bitte zusätzlich einen Spieltest-Bericht (Issue-Vorlage) anlegen._")
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partien", type=int, default=2000)
    ap.add_argument("--spieler", type=int, default=2)
    ap.add_argument("--pakete", default="basis", help="kommagetrennt, z. B. basis,heuriger")
    ap.add_argument("--karten", default="", help="kommagetrennte Karten-IDs")
    ap.add_argument("--geaendert", default="", help="Git-Basis, z. B. origin/main")
    ap.add_argument("--alle-karten", action="store_true")
    ap.add_argument("--markdown", default="")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    pakete = lade_pakete()
    aktiv = args.pakete.split(",")
    ziel = [k for k in args.karten.split(",") if k]
    if args.geaendert:
        ziel += geaenderte_karten(args.geaendert)
        # Pakete der geänderten Karten automatisch aktivieren
        for pid, p in pakete.items():
            if any(k in p["karten"] for k in ziel) and pid not in aktiv:
                aktiv.append(pid)
    karten = alle_karten(pakete, aktiv)
    markt_ziel = [k for k in ziel if karten.get(k, {}).get("typ") == "markt"]
    if args.alle_karten:
        markt_ziel = sorted(k for k, c in karten.items() if c["typ"] == "markt")

    ergebnisse = spiele(karten, args.partien, args.spieler, seed=args.seed)
    gesamt = gesamtbericht(ergebnisse, args.spieler)
    berichte = []
    for kid in markt_ziel:
        berichte.append(kartenbericht(karten, kid, n=max(400, args.partien // 3), seed=args.seed + 7))

    warnungen = []
    lo, hi = GRENZEN["runden"]
    if not lo <= gesamt["runden_mittel"] <= hi:
        warnungen.append(f"Spieldauer Ø {gesamt['runden_mittel']:.1f} Runden liegt außerhalb {lo}–{hi}.")
    if args.spieler == 2:
        lo, hi = GRENZEN["startspieler_quote_2p"]
        q = gesamt["siegquote_position"][0]
        if not lo <= q <= hi:
            warnungen.append(f"Startspieler gewinnt {q:.0%} der Partien (Ziel {lo:.0%}–{hi:.0%}).")
    nicht_markt = [k for k in ziel if karten.get(k, {}).get("typ") not in ("markt", None)]
    if nicht_markt:
        warnungen.append("Ausbauten/Anlässe werden im Gesamtbericht mitgetestet: " + ", ".join(nicht_markt))

    md = markdown(gesamt, berichte, karten, warnungen)
    print(md)
    if args.markdown:
        Path(args.markdown).write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
