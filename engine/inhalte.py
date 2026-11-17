"""Lädt Pakete und Karten aus inhalte/<paket>/**.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INHALTE = ROOT / "inhalte"


def lade_pakete(verzeichnis: Path = INHALTE) -> dict[str, dict]:
    pakete = {}
    for meta in sorted(verzeichnis.glob("*/paket.yaml")):
        daten = yaml.safe_load(meta.read_text(encoding="utf-8"))
        daten["_pfad"] = meta.parent
        daten["karten"] = {}
        for datei in sorted(meta.parent.rglob("*.yaml")):
            if datei.name == "paket.yaml":
                continue
            karte = yaml.safe_load(datei.read_text(encoding="utf-8"))
            karte["_datei"] = str(datei.relative_to(verzeichnis.parent))
            karte["_paket"] = daten["id"]
            daten["karten"][karte["id"]] = karte
        pakete[daten["id"]] = daten
    return pakete


def alle_karten(pakete: dict[str, dict], aktiv: list[str] | None = None) -> dict[str, dict]:
    karten = {}
    for pid, p in pakete.items():
        if aktiv is not None and pid not in aktiv:
            continue
        karten.update(p["karten"])
    return karten
