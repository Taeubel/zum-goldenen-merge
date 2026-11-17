"""Regel-Engine für „Zum Goldenen Merge“. Setzt REGELN.md 1:1 um."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import effekte as fx

# Zentrale Spielparameter – Änderungen nur per RFC (siehe GOVERNANCE.md)
PARAMETER = {
    "handgroesse": 5,
    "markt_stapel": 10,
    "kopien_je_stapel": {1: 10, 2: 10, 3: 10, 4: 12},
    "ausbauten_im_spiel": {1: 14, 2: 14, 3: 18, 4: 20},
    "ausbau_auslage": 4,
    "leere_stapel_fuer_ende": 3,
    "spende_kosten": 3,       # Spenden an den Musikverein: Geld -> 1 Ruf
    "spende_max": 99,         # praktisch unbegrenzt
    "handwerker_geld": 3,     # fehlende Arbeit beim Bauen: je 3 Geld
    "max_runden": 30,         # Sicherheitsnetz für die Simulation
    "startbonus_ruf": [0, 2, 2, 3],  # Ausgleich für spätere Startpositionen
}


@dataclass
class Spieler:
    name: str
    bot: object
    nachzieh: list = field(default_factory=list)
    ablage: list = field(default_factory=list)
    hand: list = field(default_factory=list)
    gespielt: list = field(default_factory=list)
    ausbauten: list = field(default_factory=list)
    ruf: int = 0
    geld: int = 0
    arbeit: int = 0
    kaeufe: int = 0
    ablegen_offen: int = 0
    spaete_effekte: list = field(default_factory=list)
    gekauft: list = field(default_factory=list)  # Statistik
    entsorgt: int = 0

    def alle_karten(self):
        return self.nachzieh + self.ablage + self.hand + self.gespielt


class Spiel:
    def __init__(self, karten: dict, bots: list, seed: int = 0, markt: list[str] | None = None,
                 parameter: dict | None = None):
        self.rng = random.Random(seed)
        self.k = karten
        self.p = {**PARAMETER, **(parameter or {})}
        n = len(bots)
        self.spieler = [Spieler(f"S{i+1}", b) for i, b in enumerate(bots)]
        pool = sorted(i for i, c in karten.items() if c["typ"] == "markt")
        if markt is None:
            markt = self.rng.sample(pool, min(self.p["markt_stapel"], len(pool)))
        kopien = self.p["kopien_je_stapel"][n]
        self.markt = {m: kopien for m in markt}
        aus_pool = sorted(i for i, c in karten.items() if c["typ"] == "ausbau")
        anzahl = min(self.p["ausbauten_im_spiel"][n], len(aus_pool))
        self.ausbau_stapel = self.rng.sample(aus_pool, anzahl)
        self.auslage = [self.ausbau_stapel.pop() for _ in range(min(self.p["ausbau_auslage"], len(self.ausbau_stapel)))]
        self.anlass_pool = sorted(i for i, c in karten.items() if c["typ"] == "anlass")
        self.anlass_stapel = []
        self.anlass = None
        self.runde = 0
        self.ende_ausgeloest = None
        start = [i for i, c in karten.items() if c["typ"] == "start" for _ in range(c.get("anzahl", 1))]
        for idx, sp in enumerate(self.spieler):
            sp.nachzieh = list(start)
            self.rng.shuffle(sp.nachzieh)
            sp.ruf = self.p["startbonus_ruf"][idx] if idx < len(self.p["startbonus_ruf"]) else 0
            self.ziehen(sp, self.p["handgroesse"])

    # --- Hilfen ---------------------------------------------------------------
    def ziehen(self, sp: Spieler, n: int):
        for _ in range(n):
            if not sp.nachzieh:
                if not sp.ablage:
                    return
                sp.nachzieh, sp.ablage = sp.ablage, []
                self.rng.shuffle(sp.nachzieh)
            sp.hand.append(sp.nachzieh.pop())

    def entsorgen(self, sp: Spieler, n: int):
        for kid in sp.bot.waehle_entsorgen(self, sp, n):
            sp.hand.remove(kid)
            sp.entsorgt += 1

    def nehmen(self, sp: Spieler, max_kosten: int):
        wahl = sp.bot.waehle_kauf(self, sp, max_kosten, gratis=True)
        if wahl:
            self.markt[wahl] -= 1
            sp.ablage.append(wahl)
            sp.gekauft.append(wahl)

    def tags(self, kid):
        return self.k[kid].get("tags", [])

    def ausbau_kosten(self, aid):
        rabatt = (self.k[self.anlass].get("bau_rabatt", 0) if self.anlass else 0)
        return max(0, self.k[aid]["kosten"] - rabatt)

    def baukraft(self, sp):
        return sp.arbeit + sp.geld // self.p["handwerker_geld"]

    def kaufbar(self, max_kosten):
        return [m for m, n in self.markt.items() if n > 0 and self.k[m]["kosten"] <= max_kosten]

    def leere_stapel(self):
        return sum(1 for n in self.markt.values() if n == 0)

    # --- Ablauf ---------------------------------------------------------------
    def neue_runde(self):
        self.runde += 1
        if not self.anlass_stapel:
            self.anlass_stapel = list(self.anlass_pool)
            self.rng.shuffle(self.anlass_stapel)
        self.anlass = self.anlass_stapel.pop() if self.anlass_stapel else None

    def zug(self, sp: Spieler):
        self.spieler_am_zug = sp
        a = self.k[self.anlass] if self.anlass else {}
        # 1. Zugbeginn: Ablegen (Grantler, Föhnsturm, Krampuslauf)
        ablegen = sp.ablegen_offen + a.get("ablegen", 0)
        if a.get("fuehrender_ablegen"):
            fuehrend = max(s.ruf for s in self.spieler)
            if sp.ruf == fuehrend and sp.ruf > 0:
                ablegen += a["fuehrender_ablegen"]
        sp.ablegen_offen = 0
        for kid in sp.bot.waehle_ablegen(self, sp, min(ablegen, len(sp.hand))):
            sp.hand.remove(kid)
            sp.ablage.append(kid)
        sp.kaeufe = 1
        # 2. Anlass und Ausbauten
        fx.anwenden(self, sp, a.get("fuer_alle", []), self.anlass)
        for aid in sp.ausbauten:
            fx.anwenden(self, sp, self.k[aid].get("jede_runde", []), aid)
        # 3. Ausspielen (alle Handkarten, Reihenfolge wählt der Spieler)
        while sp.hand:
            kid = sp.bot.waehle_ausspielen(self, sp)
            sp.hand.remove(kid)
            sp.gespielt.append(kid)
            fx.anwenden(self, sp, self.k[kid].get("effekte", []), kid)
            tb = a.get("tag_bonus")
            if tb and tb["tag"] in self.tags(kid):
                fx.anwenden(self, sp, tb["effekte"], self.anlass)
        # 4. Kombos (reihenfolgeunabhängig, zählt nur ANDERE gespielte Karten)
        for i, kid in enumerate(sp.gespielt):
            kombo = self.k[kid].get("kombo")
            if not kombo:
                continue
            andere = sum(1 for j, o in enumerate(sp.gespielt) if j != i and kombo["tag"] in self.tags(o))
            if andere >= kombo["mindestens"]:
                fx.anwenden(self, sp, kombo["effekte"], kid)
        for art, obj, quelle in sp.spaete_effekte:
            if art == "je_tag":
                anzahl = sum(1 for o in sp.gespielt if obj["tag"] in self.tags(o))
                for _ in range(anzahl):
                    fx.anwenden(self, sp, obj["effekte"], quelle)
        sp.spaete_effekte = []
        # 5. Bauen (max. 1 Ausbau). Fehlende Arbeit: je 2 Geld ("Handwerker")
        if not a.get("kein_bau"):
            wahl = sp.bot.waehle_ausbau(self, sp)
            if wahl:
                kosten = self.ausbau_kosten(wahl)
                aus_arbeit = min(sp.arbeit, kosten)
                sp.arbeit -= aus_arbeit
                sp.geld -= (kosten - aus_arbeit) * self.p["handwerker_geld"]
                self.auslage.remove(wahl)
                sp.ausbauten.append(wahl)
                fx.anwenden(self, sp, self.k[wahl].get("beim_bau", []), wahl)
                if self.ausbau_stapel:
                    self.auslage.append(self.ausbau_stapel.pop())
                elif self.ende_ausgeloest is None:
                    self.ende_ausgeloest = "ausbauten"
        # 6. Kaufen
        while sp.kaeufe > 0:
            wahl = sp.bot.waehle_kauf(self, sp, sp.geld)
            if not wahl:
                break
            sp.geld -= self.k[wahl]["kosten"]
            self.markt[wahl] -= 1
            sp.ablage.append(wahl)
            sp.gekauft.append(wahl)
            sp.kaeufe -= 1
        # 7. Spenden: je X Geld -> 1 Ruf (max. "spende_max" pro Zug)
        gespendet = 0
        while (sp.geld >= self.p["spende_kosten"] and gespendet < self.p["spende_max"]
               and sp.bot.will_spenden(self, sp)):
            sp.geld -= self.p["spende_kosten"]
            sp.ruf += 1
            gespendet += 1
        if self.leere_stapel() >= self.p["leere_stapel_fuer_ende"] and self.ende_ausgeloest is None:
            self.ende_ausgeloest = "markt"
        # 8. Aufräumen
        sp.ablage += sp.gespielt + sp.hand
        sp.gespielt, sp.hand = [], []
        sp.geld = sp.arbeit = sp.kaeufe = 0
        self.ziehen(sp, self.p["handgroesse"])

    def wertung(self, sp: Spieler) -> int:
        punkte = sp.ruf
        karten = sp.alle_karten()
        for aid in sp.ausbauten:
            a = self.k[aid]
            punkte += a.get("ruf", 0)
            ew = a.get("endwertung")
            if ew:
                anzahl = sum(1 for c in karten if ew["tag"] in self.tags(c))
                punkte += (anzahl // ew["je"]) * ew["ruf"]
        return punkte

    def spielen(self) -> dict:
        while self.ende_ausgeloest is None and self.runde < self.p["max_runden"]:
            self.neue_runde()
            for sp in self.spieler:
                self.zug(sp)  # Runde wird immer zu Ende gespielt
        punkte = [self.wertung(s) for s in self.spieler]
        # Gleichstand: mehr Ausbauten, dann spätere Startposition
        rang = max(range(len(self.spieler)),
                   key=lambda i: (punkte[i], len(self.spieler[i].ausbauten), i))
        return {
            "punkte": punkte,
            "sieger": rang,
            "runden": self.runde,
            "ende": self.ende_ausgeloest or "limit",
            "gekauft": [s.gekauft for s in self.spieler],
            "markt": list(self.markt),
        }
