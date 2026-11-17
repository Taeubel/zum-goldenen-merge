"""Tests für den Balance-Bericht (tools/simulieren.py, tools/stammtisch.py)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.inhalte import alle_karten, lade_pakete  # noqa: E402
from tools import simulieren as sim  # noqa: E402
from tools import stammtisch  # noqa: E402

KARTEN = alle_karten(lade_pakete(), ["basis"])


def _ergebnis(spieler=(2, 3, 4)):
    e = sim.auswerten(KARTEN, ["koch"], list(spieler), partien=30, seed=1, n_duell=20, basis_karten=KARTEN)
    return sim.bewerte(e)


def test_ampel_grenzen():
    g = (0.4, 0.6, 0.35, 0.65)
    assert sim.ampel(0.5, g) == sim.GRUEN
    assert sim.ampel(0.62, g) == sim.GELB
    assert sim.ampel(0.3, g) == sim.ROT


def test_fokus_band_skaliert_mit_spielerzahl():
    lo, hi, _, _ = sim.fokus_grenzen(4)
    assert lo < 0.25 < hi


def test_bericht_hat_alle_abschnitte_und_spielerzahlen():
    md = sim.markdown(_ergebnis(), KARTEN, [], ziel=["koch"], basis_name="main", basis_karten=KARTEN)
    for text in ("Balance-Bericht", "Stimmen vom Stammtisch", "Die Karten aus diesem PR",
                 "Das Spiel als Ganzes", "Was jetzt?", "Wie lese ich diesen Bericht?",
                 "2 Spieler", "3 Spieler", "4 Spieler", "vorher"):
        assert text in md
    for f in ("Resi", "Ferdl", "Frau Magister Brandl", "Lukas", "Der Grantler"):
        assert f in md


def test_jede_figur_schreibt_prosa():
    e = _ergebnis((2,))
    for s in stammtisch.stimmen(e, KARTEN, ziel=["koch"], basis_karten=KARTEN):
        assert s["text"].strip().endswith((".", "!", "?"))
        assert len(s["text"]) > 40


def test_zu_starke_karte_faerbt_bericht_rot():
    e = _ergebnis((2,))
    e[2]["karten"]["koch"]["siegquote"] = 0.8
    sim.bewerte(e)
    assert sim.gesamtampel(e) == sim.ROT
    ferdl = next(s for s in stammtisch.stimmen(e, KARTEN, ziel=["koch"], basis_karten=KARTEN, gesamt=sim.ROT)
                 if s["name"] == "Ferdl")
    assert "😈" in ferdl["daumen"]
    md = sim.markdown(e, KARTEN, [], ziel=["koch"])
    assert "🔴 Deutliche Auffälligkeit" in md
