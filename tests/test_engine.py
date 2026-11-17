"""Grundlegende Regel- und Inhaltstests. Laufen bei jedem PR."""
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import effekte as fx  # noqa: E402
from engine.bots import BOTS, Fokus  # noqa: E402
from engine.inhalte import alle_karten, lade_pakete  # noqa: E402
from engine.spiel import Spiel  # noqa: E402
from tools.karten_bauen import kartentext  # noqa: E402

PAKETE = lade_pakete()
ALLE = alle_karten(PAKETE)


def bots(n, seed=0):
    return [BOTS["gierig"](random.Random(seed + i)) for i in range(n)]


def test_inhalte_sind_gueltig():
    r = subprocess.run([sys.executable, str(ROOT / "tools/pruefen.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("spieler", [2, 3, 4])
def test_partie_endet_und_karten_bleiben_erhalten(spieler):
    karten = alle_karten(PAKETE, ["basis"])
    s = Spiel(karten, bots(spieler), seed=42)
    vorher_markt = sum(s.markt.values())
    e = s.spielen()
    assert e["ende"] in {"ausbauten", "markt", "limit"}
    gekauft = sum(len(g) for g in e["gekauft"])
    assert sum(s.markt.values()) == vorher_markt - gekauft
    for sp in s.spieler:
        entsorgt = sp.entsorgt
        assert len(sp.alle_karten()) == 10 + len(sp.gekauft) - entsorgt


def test_gleicher_seed_gleiches_ergebnis():
    karten = alle_karten(PAKETE, ["basis"])
    a = Spiel(karten, bots(2, 1), seed=7).spielen()
    b = Spiel(karten, bots(2, 1), seed=7).spielen()
    assert a == b


@pytest.mark.parametrize("kid", sorted(k for k, c in ALLE.items() if c["typ"] == "markt"))
def test_jede_marktkarte_ist_spielbar(kid):
    karten = alle_karten(PAKETE, [ALLE[kid]["_paket"], "basis"])
    pool = sorted(k for k, c in karten.items() if c["typ"] == "markt" and k != kid)
    markt = [kid] + random.Random(1).sample(pool, 9)
    s = Spiel(karten, [Fokus(random.Random(1), kid), BOTS["gierig"](random.Random(2))], seed=3, markt=markt)
    s.spielen()


@pytest.mark.parametrize("kid", sorted(ALLE))
def test_jede_karte_hat_text(kid):
    k = ALLE[kid]
    if k["typ"] == "ausbau" and not any(f in k for f in ("jede_runde", "beim_bau", "endwertung")):
        return  # reiner Ruf-Ausbau: Wert steht in der Kostenzeile
    assert kartentext(k), f"{kid} erzeugt keinen Kartentext"


def test_jede_mechanik_wird_verwendet_oder_ist_dokumentiert():
    regeln = (ROOT / "REGELN.md").read_text(encoding="utf-8")
    for name in fx.MECHANIKEN:
        assert f"`{name}`" in regeln, f"Mechanik {name} fehlt in REGELN.md (Abschnitt Mechaniken)"


def test_kombo_zaehlt_nur_andere_karten():
    karten = alle_karten(PAKETE, ["basis"])
    s = Spiel(karten, bots(2), seed=1)
    sp = s.spieler[0]
    sp.hand = ["kuerbiskernoel"]  # Kombo braucht eine ANDERE Speise-Karte
    sp.ablegen_offen = 0
    s.anlass = None
    ruf_vorher = sp.ruf
    s.zug(sp)
    assert sp.ruf - ruf_vorher <= 1  # höchstens Spende, keine Kombo


def test_speisekarten_in_regeln_existieren():
    import re
    namen = {c["name"] for c in alle_karten(PAKETE, ["basis"]).values()}
    regeln = (ROOT / "REGELN.md").read_text(encoding="utf-8")
    for zeile in re.findall(r"^  \* \*[^*]+:\* (.+)$", regeln, flags=re.M):
        for name in [n.strip() for n in zeile.split(",")]:
            assert name in namen, f"Speisekarte nennt unbekannte Karte: {name}"
        assert len(zeile.split(",")) == 10
