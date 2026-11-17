"""Simulations-Spieler ("Vibe-Gaming"-Bots).

Die Bots sind bewusst einfach und regelbasiert: Sie sollen nicht perfekt spielen,
sondern grobe Ausreißer in der Balance sichtbar machen.
"""
from __future__ import annotations

from . import effekte as fx

STARTKARTEN = {"trinkgeld", "lehrling"}


class Bot:
    name = "basis"

    def __init__(self, rng, zufall: float = 0.1):
        self.rng = rng
        self.zufall = zufall

    # -- Bewertung --------------------------------------------------------------
    def spaetphase(self, spiel) -> float:
        """0 = Spielbeginn, 1 = Spielende naht."""
        gesamt = spiel.p["ausbauten_im_spiel"][len(spiel.spieler)]
        verbleibend = len(spiel.ausbau_stapel) + len(spiel.auslage)
        leer = spiel.leere_stapel() / spiel.p["leere_stapel_fuer_ende"]
        return max(1 - verbleibend / max(gesamt, 1), leer)

    def kartenwert(self, spiel, kid) -> float:
        c = spiel.k[kid]
        w = fx.wert_fuer(c.get("effekte", []))
        k = c.get("kombo")
        if k:
            w += 0.5 * fx.wert_fuer(k["effekte"])
        # Ruf-Effekte werden gegen Spielende wichtiger, Wirtschaft unwichtiger
        s = self.spaetphase(spiel)
        ruf = sum(e.get("ruf", 0) for e in c.get("effekte", []))
        return w * (1 - 0.5 * s) + ruf * 1.5 * s

    def ausbauwert(self, spiel, sp, aid) -> float:
        a = spiel.k[aid]
        rest = max(1.0, 12 * (1 - self.spaetphase(spiel)))
        w = a.get("ruf", 0)
        w += 0.35 * rest * fx.wert_fuer(a.get("jede_runde", []))
        w += fx.wert_fuer(a.get("beim_bau", []))
        ew = a.get("endwertung")
        if ew:
            anzahl = sum(1 for c in sp.alle_karten() if ew["tag"] in spiel.tags(c))
            w += (anzahl // ew["je"]) * ew["ruf"] + 0.5
        return w

    # -- Entscheidungen -----------------------------------------------------------
    def waehle_ausspielen(self, spiel, sp):
        def prio(kid):
            effekte = [list(e)[0] for e in spiel.k[kid].get("effekte", [])]
            if "entsorgen" in effekte:
                return 0
            if "ziehen" in effekte:
                return 1
            return 2
        return min(sp.hand, key=prio)

    def waehle_entsorgen(self, spiel, sp, n):
        kandidaten = [k for k in sp.hand if k in STARTKARTEN]
        groesse = len(sp.alle_karten())
        wahl = []
        for kid in sorted(kandidaten, key=lambda k: k != "lehrling"):
            if len(wahl) >= n or groesse - len(wahl) <= 8 or self.spaetphase(spiel) > 0.6:
                break
            wahl.append(kid)
        return wahl

    def waehle_ablegen(self, spiel, sp, n):
        return sorted(sp.hand, key=lambda k: self.kartenwert(spiel, k))[:n]

    def erwartete_einsaetze(self, spiel, sp) -> float:
        """Wie oft wird eine neu gekaufte Karte bis Spielende noch gespielt?"""
        rest_runden = max(0.5, 14 * (1 - self.spaetphase(spiel)))
        return rest_runden * spiel.p["handgroesse"] / max(5, len(sp.alle_karten()) + 1)

    def spendenwert(self, spiel, geld) -> float:
        return 1.5 * min(geld // spiel.p["spende_kosten"], spiel.p["spende_max"])

    def waehle_kauf(self, spiel, sp, max_kosten, gratis=False):
        optionen = spiel.kaufbar(max_kosten)
        if not optionen:
            return None
        if self.rng.random() < self.zufall:
            return self.rng.choice(optionen)
        einsaetze = self.erwartete_einsaetze(spiel, sp)

        def gesamt(m):
            rest = 0 if gratis else max_kosten - spiel.k[m]["kosten"]
            # Verwässerung: schwache Karten verschlechtern das Deck
            netto = self.kartenwert(spiel, m) - 1.2
            return netto * einsaetze + self.spendenwert(spiel, rest)

        beste = max(optionen, key=lambda m: (gesamt(m), -spiel.k[m]["kosten"]))
        if not gratis and gesamt(beste) <= self.spendenwert(spiel, max_kosten):
            return None
        return beste

    def will_spenden(self, spiel, sp):
        return True

    def waehle_ausbau(self, spiel, sp):
        optionen = [a for a in spiel.auslage if spiel.ausbau_kosten(a) <= spiel.baukraft(sp)]
        if not optionen:
            return None
        if self.rng.random() < self.zufall:
            return self.rng.choice(optionen)
        beste = max(optionen, key=lambda a: self.ausbauwert(spiel, sp, a))
        # Geld für Handwerker nur ausgeben, wenn sich der Ausbau lohnt
        geld_noetig = max(0, spiel.ausbau_kosten(beste) - sp.arbeit) * spiel.p["handwerker_geld"]
        if geld_noetig and self.ausbauwert(spiel, sp, beste) < self.spendenwert(spiel, geld_noetig):
            return None
        return beste


class Gierig(Bot):
    """Kauft die stärkste bezahlbare Karte, baut den wertvollsten Ausbau."""
    name = "gierig"


class Geldsack(Bot):
    """Kauft nur Geld-Karten und Ruf – die klassische 'Big Money'-Referenz."""
    name = "geldsack"

    def kartenwert(self, spiel, kid):
        c = spiel.k[kid]
        return sum(e.get("geld", 0) + 1.2 * e.get("ruf", 0) for e in c.get("effekte", []))

    def waehle_kauf(self, spiel, sp, max_kosten, gratis=False):
        optionen = spiel.kaufbar(max_kosten)
        if not optionen:
            return None
        beste = max(optionen, key=lambda m: self.kartenwert(spiel, m))
        return beste if self.kartenwert(spiel, beste) >= 1.5 or gratis else None


class Fokus(Gierig):
    """Wie 'gierig', bevorzugt aber eine bestimmte Karte.

    Die Karte bekommt +1,5 Bewertungsbonus, solange der Bot weniger als 3 besitzt.
    Spielt Fokus(X) gegen Gierig deutlich über 50 %, ist X vermutlich zu stark;
    deutlich darunter, ist X zu schwach.
    """
    name = "fokus"

    def __init__(self, rng, karte: str, zufall: float = 0.1):
        super().__init__(rng, zufall)
        self.karte = karte

    def kartenwert(self, spiel, kid):
        w = super().kartenwert(spiel, kid)
        if kid == self.karte:
            besitz = sum(1 for c in spiel.spieler_am_zug.alle_karten() if c == kid)
            if besitz < 3:
                w += 1.5
        return w


class Zufall(Bot):
    name = "zufall"

    def __init__(self, rng, zufall=1.0):
        super().__init__(rng, zufall=1.0)


BOTS = {b.name: b for b in (Gierig, Geldsack, Zufall)}
