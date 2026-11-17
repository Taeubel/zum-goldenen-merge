#!/usr/bin/env python3
"""Prüft alle Inhalte: Schema, Eindeutigkeit, bekannte Mechaniken, Kosten-Plausibilität.

Fehler brechen die CI ab. Warnungen erscheinen im PR, blockieren aber nicht.
Ausgabe im GitHub-Actions-Annotationsformat, wenn GITHUB_ACTIONS gesetzt ist.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import effekte as fx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GHA = bool(os.environ.get("GITHUB_ACTIONS"))
fehler: list[str] = []
warnungen: list[str] = []


def melde(art: str, datei: Path | str, text: str):
    rel = Path(datei).relative_to(ROOT) if Path(datei).is_absolute() else datei
    if GHA:
        print(f"::{art} file={rel}::{text}")
    else:
        print(f"[{art.upper()}] {rel}: {text}")
    (fehler if art == "error" else warnungen).append(f"{rel}: {text}")


# Kosten-Gewichte: per Regression aus dem balancierten Grundspiel ermittelt
# (siehe docs/BALANCE.md). Neue Mechaniken fallen auf ihren Bot-Wert zurück.
KOSTEN_GEWICHTE = {"geld": 1.0, "arbeit": 1.8, "ruf": 2.2, "ziehen": 2.3, "kaufen": 0.3,
                   "entsorgen": 0.5, "nehmen": 0.25, "gegner_ablegen": 1.5}
KOMBO_FAKTOR = 0.5


def _kosten(effekte) -> float:
    s = 0.0
    for e in effekte or []:
        (name, wert), = e.items()
        if name in KOSTEN_GEWICHTE:
            s += KOSTEN_GEWICHTE[name] * wert
        else:
            s += fx.MECHANIKEN[name].wert(wert)
    return s


def kosten_erwartung(karte: dict) -> float:
    w = _kosten(karte.get("effekte"))
    if karte.get("kombo"):
        w += KOMBO_FAKTOR * _kosten(karte["kombo"]["effekte"])
    return w


def pruefe_effekte(datei, effekte, ort):
    for e in effekte or []:
        if not isinstance(e, dict) or len(e) != 1:
            melde("error", datei, f"{ort}: jeder Effekt braucht genau einen Schlüssel")
            continue
        (name, wert), = e.items()
        mech = fx.MECHANIKEN.get(name)
        if not mech:
            bekannt = ", ".join(sorted(fx.MECHANIKEN))
            melde("error", datei, f"{ort}: unbekannte Mechanik „{name}“. Bekannt: {bekannt}. "
                                  "Neue Mechaniken brauchen ein RFC (docs/rfcs/).")
            continue
        if mech.param == "int" and not isinstance(wert, int):
            melde("error", datei, f"{ort}: „{name}“ erwartet eine ganze Zahl")
        if mech.param == "objekt":
            if not isinstance(wert, dict) or "effekte" not in wert:
                melde("error", datei, f"{ort}: „{name}“ erwartet ein Objekt mit 'effekte'")
            else:
                pruefe_effekte(datei, wert["effekte"], f"{ort}.{name}")
        yield name


def main() -> int:
    karte_schema = Draft202012Validator(json.loads((ROOT / "schema/karte.schema.json").read_text()))
    paket_schema = Draft202012Validator(json.loads((ROOT / "schema/paket.schema.json").read_text()))
    alle_ids: dict[str, Path] = {}
    pakete = {}
    for meta in sorted((ROOT / "inhalte").glob("*/paket.yaml")):
        p = yaml.safe_load(meta.read_text(encoding="utf-8"))
        for err in paket_schema.iter_errors(p):
            melde("error", meta, f"Schema: {err.message}")
        if p.get("id") != meta.parent.name:
            melde("error", meta, f"Paket-ID „{p.get('id')}“ muss dem Ordnernamen „{meta.parent.name}“ entsprechen")
        pakete[p.get("id")] = (meta, p)

    basis_mechaniken = set(pakete.get("basis", (None, {}))[1].get("mechaniken", []))
    for pid, (meta, p) in pakete.items():
        for b in p.get("benoetigt", []):
            if b not in pakete:
                melde("error", meta, f"benötigtes Paket „{b}“ existiert nicht")
        erlaubt = set(p.get("mechaniken", [])) | basis_mechaniken
        for b in p.get("benoetigt", []):
            erlaubt |= set(pakete.get(b, (None, {}))[1].get("mechaniken", []))
        for datei in sorted(meta.parent.rglob("*.yaml")):
            if datei.name == "paket.yaml":
                continue
            try:
                k = yaml.safe_load(datei.read_text(encoding="utf-8"))
            except yaml.YAMLError as e:
                melde("error", datei, f"YAML-Fehler: {e}")
                continue
            if not isinstance(k, dict):
                melde("error", datei, "Datei enthält keine Karte")
                continue
            for err in karte_schema.iter_errors(k):
                pfad = "/".join(str(x) for x in err.absolute_path) or "(Karte)"
                melde("error", datei, f"Schema bei {pfad}: {err.message}")
            kid = k.get("id")
            if kid != datei.stem:
                melde("error", datei, f"id „{kid}“ muss dem Dateinamen „{datei.stem}“ entsprechen")
            if kid in alle_ids:
                melde("error", datei, f"id „{kid}“ gibt es schon in {alle_ids[kid].relative_to(ROOT)}")
            alle_ids[kid] = datei
            ordner = {"start": "start", "markt": "markt", "ausbau": "ausbauten", "anlass": "anlaesse"}
            if k.get("typ") in ordner and datei.parent.name != ordner[k["typ"]]:
                melde("error", datei, f"Karten vom Typ „{k['typ']}“ gehören in den Ordner „{ordner[k['typ']]}/“")
            if k.get("typ") == "start" and pid != "basis":
                melde("error", datei, "Startkarten dürfen nur im Grundspiel geändert werden")
            benutzt = set()
            for feld in ("effekte", "jede_runde", "beim_bau", "fuer_alle"):
                benutzt |= set(pruefe_effekte(datei, k.get(feld), feld))
            for feld in ("kombo", "tag_bonus"):
                if isinstance(k.get(feld), dict):
                    benutzt |= set(pruefe_effekte(datei, k[feld].get("effekte"), feld))
                    if feld == "kombo":
                        benutzt.add("kombo")
            # "Beim Bau" passiert nach dem Ausspielen: Ziehen/Arbeit/Entsorgen wären wirkungslos
            for e in k.get("beim_bau") or []:
                if isinstance(e, dict) and set(e) & {"ziehen", "arbeit", "entsorgen"}:
                    melde("error", datei, f"beim_bau: „{list(e)[0]}“ hat nach dem Ausspielen keine Wirkung "
                                          "(erlaubt: geld, kaufen, ruf, nehmen)")
            fremd = benutzt - erlaubt
            if fremd:
                melde("error", datei, f"Mechanik(en) {sorted(fremd)} sind im Paket „{pid}“ nicht deklariert (paket.yaml → mechaniken)")
            if k.get("typ") == "markt" and isinstance(k.get("kosten"), int) and not fremd and k.get("effekte"):
                try:
                    soll = kosten_erwartung(k)
                except KeyError:
                    continue
                if abs(soll - k["kosten"]) > 2.0:
                    richtung = "günstig" if k["kosten"] < soll else "teuer"
                    melde("warning", datei, f"Kosten {k['kosten']} wirken zu {richtung} (Faustformel ≈ {soll:.1f}). "
                                            "Die Simulation im PR gibt genauere Hinweise.")

    print(f"\n{len(alle_ids)} Karten in {len(pakete)} Paketen geprüft: "
          f"{len(fehler)} Fehler, {len(warnungen)} Warnungen.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
