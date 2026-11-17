"""Registry aller Spielmechaniken (Effekt-Primitive).

Jede Mechanik ist genau eine Funktion mit dem Dekorator ``@effekt``.
Eine neue Mechanik braucht:
  1. eine Funktion hier (Spielwirkung im Simulator),
  2. einen Regeltext (``text``) – daraus werden die Kartentexte generiert,
  3. einen Wert (``wert``) – grobe Stärke für den Kosten-Check,
  4. einen Eintrag in REGELN.md und einen Test in tests/.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

TAGS = {"geld", "personal", "gast", "speise", "getraenk"}
REGIONEN = {"alle", "wien", "niederoesterreich", "oberoesterreich", "salzburg", "tirol",
            "vorarlberg", "kaernten", "steiermark", "burgenland"}


@dataclass
class Mechanik:
    name: str
    fn: Callable[..., None]
    text: Callable[[Any], str]
    wert: Callable[[Any], float]
    param: str  # "int" oder "objekt"


MECHANIKEN: dict[str, Mechanik] = {}


def effekt(name: str, text: Callable[[Any], str], wert: Callable[[Any], float], param: str = "int"):
    def deco(fn):
        MECHANIKEN[name] = Mechanik(name, fn, text, wert, param)
        return fn
    return deco


def anwenden(spiel, spieler, effekte: list[dict], quelle=None) -> None:
    for e in effekte or []:
        (name, wert), = e.items()
        MECHANIKEN[name].fn(spiel, spieler, wert, quelle)


def text_fuer(effekte: list[dict]) -> str:
    teile = []
    for e in effekte or []:
        (name, wert), = e.items()
        teile.append(MECHANIKEN[name].text(wert))
    return ", ".join(teile)


def wert_fuer(effekte: list[dict]) -> float:
    s = 0.0
    for e in effekte or []:
        (name, wert), = e.items()
        s += MECHANIKEN[name].wert(wert)
    return s


# --- Grundspiel -------------------------------------------------------------

@effekt("geld", text=lambda n: f"+{n} Geld", wert=lambda n: 1.0 * n)
def _geld(spiel, sp, n, q):
    sp.geld += n


@effekt("arbeit", text=lambda n: f"+{n} Arbeit", wert=lambda n: 1.0 * n)
def _arbeit(spiel, sp, n, q):
    sp.arbeit += n


@effekt("ruf", text=lambda n: f"+{n} Ruf", wert=lambda n: 1.5 * n)
def _ruf(spiel, sp, n, q):
    sp.ruf += n


@effekt("ziehen", text=lambda n: f"ziehe {n} Karte{'n' if n != 1 else ''}", wert=lambda n: 1.0 * n)
def _ziehen(spiel, sp, n, q):
    spiel.ziehen(sp, n)


@effekt("kaufen", text=lambda n: f"+{n} Kauf", wert=lambda n: 0.5 * n)
def _kaufen(spiel, sp, n, q):
    sp.kaeufe += n


@effekt("entsorgen", text=lambda n: f"entsorge bis zu {n} Karte{'n' if n != 1 else ''} aus deiner Hand",
        wert=lambda n: 0.6 * n)
def _entsorgen(spiel, sp, n, q):
    spiel.entsorgen(sp, n)


@effekt("nehmen", text=lambda n: f"nimm eine Marktkarte mit Kosten bis {n} (gratis)",
        wert=lambda n: 0.5 * n)
def _nehmen(spiel, sp, n, q):
    spiel.nehmen(sp, n)


@effekt("gegner_ablegen",
        text=lambda n: f"alle anderen legen zu Beginn ihres nächsten Zugs {n} Handkarte{'n' if n != 1 else ''} ab",
        wert=lambda n: 0.7 * n)
def _gegner_ablegen(spiel, sp, n, q):
    for andere in spiel.spieler:
        if andere is not sp:
            andere.ablegen_offen += n


# --- Erweiterung „Beim Heurigen“ -------------------------------------------

@effekt("je_tag", param="objekt",
        text=lambda o: f"je gespielter Karte mit „{o['tag']}“ (inkl. dieser): {text_fuer(o['effekte'])}",
        wert=lambda o: 2.5 * wert_fuer(o["effekte"]))
def _je_tag(spiel, sp, o, q):
    # wird erst in der Kombo-Phase abgerechnet (reihenfolgeunabhängig)
    sp.spaete_effekte.append(("je_tag", o, q))
