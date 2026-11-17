"""Stimmen vom Stammtisch: erfundene Figuren kommentieren den Balance-Bericht.

Jede Figur schaut auf andere Zahlen der Simulation und beschreibt in ein paar Sätzen,
wie sie die Änderung findet. Die Texte entstehen nach festen Regeln aus den Zahlen
(kein Zufall, keine KI): gleicher Stand, gleicher Text.

Neue Figur? Funktion `def name(k: Kontext) -> dict` schreiben und in FIGUREN eintragen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DAFUER, NAJA, DAGEGEN = "👍 gefällt mir", "🤷 geht so", "👎 gefällt mir nicht"


def _p(x):
    return f"{x * 100:.0f}"


def _z(x):
    return f"{x:.1f}".replace(".", ",")


def _liste(woerter):
    woerter = list(woerter)
    return woerter[0] if len(woerter) == 1 else ", ".join(woerter[:-1]) + " und " + woerter[-1]


def _zahlwort(n):
    return {2: "zu zweit", 3: "zu dritt", 4: "zu viert", 5: "zu fünft"}.get(n, f"mit {n} Leuten")


@dataclass
class Kontext:
    ergebnis: dict
    karten: dict
    ziel: list
    basis_karten: dict
    gesamt: str
    kosten: object  # Funktion (karte, bericht, spielerzahl) -> Faustformel-Preis oder None
    zahlen: list = field(init=False)
    haupt: int = field(init=False)

    def __post_init__(self):
        self.zahlen = sorted(self.ergebnis)
        self.haupt = 2 if 2 in self.ergebnis else self.zahlen[0]

    @property
    def markt(self):
        return [k for k in self.ziel if self.karten.get(k, {}).get("typ") == "markt"]

    @property
    def mit_basis(self):
        return any(r["basis"] for r in self.ergebnis.values())

    def name(self, kid):
        return self.karten.get(kid, {}).get("name", kid)


def _gruen(licht):
    return licht == "🟢"


# -- Figuren -------------------------------------------------------------------------

def resi(k: Kontext) -> dict:
    """Wirtin, spielt am liebsten in großer Runde: Spieldauer und Spannung."""
    n = max(k.zahlen)
    r = k.ergebnis[n]
    g, b, a = r["gesamt"], r["basis"], r["ampeln"]
    dauer = g["runden_mittel"]
    s = []
    if _gruen(a["runden"]):
        s.append(f"Bei mir sitzen meistens {n} Leute am Tisch, und mit Ø {_z(dauer)} Runden "
                 "ist eine Partie gut an einem Abend zu schaffen.")
    elif dauer < 10:
        s.append(f"{_zahlwort(n).capitalize()} ist nach Ø {_z(dauer)} Runden schon Schluss. "
                 "Da hat man sich grad eingespielt und muss schon zahlen.")
    else:
        s.append(f"{_zahlwort(n).capitalize()} dauert eine Partie Ø {_z(dauer)} Runden, da wird die Küche kalt.")
    if b and abs(dauer - b["runden_mittel"]) >= 0.5:
        d = dauer - b["runden_mittel"]
        s.append(f"Das sind {_z(abs(d))} Runden {'weniger' if d < 0 else 'mehr'} als vorher"
                 + (", das passt mir." if _gruen(a["runden"]) else ", und das merkt man."))
    kq = g["knapp_quote"]
    if kq >= 0.4:
        s.append(f"Schön ist, dass {_p(kq)} von 100 Partien bis zum Schluss knapp bleiben. "
                 "Da schaut keiner aufs Handy.")
    elif kq >= 0.3:
        s.append(f"Knapp wird's in {_p(kq)} von 100 Partien, das ist in Ordnung.")
    else:
        s.append(f"Nur {_p(kq)} von 100 Partien bleiben knapp, oft steht der Sieger früh fest. Das mag ich nicht.")
    if b and abs(kq - b["knapp_quote"]) >= 0.05:
        s.append("Spannender als vorher, sehr gut." if kq > b["knapp_quote"]
                 else "Vorher war's spannender, schade.")
    if not _gruen(a["limit"]):
        s.append("Dass manche Partie gar nicht aufhört, geht gar nicht. Irgendwann ist Sperrstunde.")
    schlecht = (not _gruen(a["runden"])) + (not _gruen(a["limit"])) + (kq < 0.3)
    return {"emoji": "🍺", "name": "Resi", "rolle": "Wirtin, spielt am liebsten in großer Runde",
            "daumen": DAFUER if schlecht == 0 else NAJA if schlecht == 1 else DAGEGEN, "text": " ".join(s)}


def ferdl(k: Kontext) -> dict:
    """Optimierer: sucht die stärkste Karte und reizt sie aus."""
    rolle = "Optimierer, sucht immer die stärkste Karte"
    if not k.markt:
        g = k.ergebnis[k.haupt]["gesamt"]
        lieblings = g["meistgekauft"][0] if g["meistgekauft"] else None
        s = "Nix Neues zum Ausreizen in diesem PR."
        if lieblings:
            s += (f" Ich bleib bei {k.name(lieblings[0])}, die kaufen die Bots eh am liebsten "
                  f"({_z(lieblings[1])} Stück pro Partie).")
        if k.ziel:
            s += " Ausbauten und Anlässe schau ich mir erst an, wenn sie am Tisch liegen."
        return {"emoji": "🧮", "name": "Ferdl", "rolle": rolle, "daumen": NAJA, "text": s}
    s = []
    stark = schwach = False
    for kid in k.markt:
        c = k.karten[kid]
        # die auffälligste Spielerzahl für diese Karte
        def abstand(n):
            b = k.ergebnis[n]["karten"][kid]
            return abs(b["siegquote"] - b["fair"])
        n = max(k.zahlen, key=lambda x: (abstand(x), x == k.haupt))
        r = k.ergebnis[n]
        b = r["karten"][kid]
        licht, _ = r["ampeln"]["karten"][kid]
        q, fair = round(b["siegquote"] * 100), round(b["fair"] * 100)
        wo = "" if len(k.zahlen) == 1 else f" {_zahlwort(n)}"
        if not _gruen(licht) and b["siegquote"] > b["fair"]:
            stark = True
            s.append(f"{k.name(kid)} hab ich{wo} sofort dreimal gekauft und damit {q} von 100 Partien gewonnen, "
                     f"fair wären {fair}. Mir taugt's, aber das macht dann jeder so.")
        elif not _gruen(licht):
            schwach = True
            s.append(f"{k.name(kid)} lass ich liegen. Wer{wo} drauf setzt, gewinnt nur {q} von 100 Partien, "
                     f"fair wären {fair}.")
        else:
            s.append(f"{k.name(kid)} ist ordentlich, aber kein Selbstläufer: Mit Fokus darauf gewinn ich{wo} "
                     f"{q} von 100 Partien, fair wären {fair}.")
        if b["kaeufe"] < 1:
            s.append(f"Die Bots kaufen sie aber kaum, im Schnitt {_z(b['kaeufe'])} Stück pro Partie.")
        soll = k.kosten(c, b, n)
        if soll is not None and isinstance(c.get("kosten"), int) and abs(soll - c["kosten"]) > 2:
            s.append(f"Für {c['kosten']} Geld kriegt man Effekte, die laut Faustformel eher {_z(soll)} wert sind.")
        alt = r["basis_karten"].get(kid)
        if alt and abs(alt["siegquote"] - b["siegquote"]) >= 0.03:
            s.append(f"Vorher waren's {_p(alt['siegquote'])} von 100.")
    daumen = DAGEGEN if (stark or schwach) else DAFUER
    if stark and not schwach:
        daumen = "😈 für mich super, fürs Spiel nicht"
    return {"emoji": "🧮", "name": "Ferdl", "rolle": rolle, "daumen": daumen, "text": " ".join(s)}


def brandl(k: Kontext) -> dict:
    """Schiedsrichterin: Fairness der Sitzplätze bei jeder Spielerzahl."""
    s = ["Ich schau nur auf eins: Hat jeder Platz am Tisch die gleichen Chancen?"]
    teile = []
    for n in k.zahlen:
        q = k.ergebnis[n]["gesamt"]["siegquote_position"]
        if n == 2:
            teile.append(f"zu zweit gewinnt der Startspieler {_p(q[0])} von 100 Partien")
        else:
            verb = "liegen die Plätze bei" if len(teile) < 2 else "sind es"
            teile.append(f"{_zahlwort(n)} {verb} {' / '.join(_p(x) for x in q)} %")
    s.append(teile[0][0].upper() + teile[0][1:] + (", " + ", ".join(teile[1:]) if teile[1:] else "") + ".")
    probleme = []
    for n in k.zahlen:
        r = k.ergebnis[n]
        if not _gruen(r["ampeln"]["position"]):
            q = r["gesamt"]["siegquote_position"]
            fair = 1 / n
            i = max(range(n), key=lambda j: abs(q[j] - fair))
            probleme.append(f"{_zahlwort(n)} ist Platz {i + 1} mit {_p(q[i])} % klar "
                            f"{'im Vorteil' if q[i] > fair else 'benachteiligt'}")
    if probleme:
        s.append("Aber " + "; ".join(probleme) + ". Das gehört sich angeschaut.")
    else:
        s.append("Das ist alles im Rahmen dessen, was der Zufall hergibt. Keine Beanstandung.")
    verschoben = [n for n in k.zahlen if k.ergebnis[n]["basis"] and
                  abs(k.ergebnis[n]["gesamt"]["positions_abweichung"]
                      - k.ergebnis[n]["basis"]["positions_abweichung"]) >= 0.03]
    if verschoben:
        s.append("Gegenüber vorher hat sich " + " und ".join(_zahlwort(n) for n in verschoben)
                 + " etwas verschoben, das behalt ich im Auge.")
    return {"emoji": "⚖️", "name": "Frau Magister Brandl", "rolle": "Schiedsrichterin, achtet auf Fairness",
            "daumen": DAGEGEN if probleme else DAFUER, "text": " ".join(s)}


def lukas(k: Kontext) -> dict:
    """Neuling: versteht nicht jede Zahl, will wissen, ob es passt und ob es kompliziert wird."""
    s = []
    if k.gesamt == "🟢":
        s.append("Ich versteh nicht jede Zahl da unten, aber wenn überall Grün steht, bin ich beruhigt.")
    elif k.gesamt == "🟡":
        s.append("Ein paar gelbe Punkte sind dabei. Ich würd's einfach einmal am Tisch ausprobieren und schauen, "
                 "ob es sich komisch anfühlt.")
    else:
        s.append("Rot heißt für mich: Lieber noch nicht mergen, bis jemand draufgeschaut hat.")
    neu = [kid for kid in k.ziel if k.mit_basis and kid in k.karten and kid not in k.basis_karten]
    if not k.ziel:
        s.append("Neue Karten muss ich mir diesmal keine merken, sehr gut.")
    elif len(neu) >= 3:
        s.append(f"{len(neu)} neue Karten auf einmal sind aber viel zum Merken.")
    elif neu:
        s.append(f"Neu ist {_liste(k.name(x) for x in neu)}, das kann ich mir merken.")
    else:
        s.append(f"Geändert wurde {_liste(k.name(x) for x in k.ziel if x in k.karten)}, "
                 "da muss ich mir nur die neuen Werte merken.")
    kombi = [kid for kid in k.ziel if k.karten.get(kid, {}).get("kombo")]
    viel = [kid for kid in k.ziel if len(k.karten.get(kid, {}).get("effekte") or []) >= 3]
    if kombi:
        s.append(f"Bei {_liste(k.name(x) for x in kombi)} gibt's eine Kombo, "
                 "die muss man mir am Anfang erklären.")
    if viel:
        s.append(f"{_liste(k.name(x) for x in viel)} {'macht' if len(viel) == 1 else 'machen'} "
                 "ganz schön viel auf einmal.")
    daumen = DAFUER if k.gesamt == "🟢" else NAJA if k.gesamt == "🟡" else DAGEGEN
    return {"emoji": "🎲", "name": "Lukas", "rolle": "zum ersten Mal dabei", "daumen": daumen, "text": " ".join(s)}


def grantler(k: Kontext) -> dict:
    """Der Grantler: findet immer was, schaut auf die größte Veränderung zu vorher."""
    rolle = "Stammgast seit 1987, findet immer was"
    if not k.mit_basis:
        return {"emoji": "😤", "name": "Der Grantler", "rolle": rolle, "daumen": NAJA,
                "text": "Ohne Vergleich mit früher kann ich nicht einmal ordentlich granteln. "
                        "Passen tut's mir trotzdem nicht."}
    # Veränderungen sammeln, normiert auf „spürbar“
    kandidaten = []
    for n in k.zahlen:
        r = k.ergebnis[n]
        g, b = r["gesamt"], r["basis"]
        if not b:
            continue
        d = g["runden_mittel"] - b["runden_mittel"]
        kandidaten.append((abs(d) / 1.0, f"Partien {_zahlwort(n)} sind {_z(abs(d))} Runden "
                                         f"{'kürzer' if d < 0 else 'länger'}"))
        d = g["knapp_quote"] - b["knapp_quote"]
        kandidaten.append((abs(d) / 0.05, f"Partien {_zahlwort(n)} sind {'öfter' if d > 0 else 'seltener'} "
                                          f"knapp ({_p(abs(d))} von 100)"))
        for kid, bb in r["karten"].items():
            alt = r["basis_karten"].get(kid)
            if alt:
                d = bb["siegquote"] - alt["siegquote"]
                kandidaten.append((abs(d) / 0.04, f"{k.name(kid)} gewinnt {_zahlwort(n)} "
                                                  f"{_p(abs(d))} von 100 Partien {'mehr' if d > 0 else 'weniger'}"))
    neu = [kid for kid in k.markt if kid not in k.basis_karten]
    kandidaten.sort(key=lambda x: -x[0])
    spuerbar = [t for w, t in kandidaten if w >= 1][:2]
    s = []
    if neu:
        s.append(f"Schon wieder was Neues: {_liste(k.name(x) for x in neu)}. Früher hat's das auch nicht gebraucht.")
    if spuerbar:
        s.append("Früher war alles besser. " + _liste(spuerbar) + ".")
    elif not neu:
        s.append("Nix hat sich geändert, Spieldauer, Spannung, alles wie vorher. Wozu dann der ganze Aufwand?")
    if k.gesamt == "🟢":
        s.append("Aber gut, ich geb's zu: Kaputt ist nix.")
        daumen = "😒 brummt, nickt aber"
    else:
        s.append("Und diesmal hab ich sogar recht, schaut's euch die " +
                 ("roten" if k.gesamt == "🔴" else "gelben") + " Punkte an.")
        daumen = DAGEGEN
    return {"emoji": "😤", "name": "Der Grantler", "rolle": rolle, "daumen": daumen, "text": " ".join(s)}


FIGUREN = [resi, ferdl, brandl, lukas, grantler]


def stimmen(ergebnis, karten, *, ziel=None, basis_karten=None, gesamt="🟢", kosten=None):
    k = Kontext(ergebnis, karten, ziel or [], basis_karten or {}, gesamt, kosten or (lambda c, b, n: None))
    return [f(k) for f in FIGUREN]
