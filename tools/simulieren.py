#!/usr/bin/env python3
"""Balance-Simulation ("Vibe-Gaming").

Beispiele:
  python tools/simulieren.py                       # Gesamtbericht für 2, 3 und 4 Spieler
  python tools/simulieren.py --spieler 2           # nur 2 Spieler
  python tools/simulieren.py --karten koch,most    # Bericht für bestimmte Karten
  python tools/simulieren.py --geaendert origin/main --markdown bericht.md

Mit --geaendert wird zusätzlich der Kartenstand der Git-Basis simuliert
(gleiche Engine, gleiche Zufallszahlen). So zeigt der Bericht „vorher → nachher“.
Die Stimmen vom Stammtisch (tools/stammtisch.py) werden aus diesen Zahlen abgeleitet.
"""
from __future__ import annotations

import argparse
import io
import math
import random
import statistics
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bots import BOTS, Fokus  # noqa: E402
from engine.inhalte import alle_karten, lade_pakete  # noqa: E402
from engine.spiel import PARAMETER, Spiel  # noqa: E402
from tools import stammtisch  # noqa: E402

try:  # Faustformel aus dem Prüfwerkzeug (optional)
    from tools.pruefen import kosten_erwartung  # noqa: E402
except Exception:  # pragma: no cover - z. B. wenn jsonschema fehlt
    kosten_erwartung = None

# Ampel-Grenzen. Jeweils (grün von, grün bis, gelb von, gelb bis).
# Grün = im Zielbereich, Gelb = knapp daneben, Rot = deutlich daneben.
# Keine Ampel blockiert den PR, sie sind Hinweise für Menschen.
GRENZEN = {
    "fokus_siegquote": (0.40, 0.60, 0.35, 0.65),        # Fokus-Bot vs. Gierig-Bot (2 Spieler)
    "startspieler_quote_2p": (0.44, 0.56, 0.40, 0.60),
    # Größte Abweichung einer Sitzposition von der fairen Quote (1/Spielerzahl)
    "positions_abweichung": (0.0, 0.06, 0.0, 0.10),
    "runden": (10, 20, 8, 22),                          # 2 Spieler
    "runden_gross": (9, 20, 7, 22),                     # 3+ Spieler (Partien sind etwas kürzer)
    "limit_quote": (0.0, 0.01, 0.0, 0.03),              # Partien, die das Rundenlimit erreichen
}

GRUEN, GELB, ROT, INFO = "🟢", "🟡", "🔴", "ℹ️"
RANG = {GRUEN: 0, INFO: 0, GELB: 1, ROT: 2}
TYP_NAME = {"markt": "Marktkarte", "ausbau": "Ausbau", "anlass": "Anlass", "start": "Startkarte"}
ENDE_NAME = {
    "ausbauten": "Alle Ausbauten gebaut",
    "markt": f"{PARAMETER['leere_stapel_fuer_ende']} Marktstapel leer",
    "limit": f"Sicherheitslimit ({PARAMETER['max_runden']} Runden) erreicht",
}


def fokus_grenzen(spielerzahl=2):
    """Zielband fürs Fokus-Duell: fair (1/Spielerzahl) ± 10 Pkt. grün, ± 15 Pkt. gelb."""
    if spielerzahl == 2:
        return GRENZEN["fokus_siegquote"]
    fair = 1 / spielerzahl
    return (fair - 0.10, fair + 0.10, fair - 0.15, fair + 0.15)


def runden_grenzen(spielerzahl=2):
    return GRENZEN["runden"] if spielerzahl <= 2 else GRENZEN["runden_gross"]


# -- Simulation -------------------------------------------------------------------

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


def _perzentil(werte, p):
    s = sorted(werte)
    return s[min(len(s) - 1, int(p * len(s)))]


