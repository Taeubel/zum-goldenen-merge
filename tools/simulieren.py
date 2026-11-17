#!/usr/bin/env python3
"""Balance-Simulation ("Vibe-Gaming").

Beispiele:
  python tools/simulieren.py                       # Gesamtbericht Grundspiel
  python tools/simulieren.py --karten koch,most    # Bericht für bestimmte Karten
  python tools/simulieren.py --geaendert origin/main --markdown bericht.md

Mit --geaendert wird zusätzlich der Kartenstand der Git-Basis simuliert
(gleiche Engine, gleiche Zufallszahlen). So zeigt der Bericht „vorher → nachher“.
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
    "runden": (10, 20, 8, 22),
    "limit_quote": (0.0, 0.01, 0.0, 0.03),              # Partien, die das Rundenlimit erreichen
}

def fokus_grenzen(spielerzahl=2):
    """Zielband fürs Fokus-Duell: fair (1/Spielerzahl) ± 10 Pkt. grün, ± 15 Pkt. gelb."""
    fair = 1 / spielerzahl
    if spielerzahl == 2:
        return GRENZEN["fokus_siegquote"]
    return (fair - 0.10, fair + 0.10, fair - 0.15, fair + 0.15)


GRUEN, GELB, ROT, INFO = "🟢", "🟡", "🔴", "ℹ️"
RANG = {GRUEN: 0, INFO: 0, GELB: 1, ROT: 2}
TYP_NAME = {"markt": "Marktkarte", "ausbau": "Ausbau", "anlass": "Anlass", "start": "Startkarte"}
ENDE_NAME = {
    "ausbauten": "Alle Ausbauten gebaut",
    "markt": f"{PARAMETER['leere_stapel_fuer_ende']} Marktstapel leer",
    "limit": f"Sicherheitslimit ({PARAMETER['max_runden']} Runden) erreicht",
}


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
    return {
        "spiele": n,
        "runden_mittel": statistics.mean(runden),
        "runden_min_max": (min(runden), max(runden)),
        "runden_p10_p90": (_perzentil(runden, 0.1), _perzentil(runden, 0.9)),
        "punkte_mittel": statistics.mean(punkte),
        "sieger_punkte_mittel": statistics.mean(max(e["punkte"]) for e in ergebnisse),
        "abstand_mittel": statistics.mean(abstaende),
        "knapp_quote": sum(a <= 3 for a in abstaende) / n,
        "siegquote_position": [sieg_pos[i] / n for i in range(spielerzahl)],
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
            "fair": 1 / spielerzahl,
            # 95-%-Unsicherheit der Siegquote (Normalnäherung)
            "unsicherheit": 1.96 * math.sqrt(max(q * (1 - q), 0.01) / n)}


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


def veraenderung(jetzt, vorher, einheit="pp", schwelle=0.0):
    """'+3 Pkt.' o. ä.; leer, wenn kein Vergleich. Prozentwerte als Anteil übergeben."""
    if vorher is None:
        return "–"
    if einheit == "pp":
        d = (jetzt - vorher) * 100
        txt = f"{prozent(vorher)} ({d:+.0f} Pkt.)"
    else:
        d = jetzt - vorher
        txt = f"{zahl(vorher)} ({d:+.1f})".replace(".", ",")
    return txt if abs(d) > schwelle else f"{txt[:txt.index(' (')]} (gleich)"


def karten_urteil(b, spielerzahl=2):
    q = b["siegquote"]
    g_lo, g_hi, y_lo, y_hi = fokus_grenzen(spielerzahl)
    von100 = round(q * 100)
    if g_lo <= q <= g_hi:
        return (GRUEN, f"Ausgewogen. Wer die Karte gezielt kauft, gewinnt {von100} von 100 Partien "
                       f"(fair wären {round(100 / spielerzahl)}).")
    if q > g_hi:
        stufe = "etwas zu stark" if q <= y_hi else "deutlich zu stark"
        return (GELB if q <= y_hi else ROT,
                f"Vermutlich {stufe}: {von100} von 100 Siegen. Idee: Kosten erhöhen oder Effekt abschwächen.")
    stufe = "etwas zu schwach" if q >= y_lo else "deutlich zu schwach"
    return (GELB if q >= y_lo else ROT,
            f"Vermutlich {stufe}: nur {von100} von 100 Siegen. Idee: Kosten senken oder Effekt verstärken.")


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


# -- Markdown ----------------------------------------------------------------------

def markdown(gesamt, karten_berichte, karten, warnungen, *, spielerzahl=2, ziel=None,
             basis=None, basis_name="", basis_karten=None, basis_berichte=None) -> str:
    ziel = ziel or []
    basis_berichte = basis_berichte or {}
    basis_karten = basis_karten or {}
    lichter = []
    todo = []

    # Kennzahlen des Gesamtspiels
    zeilen_gesamt = []
    r = gesamt["runden_mittel"]
    l_runden = ampel(r, GRENZEN["runden"])
    lo, hi = GRENZEN["runden"][:2]
    deutung = ("Partien dauern angenehm lang." if l_runden == GRUEN else
               "Partien sind zu kurz, Aufbau lohnt sich kaum." if r < lo else
               "Partien ziehen sich in die Länge.")
    zeilen_gesamt.append((l_runden, "Spieldauer", f"Ø {zahl(r)} Runden",
                          veraenderung(r, basis and basis["runden_mittel"], "abs", 0.2) if basis else "–",
                          f"{lo}–{hi} Runden", deutung))
    if l_runden != GRUEN:
        todo.append(f"{l_runden} **Spieldauer:** Prüfen, ob die Änderung das Spielende zu früh oder zu spät auslöst.")

    if spielerzahl == 2:
        q = gesamt["siegquote_position"][0]
        l = ampel(q, GRENZEN["startspieler_quote_2p"])
        lo, hi = GRENZEN["startspieler_quote_2p"][:2]
        deutung = ("Wer anfängt, hat keinen nennenswerten Vorteil." if l == GRUEN else
                   "Wer anfängt, gewinnt zu oft." if q > hi else "Wer anfängt, verliert zu oft.")
        zeilen_gesamt.append((l, "Fairness der Startposition", f"{prozent(q)} Siege für Startspieler",
                              veraenderung(q, basis and basis["siegquote_position"][0], "pp", 1) if basis else "–",
                              f"{prozent(lo)}–{prozent(hi)}", deutung))
        if l != GRUEN:
            todo.append(f"{l} **Startposition:** Die Änderung verschiebt den Vorteil des Startspielers.")
    else:
        q = " / ".join(prozent(x) for x in gesamt["siegquote_position"])
        zeilen_gesamt.append((INFO, "Siege nach Startposition", q, "–", f"je ≈ {prozent(1 / spielerzahl)}",
                              "Sollte ungefähr gleich verteilt sein."))

    lq = gesamt["limit_quote"]
    l = ampel(lq, GRENZEN["limit_quote"])
    zeilen_gesamt.append((l, "Festgefahrene Partien", f"{zahl(lq * 100)} %",
                          (f"{zahl(basis['limit_quote'] * 100)} %" if basis else "–"),
                          f"höchstens {prozent(GRENZEN['limit_quote'][1])}",
                          "Fast jede Partie endet regulär." if l == GRUEN else
                          "Zu viele Partien kommen nicht zum Ende (Rundenlimit)."))
    if l != GRUEN:
        todo.append(f"{l} **Festgefahrene Partien:** Bots erreichen oft das Rundenlimit. "
                    "Vermutlich lohnt sich Bauen oder Kaufen nicht mehr genug.")

    if basis:
        d = r - basis["runden_mittel"]
        if l_runden == GRUEN and abs(d) >= 1:
            todo.append(f"{INFO} **Spieldauer** hat sich spürbar verändert "
                        f"({f'{d:+.1f}'.replace('.', ',')} Runden). Noch im grünen Bereich, aber gut zu wissen.")
        if spielerzahl == 2:
            d = (gesamt["siegquote_position"][0] - basis["siegquote_position"][0]) * 100
            if zeilen_gesamt[1][0] == GRUEN and abs(d) >= 4:
                todo.append(f"{INFO} **Startposition:** Der Startspieler gewinnt {d:+.0f} Prozentpunkte "
                            "häufiger als vorher. Noch im grünen Bereich.")

    zeilen_gesamt.append((INFO, "Spannung", f"{prozent(gesamt['knapp_quote'])} knappe Partien",
                          (prozent(basis["knapp_quote"]) if basis else "–"), "–",
                          f"Anteil der Partien, die mit höchstens 3 Ruf Abstand entschieden werden "
                          f"(Ø Abstand {zahl(gesamt['abstand_mittel'])} Ruf)."))
    lichter += [z[0] for z in zeilen_gesamt]

    # Karten
    zeilen_karten = []
    for b in karten_berichte:
        c = karten.get(b["karte"], {})
        licht, text = karten_urteil(b, spielerzahl)
        lichter.append(licht)
        kosten = str(c.get("kosten", "–"))
        if kosten_erwartung and c.get("effekte"):
            try:
                soll = kosten_erwartung(c)
                kosten += f" (Faustformel ≈ {zahl(soll)})"
                if isinstance(c.get("kosten"), int) and abs(soll - c["kosten"]) > 2:
                    guenstig = c["kosten"] < soll
                    richtung = "günstig" if guenstig else "teuer"
                    q, (g_lo, g_hi) = b["siegquote"], fokus_grenzen(spielerzahl)[:2]
                    if g_lo <= q <= g_hi:
                        text += (f" Die Faustformel hält den Preis für zu {richtung}, "
                                 "in der Simulation fällt das aber nicht auf.")
                    elif (q > g_hi) == guenstig:
                        text += f" Die Faustformel sieht das auch so (Preis wirkt zu {richtung})."
                    else:
                        text += (f" Die Faustformel hält den Preis dagegen für zu {richtung}. "
                                 "Hier widersprechen sich beide, ein Spieltest klärt das am besten.")
            except Exception:  # noqa: BLE001
                pass
        alt = basis_berichte.get(b["karte"])
        if alt:
            vorher = veraenderung(b["siegquote"], alt["siegquote"], "pp", 1)
        elif basis is not None and b["karte"] not in basis_karten:
            vorher = "neu"
        else:
            vorher = "–"
        zeilen_karten.append((licht, c.get("name", b["karte"]), kosten,
                              f"{prozent(b['siegquote'])} ± {b['unsicherheit'] * 100:.0f}",
                              vorher, zahl(b["kaeufe"]), text))
        if licht != GRUEN:
            todo.append(f"{licht} **{c.get('name', b['karte'])}:** {text}")

    schlimmstes = max(lichter, key=RANG.get, default=GRUEN)
    if schlimmstes == INFO:
        schlimmstes = GRUEN
    titel, satz = GESAMT_TEXT[schlimmstes]

    z = ["## 🍺 Balance-Bericht (Simulation)", "",
         f"> ### {schlimmstes} {titel}", f"> {satz}", ""]

    # Was wurde geprüft?
    teile = [f"**{tausend(gesamt['spiele'])} simulierte Partien** mit {spielerzahl} Bots"]
    if basis is not None:
        teile.append(f"verglichen mit dem Stand von `{basis_name}` (Spalte „vorher“)")
    z.append("**Was wurde geprüft?** " + ", ".join(teile) + ".")
    if ziel:
        namen = [f"{karten.get(k, {}).get('name', k)} ({TYP_NAME.get(karten.get(k, {}).get('typ'), 'entfernt')})"
                 for k in ziel]
        z.append(f"Geänderte Karten in diesem PR: {', '.join(namen)}.")
    else:
        z.append("Dieser PR ändert keine Karten. Geprüft wurde nur, ob das Spiel als Ganzes rund läuft.")
    z.append("")

    if zeilen_karten:
        z += ["### 🎯 Die Karten aus diesem PR", "",
              "Ein Bot kauft die Karte bevorzugt, die anderen spielen normal. "
              f"**Fair wäre eine Siegquote um {prozent(1 / spielerzahl)}**, "
              f"grün ist alles zwischen {prozent(fokus_grenzen(spielerzahl)[0])} "
              f"und {prozent(fokus_grenzen(spielerzahl)[1])}.", "",
              "| | Karte | Kosten | Siegquote | vorher | Ø gekauft | Was heißt das? |",
              "|---|---|---|---|---|---|---|"]
        z += ["| " + " | ".join(zeile) + " |" for zeile in zeilen_karten]
        z.append("")
    nicht_markt = [k for k in ziel if karten.get(k, {}).get("typ") not in ("markt", None)]
    if nicht_markt:
        namen = ", ".join(karten[k].get("name", k) for k in nicht_markt)
        z += [f"_{namen}: Ausbauten, Anlässe und Startkarten lassen sich nicht einzeln im Duell testen. "
              "Ihre Wirkung steckt in den Werten zum Gesamtspiel unten"
              + (" (achte auf die Spalte „vorher“)." if basis is not None else ".") + "_", ""]

    z += ["### 📊 Das Spiel als Ganzes", "",
          "| | Kennzahl | Jetzt | vorher | Ziel | Was heißt das? |",
          "|---|---|---|---|---|---|"]
    z += ["| " + " | ".join(zeile) + " |" for zeile in zeilen_gesamt]
    z.append("")

    z += ["### 💡 Was jetzt?", ""]
    todo.sort(key=lambda t: -RANG.get(t.split(" ", 1)[0], 0))
    if any(not t.startswith(INFO) for t in todo):
        z += [f"- {t}" for t in todo]
    elif todo:
        z += ["- ✅ Aus Sicht der Simulation gibt es nichts zu tun."] + [f"- {t}" for t in todo]
    else:
        z.append("- ✅ Aus Sicht der Simulation gibt es nichts zu tun.")
    z += [f"- ⚠️ {w}" for w in warnungen]
    z.append("- 🎲 Die Bots sind einfach gestrickt. Ein echter Spieltest am Tisch ist immer besser: "
             "Ergebnis gern als Spieltest-Issue melden.")
    z.append("")

    # Erklärung für Neulinge
    g = fokus_grenzen(spielerzahl)
    z += ["<details><summary>📖 <b>Wie lese ich diesen Bericht?</b></summary>", "",
          "**Die Ampel**",
          "- 🟢 im Zielbereich, alles gut",
          "- 🟡 knapp daneben: anschauen, oft reicht ein Spieltest",
          "- 🔴 deutlich daneben: die Änderung sollte vermutlich angepasst werden",
          "- ℹ️ nur zur Information, ohne Bewertung",
          "",
          "Keine Ampel blockiert den PR. Die Entscheidung treffen Menschen.",
          "",
          "**Die Begriffe**",
          "- **Bots:** Computer-Spieler, die nach einfachen Regeln Karten kaufen und bauen. "
          "Sie spielen tausende Partien in wenigen Sekunden.",
          "- **Siegquote (Fokus-Duell):** Ein Bot kauft die neue Karte bevorzugt (bis zu 3 Stück), "
          "die anderen spielen ganz normal. Gewinnt der Fokus-Bot viel öfter als fair, "
          "ist die Karte zu stark. Gewinnt er viel seltener, ist sie zu schwach. "
          f"Grün: {prozent(g[0])}–{prozent(g[1])}, gelb: {prozent(g[2])}–{prozent(g[3])}.",
          "- **± Zahl:** die Messungenauigkeit. Bei „48 % ± 4“ liegt der wahre Wert ziemlich sicher "
          "zwischen 44 % und 52 %.",
          "- **vorher:** derselbe Wert mit den Karten vor diesem PR. „+5 Pkt.“ heißt: "
          "5 Prozentpunkte mehr als vorher. „neu“ heißt: Die Karte gab es vorher nicht.",
          "- **Ø gekauft:** wie viele Exemplare der Fokus-Bot pro Partie im Schnitt kauft. "
          "Sehr niedrige Werte heißen: Die Karte war meist zu teuer oder nicht attraktiv.",
          "- **Faustformel:** ein Richtwert für die Kosten, berechnet aus den Effekten der Karte "
          "(siehe `docs/BALANCE.md`). Weichen Kosten und Faustformel um mehr als 2 ab, lohnt ein Blick.",
          "- **Fairness der Startposition:** Wie oft gewinnt, wer die Partie beginnt? Fair ist ungefähr die Hälfte.",
          "- **Festgefahrene Partien:** Partien, die nach "
          f"{PARAMETER['max_runden']} Runden abgebrochen werden, weil keiner das Ende auslöst.",
          "",
          "</details>", ""]

    # Details
    p10, p90 = gesamt["runden_p10_p90"]
    mn, mx = gesamt["runden_min_max"]
    z += ["<details><summary>🔬 <b>Details für Tüftler</b></summary>", "",
          f"- Spieldauer: Ø {zahl(gesamt['runden_mittel'])} Runden, 80 % der Partien zwischen "
          f"{p10} und {p90} (kürzeste {mn}, längste {mx})",
          f"- Ruf: Ø {zahl(gesamt['punkte_mittel'])} je Spieler, Ø {zahl(gesamt['sieger_punkte_mittel'])} beim Sieger",
          "- Siege nach Startposition: " + " / ".join(prozent(x) for x in gesamt["siegquote_position"]),
          "- Wie Partien enden: " + ", ".join(
              f"{ENDE_NAME.get(k, k)} {zahl(v * 100)} %"
              for k, v in sorted(gesamt["spielende"].items(), key=lambda kv: -kv[1])),
          "- Meistgekaufte Marktkarten (Ø pro Partie, alle Bots): " + ", ".join(
              f"{karten.get(k, {}).get('name', k)} {zahl(v)}" for k, v in gesamt["meistgekauft"]),
          ]
    for b in karten_berichte:
        alt = basis_berichte.get(b["karte"])
        if alt:
            z.append(f"- {karten.get(b['karte'], {}).get('name', b['karte'])} vorher: "
                     f"Siegquote {prozent(alt['siegquote'])}, Ø gekauft {zahl(alt['kaeufe'])}")
    if karten_berichte:
        z.append(f"- Fokus-Duell: {tausend(karten_berichte[0]['partien'])} Partien je Karte, Sitzplätze wechseln")
    z += ["- Grenzwerte und Methode: `tools/simulieren.py` und `docs/BALANCE.md`", "", "</details>", ""]

    z.append("_Die Simulation ersetzt keinen echten Spieltest. Sie zeigt nur grobe Ausreißer._")
    return "\n".join(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--partien", type=int, default=2000)
    ap.add_argument("--spieler", type=int, default=2)
    ap.add_argument("--pakete", default="basis", help="kommagetrennt, z. B. basis,heuriger")
    ap.add_argument("--karten", default="", help="kommagetrennte Karten-IDs")
    ap.add_argument("--geaendert", default="", help="Git-Basis, z. B. origin/main")
    ap.add_argument("--ohne-vergleich", action="store_true", help="Basis nicht zusätzlich simulieren")
    ap.add_argument("--alle-karten", action="store_true")
    ap.add_argument("--markdown", default="")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

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

    n_duell = max(400, args.partien // 3)
    ergebnisse = spiele(karten, args.partien, args.spieler, seed=args.seed)
    gesamt = gesamtbericht(ergebnisse, args.spieler, karten)
    berichte = [kartenbericht(karten, kid, n=n_duell, spielerzahl=args.spieler, seed=args.seed + 7)
                for kid in markt_ziel]

    # Vergleich mit der Basis (gleiche Engine, gleiche Zufallszahlen)
    basis = None
    basis_karten = {}
    basis_berichte = {}
    if args.geaendert and not args.ohne_vergleich:
        with tempfile.TemporaryDirectory() as tmp:
            bp = basis_pakete(args.geaendert, Path(tmp))
            if bp is not None:
                basis_karten = alle_karten(bp, [p for p in aktiv if p in bp])
                try:
                    basis = gesamtbericht(spiele(basis_karten, args.partien, args.spieler, seed=args.seed),
                                          args.spieler, basis_karten)
                    for kid in markt_ziel:
                        if basis_karten.get(kid, {}).get("typ") == "markt":
                            basis_berichte[kid] = kartenbericht(basis_karten, kid, n=n_duell,
                                                                spielerzahl=args.spieler, seed=args.seed + 7)
                except Exception as e:  # noqa: BLE001 - z. B. alte Karten passen nicht zur neuen Engine
                    print(f"Hinweis: Basis-Simulation fehlgeschlagen ({e})", file=sys.stderr)
                    basis, basis_berichte = None, {}

    warnungen = []
    entfernt = [k for k in ziel if k not in karten]
    if entfernt:
        warnungen.append("Entfernte Karten: " + ", ".join(entfernt))

    md = markdown(gesamt, berichte, karten, warnungen, spielerzahl=args.spieler, ziel=ziel,
                  basis=basis, basis_name=args.geaendert.removeprefix("origin/"), basis_karten=basis_karten,
                  basis_berichte=basis_berichte)
    print(md)
    if args.markdown:
        Path(args.markdown).write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