def gesamtbericht(ergebnisse, spielerzahl, karten=None):
    runden = [e["runden"] for e in ergebnisse]
    punkte = [p for e in ergebnisse for p in e["punkte"]]
    sieg_pos = defaultdict(int)
    enden = defaultdict(int)
    abstaende = []
    gekauft = Counter()
    for e in ergebnisse:
        sieg_pos[e["sieger"]] += 1
        enden[e["ende"]] += 1
        p = sorted(e["punkte"], reverse=True)
        abstaende.append(p[0] - p[1] if len(p) > 1 else 0)
        for liste in e["gekauft"]:
            gekauft.update(k for k in liste if not karten or karten.get(k, {}).get("typ") == "markt")
    n = len(ergebnisse)
    quoten = [sieg_pos[i] / n for i in range(spielerzahl)]
    return {
        "spiele": n,
        "spieler": spielerzahl,
        "runden_mittel": statistics.mean(runden),
        "runden_min_max": (min(runden), max(runden)),
        "runden_p10_p90": (_perzentil(runden, 0.1), _perzentil(runden, 0.9)),
        "punkte_mittel": statistics.mean(punkte),
        "sieger_punkte_mittel": statistics.mean(max(e["punkte"]) for e in ergebnisse),
        "abstand_mittel": statistics.mean(abstaende),
        "knapp_quote": sum(a <= 3 for a in abstaende) / n,
        "siegquote_position": quoten,
        "positions_abweichung": max(abs(q - 1 / spielerzahl) for q in quoten),
        "spielende": {k: v / n for k, v in enden.items()},
        "limit_quote": enden.get("limit", 0) / n,
        "meistgekauft": [(k, v / n) for k, v in gekauft.most_common(5)],
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
    q = siege / n
    return {"karte": kid, "partien": n, "siegquote": q, "kaeufe": kaeufe / n,
            "fair": 1 / spielerzahl, "spieler": spielerzahl,
            # 95-%-Unsicherheit der Siegquote (Normalnäherung)
            "unsicherheit": 1.96 * math.sqrt(max(q * (1 - q), 0.01) / n)}


def auswerten(karten, markt_ziel, spielerzahlen, partien, seed, n_duell, basis_karten=None):
    """Simuliert alle Spielerzahlen, optional auch den Kartenstand der Basis.

    Ergebnis: {spielerzahl: {"gesamt", "karten", "basis", "basis_karten"}}
    """
    ergebnis = {}
    for n in spielerzahlen:
        r = {"gesamt": gesamtbericht(spiele(karten, partien, n, seed=seed), n, karten),
             "karten": {kid: kartenbericht(karten, kid, n_duell, n, seed + 7) for kid in markt_ziel},
             "basis": None, "basis_karten": {}}
        if basis_karten is not None:
            try:
                r["basis"] = gesamtbericht(spiele(basis_karten, partien, n, seed=seed), n, basis_karten)
                r["basis_karten"] = {kid: kartenbericht(basis_karten, kid, n_duell, n, seed + 7)
                                     for kid in markt_ziel
                                     if basis_karten.get(kid, {}).get("typ") == "markt"}
            except Exception as e:  # noqa: BLE001 - z. B. alte Karten passen nicht zur neuen Engine
                print(f"Hinweis: Basis-Simulation fehlgeschlagen ({e})", file=sys.stderr)
                r["basis"], r["basis_karten"] = None, {}
        ergebnis[n] = r
    return ergebnis


# -- Git ---------------------------------------------------------------------------

def geaenderte_karten(basis: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{basis}...HEAD", "--", "inhalte/"],
                         capture_output=True, text=True, check=True).stdout
    return sorted({Path(p).stem for p in out.split() if p.endswith(".yaml") and not p.endswith("paket.yaml")})


def basis_pakete(basis: str, ziel: Path):
    """Entpackt inhalte/ aus der Git-Basis nach `ziel` und lädt die Pakete. None bei Fehler."""
    try:
        ref = subprocess.run(["git", "merge-base", basis, "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip() or basis
        tar = subprocess.run(["git", "archive", ref, "inhalte"], capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(ziel, filter="data")
        return lade_pakete(ziel / "inhalte")
    except Exception as e:  # noqa: BLE001 - Vergleich ist optional
        print(f"Hinweis: Kein Vergleich mit {basis} möglich ({e})", file=sys.stderr)
        return None


# -- Bewertung ---------------------------------------------------------------------

def ampel(wert, grenzen):
    g_lo, g_hi, y_lo, y_hi = grenzen
    if g_lo <= wert <= g_hi:
        return GRUEN
    if y_lo <= wert <= y_hi:
        return GELB
    return ROT


def zahl(x, stellen=1):
    return f"{x:.{stellen}f}".replace(".", ",")


def prozent(x):
    return f"{x * 100:.0f} %"


def tausend(n):
    return f"{n:,}".replace(",", ".")


def karten_urteil(b, spielerzahl=2):
    q = b["siegquote"]
    g_lo, g_hi, y_lo, y_hi = fokus_grenzen(spielerzahl)
    von100 = round(q * 100)
    fair = round(100 / spielerzahl)
    if g_lo <= q <= g_hi:
        return (GRUEN, f"Ausgewogen. Wer die Karte gezielt kauft, gewinnt {von100} von 100 Partien "
                       f"(fair wären {fair}).")
    if q > g_hi:
        stufe = "etwas zu stark" if q <= y_hi else "deutlich zu stark"
        return (GELB if q <= y_hi else ROT,
                f"Vermutlich {stufe}: {von100} von 100 Siegen (fair wären {fair}). "
                "Idee: Kosten erhöhen oder Effekt abschwächen.")
    stufe = "etwas zu schwach" if q >= y_lo else "deutlich zu schwach"
    return (GELB if q >= y_lo else ROT,
            f"Vermutlich {stufe}: nur {von100} von 100 Siegen (fair wären {fair}). "
            "Idee: Kosten senken oder Effekt verstärken.")


def bewerte(ergebnis):
    """Ampeln je Spielerzahl. Ergänzt ergebnis[n]["ampeln"]."""
    for n, r in ergebnis.items():
        g = r["gesamt"]
        a = {"runden": ampel(g["runden_mittel"], runden_grenzen(n)),
             "position": (ampel(g["siegquote_position"][0], GRENZEN["startspieler_quote_2p"]) if n == 2
                          else ampel(g["positions_abweichung"], GRENZEN["positions_abweichung"])),
             "limit": ampel(g["limit_quote"], GRENZEN["limit_quote"]),
             "karten": {kid: karten_urteil(b, n) for kid, b in r["karten"].items()}}
        r["ampeln"] = a
    return ergebnis


GESAMT_TEXT = {
    GRUEN: ("Alles im grünen Bereich",
            "Die Simulation findet keine Auffälligkeiten. Aus Balance-Sicht spricht nichts gegen diesen PR."),
    GELB: ("Kleine Auffälligkeiten",
           "Kein Grund zur Sorge, aber mindestens ein Wert liegt knapp außerhalb des Zielbereichs. "
           "Bitte die gelben Punkte unten anschauen und, wenn möglich, am Tisch testen."),
    ROT: ("Deutliche Auffälligkeit",
          "Mindestens ein Wert liegt klar außerhalb des Zielbereichs. "
          "Bitte die roten Punkte unten prüfen, bevor der PR gemergt wird."),
}


def schlimmste(lichter):
    s = max(lichter, key=RANG.get, default=GRUEN)
    return GRUEN if s == INFO else s


def gesamtampel(ergebnis):
    lichter = []
    for r in ergebnis.values():
        a = r["ampeln"]
        lichter += [a["runden"], a["position"], a["limit"]] + [lt for lt, _ in a["karten"].values()]
    return schlimmste(lichter)


# -- Markdown ----------------------------------------------------------------------

def _vorher(jetzt_txt, vorher_txt, gleich):
    if vorher_txt is None:
        return jetzt_txt
    return f"{jetzt_txt}<br><sub>vorher {'gleich' if gleich else vorher_txt}</sub>"


def _positionen(g):
    if g["spieler"] == 2:
        return f"{prozent(g['siegquote_position'][0])} Startspieler"
    return " / ".join(f"{q * 100:.0f}" for q in g["siegquote_position"]) + " %"


def _kosten_text(c, b, n):
    """Faustformel-Kommentar zur Karte und Faustformel-Preis (oder None)."""
    if not (kosten_erwartung and c.get("effekte") and isinstance(c.get("kosten"), int)):
        return "", None
    try:
        soll = kosten_erwartung(c)
    except Exception:  # noqa: BLE001
        return "", None
    if abs(soll - c["kosten"]) <= 2:
        return "", soll
    guenstig = c["kosten"] < soll
    richtung = "günstig" if guenstig else "teuer"
    q, (g_lo, g_hi) = b["siegquote"], fokus_grenzen(n)[:2]
    if g_lo <= q <= g_hi:
        return (f" Die Faustformel hält den Preis für zu {richtung}, "
                "in der Simulation fällt das aber nicht auf."), soll
    if (q > g_hi) == guenstig:
        return f" Die Faustformel sieht das auch so (Preis wirkt zu {richtung}).", soll
    return (f" Die Faustformel hält den Preis dagegen für zu {richtung}. "
            "Hier widersprechen sich beide, ein Spieltest klärt das am besten."), soll


def markdown(ergebnis, karten, warnungen, *, ziel=None, basis_name="", basis_karten=None) -> str:
    ziel = ziel or []
    basis_karten = basis_karten or {}
    zahlen = sorted(ergebnis)
    haupt = 2 if 2 in ergebnis else zahlen[0]
    mit_basis = any(r["basis"] for r in ergebnis.values())
    licht = gesamtampel(ergebnis)
    titel, satz = GESAMT_TEXT[licht]
    todo = []

    z = ["## 🍺 Balance-Bericht (Simulation)", "",
         f"> ### {licht} {titel}", f"> {satz}", ""]

    g0 = ergebnis[zahlen[0]]["gesamt"]
    teile = [f"**{tausend(g0['spiele'])} simulierte Partien** je Spielerzahl "
             f"({', '.join(str(n) for n in zahlen)} Spieler)"]
    if mit_basis:
        teile.append(f"verglichen mit dem Stand von `{basis_name}` („vorher“)")
    z.append("**Was wurde geprüft?** " + ", ".join(teile) + ".")
    if ziel:
        namen = [f"{karten.get(k, {}).get('name', k)} ({TYP_NAME.get(karten.get(k, {}).get('typ'), 'entfernt')})"
                 for k in ziel]
        z.append(f"Geänderte Karten in diesem PR: {', '.join(namen)}.")
    else:
        z.append("Dieser PR ändert keine Karten. Geprüft wurde nur, ob das Spiel als Ganzes rund läuft.")
    z.append("")

    # Stimmen vom Stammtisch
    stimmen = stammtisch.stimmen(ergebnis, karten, ziel=ziel, basis_karten=basis_karten,
                                 gesamt=licht, kosten=lambda c, b, n: _kosten_text(c, b, n)[1])
    z += ["### 🎭 Stimmen vom Stammtisch", "",
          "_Erfundene Stammgäste lesen die Zahlen unten, jeder mit einem anderen Blick aufs Spiel._", ""]
    for s in stimmen:
        z += [f"**{s['emoji']} {s['name']}**, _{s['rolle']}_ · {s['daumen']}", f"> {s['text']}", ""]

    # Karten
    markt = [kid for kid in ziel if karten.get(kid, {}).get("typ") == "markt"]
    if markt:
        z += ["### 🎯 Die Karten aus diesem PR", "",
              "Ein Bot kauft die Karte bevorzugt, die anderen spielen normal. Fair wäre eine Siegquote von "
              + ", ".join(f"{prozent(1 / n)} bei {n}" for n in zahlen) + " Spielern.", "",
              "| Karte | Kosten | " + " | ".join(f"{n} Spieler" for n in zahlen) + " | Was heißt das? |",
              "|---|---|" + "---|" * len(zahlen) + "---|"]
        for kid in markt:
            c = karten[kid]
            zellen = []
            urteile = []
            for n in zahlen:
                r = ergebnis[n]
                b = r["karten"][kid]
                lt, text = r["ampeln"]["karten"][kid]
                urteile.append((RANG[lt], n, lt, text, b))
                alt = r["basis_karten"].get(kid)
                jetzt = f"{lt} {prozent(b['siegquote'])} ± {b['unsicherheit'] * 100:.0f}"
                if alt:
                    zellen.append(_vorher(jetzt, prozent(alt["siegquote"]),
                                          abs(alt["siegquote"] - b["siegquote"]) < 0.01))
                elif mit_basis and kid not in basis_karten:
                    zellen.append(f"{jetzt}<br><sub>neu</sub>")
                else:
                    zellen.append(jetzt)
            # Urteil: schlimmste Spielerzahl, bei Gleichstand die Hauptspielerzahl
            urteile.sort(key=lambda u: (-u[0], u[1] != haupt))
            _, n_schlecht, lt, text, b = urteile[0]
            zusatz, soll = _kosten_text(c, b, n_schlecht)
            if lt != GRUEN:
                todo.append(f"{lt} **{c.get('name', kid)}** ({n_schlecht} Spieler): {text}{zusatz}")
                text = f"Bei {n_schlecht} Spielern: {text}"
            kosten = str(c.get("kosten", "–")) + (f" (Faustformel ≈ {zahl(soll)})" if soll is not None else "")
            z.append(f"| {c.get('name', kid)} | {kosten} | " + " | ".join(zellen) + f" | {text}{zusatz} |")
        z.append("")
    nicht_markt = [k for k in ziel if karten.get(k, {}).get("typ") not in ("markt", None)]
    if nicht_markt:
        namen = ", ".join(karten[k].get("name", k) for k in nicht_markt)
        z += [f"_{namen}: Ausbauten, Anlässe und Startkarten lassen sich nicht einzeln im Duell testen. "
              "Ihre Wirkung steckt in den Werten zum Gesamtspiel unten"
              + (" (achte auf „vorher“)." if mit_basis else ".") + "_", ""]

    # Gesamtspiel je Spielerzahl
    def zeile(name, ziel_txt, erklaerung, zelle):
        return f"| {name} | " + " | ".join(zelle(n) for n in zahlen) + f" | {ziel_txt} | {erklaerung} |"

    def z_runden(n):
        r = ergebnis[n]
        g, b = r["gesamt"], r["basis"]
        return _vorher(f"{r['ampeln']['runden']} Ø {zahl(g['runden_mittel'])}",
                       b and zahl(b["runden_mittel"]), b and abs(b["runden_mittel"] - g["runden_mittel"]) < 0.2)

    def z_position(n):
        r = ergebnis[n]
        g, b = r["gesamt"], r["basis"]
        gleich = b and abs(b["positions_abweichung"] - g["positions_abweichung"]) < 0.015
        return _vorher(f"{r['ampeln']['position']} {_positionen(g)}", b and _positionen(b), gleich)

    def z_limit(n):
        r = ergebnis[n]
        g, b = r["gesamt"], r["basis"]
        return _vorher(f"{r['ampeln']['limit']} {zahl(g['limit_quote'] * 100)} %",
                       b and f"{zahl(b['limit_quote'] * 100)} %",
                       b and abs(b["limit_quote"] - g["limit_quote"]) < 0.002)

    def z_knapp(n):
        r = ergebnis[n]
        g, b = r["gesamt"], r["basis"]
        return _vorher(f"{INFO} {prozent(g['knapp_quote'])}", b and prozent(b["knapp_quote"]),
                       b and abs(b["knapp_quote"] - g["knapp_quote"]) < 0.01)

    rg2, rg3 = runden_grenzen(2), runden_grenzen(3)
    runden_ziel = f"{rg2[0]}–{rg2[1]}" + (f" (ab 3 Sp.: {rg3[0]}–{rg3[1]})" if max(zahlen) > 2 else "")
    sg = GRENZEN["startspieler_quote_2p"]
    z += ["### 📊 Das Spiel als Ganzes", "",
          "| Kennzahl | " + " | ".join(f"{n} Spieler" for n in zahlen) + " | Ziel | Was heißt das? |",
          "|---|" + "---|" * len(zahlen) + "---|---|",
          zeile("Spieldauer (Runden)", runden_ziel, "Wie lange eine Partie dauert.", z_runden),
          zeile("Siege nach Sitzplatz", f"2 Sp.: {prozent(sg[0])}–{prozent(sg[1])}, sonst fair ± 6 Pkt.",
                "Wie oft gewinnt, wer als 1., 2., … dran ist. Jeder Platz sollte gleich gute Chancen haben.",
                z_position),
          zeile("Festgefahrene Partien", f"≤ {prozent(GRENZEN['limit_quote'][1])}",
                "Partien, die nicht regulär enden (Rundenlimit).", z_limit),
          zeile("Knappe Partien", "–", "Anteil der Partien mit höchstens 3 Ruf Abstand. Je höher, desto spannender.",
                z_knapp),
          ""]

    for n in zahlen:
        r = ergebnis[n]
        a, g, b = r["ampeln"], r["gesamt"], r["basis"]
        lo, hi = runden_grenzen(n)[:2]
        if a["runden"] != GRUEN:
            art = "zu kurz, Aufbau lohnt sich kaum" if g["runden_mittel"] < lo else "zu lang"
            todo.append(f"{a['runden']} **Spieldauer bei {n} Spielern:** Ø {zahl(g['runden_mittel'])} Runden "
                        f"ist {art}. Prüfen, ob die Änderung das Spielende zu früh oder zu spät auslöst.")
        elif b and abs(g["runden_mittel"] - b["runden_mittel"]) >= 1:
            d = g["runden_mittel"] - b["runden_mittel"]
            todo.append(f"{INFO} **Spieldauer bei {n} Spielern** hat sich spürbar verändert "
                        f"({f'{d:+.1f}'.replace('.', ',')} Runden). Noch im grünen Bereich.")
        if a["position"] != GRUEN:
            todo.append(f"{a['position']} **Sitzplatz bei {n} Spielern:** Die Siege sind ungleich verteilt "
                        f"({_positionen(g)}). Ein Platz ist im Vorteil.")
        elif b and abs(g["positions_abweichung"] - b["positions_abweichung"]) >= 0.04:
            todo.append(f"{INFO} **Sitzplatz bei {n} Spielern:** Die Verteilung hat sich verschoben "
                        f"({_positionen(b)} → {_positionen(g)}). Noch im grünen Bereich.")
        if a["limit"] != GRUEN:
            todo.append(f"{a['limit']} **Festgefahrene Partien bei {n} Spielern:** "
                        f"{zahl(g['limit_quote'] * 100)} % erreichen das Rundenlimit. "
                        "Vermutlich lohnt sich Bauen oder Kaufen nicht mehr genug.")

    z += ["### 💡 Was jetzt?", ""]
    todo.sort(key=lambda t: -RANG.get(t.split(" ", 1)[0], 0))
    if any(not t.startswith(INFO) for t in todo):
        z += [f"- {t}" for t in todo]
    else:
        z += ["- ✅ Aus Sicht der Simulation gibt es nichts zu tun."] + [f"- {t}" for t in todo]
    z += [f"- ⚠️ {w}" for w in warnungen]
    z.append("- 🎲 Die Bots sind einfach gestrickt. Ein echter Spieltest am Tisch ist immer besser: "
             "Ergebnis gern als Spieltest-Issue melden.")
    z.append("")

    # Erklärung für Neulinge
    g = fokus_grenzen(2)
    z += ["<details><summary>📖 <b>Wie lese ich diesen Bericht?</b></summary>", "",
          "**Die Ampel**",
          "- 🟢 im Zielbereich, alles gut",
          "- 🟡 knapp daneben: anschauen, oft reicht ein Spieltest",
          "- 🔴 deutlich daneben: die Änderung sollte vermutlich angepasst werden",
          "- ℹ️ nur zur Information, ohne Bewertung",
          "",
          "Das Gesamturteil oben ist die schlechteste Ampel über alle Spielerzahlen. "
          "Keine Ampel blockiert den PR. Die Entscheidung treffen Menschen.",
          "",
          "**Die Begriffe**",
          "- **Bots:** Computer-Spieler, die nach einfachen Regeln Karten kaufen und bauen. "
          "Sie spielen tausende Partien in wenigen Sekunden.",
          "- **Stimmen vom Stammtisch:** erfundene Figuren, die die Zahlen aus ihrer Sicht kommentieren. "
          "Ihre Meinung wird nach festen Regeln aus den Simulationsergebnissen abgeleitet, "
          "sie haben nicht selbst gespielt.",
          "- **Siegquote (Fokus-Duell):** Ein Bot kauft die neue Karte bevorzugt (bis zu 3 Stück), "
          "die anderen spielen ganz normal. Gewinnt der Fokus-Bot viel öfter als fair, "
          "ist die Karte zu stark. Gewinnt er viel seltener, ist sie zu schwach. "
          f"Bei 2 Spielern: grün {prozent(g[0])}–{prozent(g[1])}, gelb {prozent(g[2])}–{prozent(g[3])}. "
          "Bei mehr Spielern: fair ± 10 Punkte grün, ± 15 Punkte gelb.",
          "- **± Zahl:** die Messungenauigkeit. Bei „48 % ± 4“ liegt der wahre Wert ziemlich sicher "
          "zwischen 44 % und 52 %.",
          "- **vorher:** derselbe Wert mit den Karten vor diesem PR. „neu“ heißt: Die Karte gab es vorher nicht.",
          "- **Faustformel:** ein Richtwert für die Kosten, berechnet aus den Effekten der Karte "
          "(siehe `docs/BALANCE.md`). Weichen Kosten und Faustformel um mehr als 2 ab, lohnt ein Blick.",
          "- **Siege nach Sitzplatz:** Bei 2 Spielern steht dort, wie oft der Startspieler gewinnt. "
          "Bei mehr Spielern stehen die Siegquoten aller Plätze, z. B. „26 / 27 / 23 / 24 %“.",
          "- **Festgefahrene Partien:** Partien, die nach "
          f"{PARAMETER['max_runden']} Runden abgebrochen werden, weil keiner das Ende auslöst.",
          "",
          "</details>", ""]

    # Details
    z += ["<details><summary>🔬 <b>Details für Tüftler</b></summary>", ""]
    for n in zahlen:
        r = ergebnis[n]
        g = r["gesamt"]
        p10, p90 = g["runden_p10_p90"]
        mn, mx = g["runden_min_max"]
        z += [f"**{n} Spieler**",
              f"- Spieldauer: Ø {zahl(g['runden_mittel'])} Runden, 80 % der Partien zwischen "
              f"{p10} und {p90} (kürzeste {mn}, längste {mx})",
              f"- Ruf: Ø {zahl(g['punkte_mittel'])} je Spieler, Ø {zahl(g['sieger_punkte_mittel'])} beim Sieger, "
              f"Ø Abstand Sieger zu Platz 2: {zahl(g['abstand_mittel'])}",
              "- Siege nach Sitzplatz: " + " / ".join(prozent(x) for x in g["siegquote_position"]),
              "- Wie Partien enden: " + ", ".join(
                  f"{ENDE_NAME.get(k, k)} {zahl(v * 100)} %"
                  for k, v in sorted(g["spielende"].items(), key=lambda kv: -kv[1])),
              "- Meistgekaufte Marktkarten (Ø pro Partie, alle Bots): " + ", ".join(
                  f"{karten.get(k, {}).get('name', k)} {zahl(v)}" for k, v in g["meistgekauft"])]
        for kid, b in r["karten"].items():
            alt = r["basis_karten"].get(kid)
            txt = (f"- {karten[kid].get('name', kid)}: Siegquote {prozent(b['siegquote'])}, "
                   f"Ø gekauft {zahl(b['kaeufe'])}")
            if alt:
                txt += f" (vorher {prozent(alt['siegquote'])}, Ø gekauft {zahl(alt['kaeufe'])})"
            z.append(txt)
        z.append("")
    erste = next((b for r in ergebnis.values() for b in r["karten"].values()), None)
    if erste:
        z.append(f"Fokus-Duell: {tausend(erste['partien'])} Partien je Karte und Spielerzahl, Sitzplätze wechseln.")
    z += ["Grenzwerte und Methode: `tools/simulieren.py`, `tools/stammtisch.py` und `docs/BALANCE.md`", "",
          "</details>", ""]

    z.append("_Die Simulation ersetzt keinen echten Spieltest. Sie zeigt nur grobe Ausreißer._")
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partien", type=int, default=2000, help="Partien je Spielerzahl")
    ap.add_argument("--duell-partien", type=int, default=0,
                    help="Partien je Fokus-Duell (Standard: max(400, partien/3))")
    ap.add_argument("--spieler", default="2,3,4", help="kommagetrennte Spielerzahlen, z. B. 2 oder 2,3,4")
    ap.add_argument("--pakete", default="basis", help="kommagetrennt, z. B. basis,heuriger")
    ap.add_argument("--karten", default="", help="kommagetrennte Karten-IDs")
    ap.add_argument("--geaendert", default="", help="Git-Basis, z. B. origin/main")
    ap.add_argument("--ohne-vergleich", action="store_true", help="Basis nicht zusätzlich simulieren")
    ap.add_argument("--alle-karten", action="store_true")
    ap.add_argument("--markdown", default="")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    spielerzahlen = sorted({int(s) for s in str(args.spieler).split(",") if s.strip()})
    pakete = lade_pakete()
    aktiv = args.pakete.split(",")
    ziel = [k for k in args.karten.split(",") if k]
    if args.geaendert:
        ziel += [k for k in geaenderte_karten(args.geaendert) if k not in ziel]
        # Pakete der geänderten Karten automatisch aktivieren
        for pid, p in pakete.items():
            if any(k in p["karten"] for k in ziel) and pid not in aktiv:
                aktiv.append(pid)
    karten = alle_karten(pakete, aktiv)
    markt_ziel = [k for k in ziel if karten.get(k, {}).get("typ") == "markt"]
    if args.alle_karten:
        markt_ziel = sorted(k for k, c in karten.items() if c["typ"] == "markt")
        ziel = ziel + [k for k in markt_ziel if k not in ziel]

    n_duell = args.duell_partien or max(400, args.partien // 3)
    with tempfile.TemporaryDirectory() as tmp:
        basis_karten = None
        if args.geaendert and not args.ohne_vergleich:
            bp = basis_pakete(args.geaendert, Path(tmp))
            if bp is not None:
                basis_karten = alle_karten(bp, [p for p in aktiv if p in bp])
        ergebnis = bewerte(auswerten(karten, markt_ziel, spielerzahlen, args.partien, args.seed,
                                     n_duell, basis_karten))

    warnungen = []
    entfernt = [k for k in ziel if k not in karten]
    if entfernt:
        warnungen.append("Entfernte Karten: " + ", ".join(entfernt))

    md = markdown(ergebnis, karten, warnungen, ziel=ziel,
                  basis_name=args.geaendert.removeprefix("origin/"), basis_karten=basis_karten)
    print(md)
    if args.markdown:
        Path(args.markdown).write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
