# 🍺 Zum Goldenen Merge

**Das Open-Source-Wirtshausspiel aus Österreich. Gebaut von allen, per Pull Request.**

[![CI](https://github.com/Taeubel/zum-goldenen-merge/actions/workflows/ci.yml/badge.svg)](https://github.com/Taeubel/zum-goldenen-merge/actions/workflows/ci.yml)
[![Kartengalerie](https://img.shields.io/badge/Karten-Galerie-b5121b)](https://Taeubel.github.io/zum-goldenen-merge/)
[![Lizenz: CC BY-SA 4.0](https://img.shields.io/badge/Inhalte-CC%20BY--SA%204.0-lightgrey)](LICENSE-INHALTE.md)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-blue)](LICENSE)

Ihr führt je ein Wirtshaus: Ihr stellt die Kellnerin ein, holt den Stammgast an den Tisch, setzt Kasnudeln und Uhudler auf die Karte und baut euch vom Gastgarten bis zum Tanzboden hoch. Ein Deckbau-Spiel für 2–4 Personen, rund 45 Minuten.

**Das Besondere:** Jede Karte ist eine kleine Textdatei in diesem Repository. Wer eine Idee hat – den Kaiserschmarrn, den Kirtag im eigenen Ort, den grantigen Hausmeister –, schickt einen Pull Request. Ein Bot spielt die neue Karte sofort tausende Male durch und sagt im PR, ob sie zu stark oder zu schwach ist. Am Ende steht dein Name auf der Karte.

## Spielen

1. Neuestes **Print-and-Play-PDF** aus den [Releases](../../releases) laden. Oder alle Karten in der [Galerie](https://Taeubel.github.io/zum-goldenen-merge/) ansehen.
2. Ausdrucken, schneiden, losspielen: [Spielregeln](REGELN.md) (2 Seiten).
3. [Spieltest-Bericht](../../issues/new?template=2-spieltest.yml) schreiben. Das hilft am meisten!

## Mitmachen

| Ich will … | So geht's |
|---|---|
| eine Idee einbringen, ohne Code | [Kartenidee einreichen](../../issues/new?template=1-karte.yml) |
| eine Karte selbst anlegen | [CONTRIBUTING.md → Weg 2](CONTRIBUTING.md) (geht im Browser) |
| ein Bundesland-Paket starten | [CONTRIBUTING.md → Eigenes Paket](CONTRIBUTING.md#eigenes-paket-z-b-ein-bundesland) |
| eine neue Regel vorschlagen | [RFC-Issue](../../issues/new?template=3-mechanik.yml) |
| den Simulator verbessern | `engine/bots.py` – bessere Bots, bessere Balance |

Wo noch Karten fehlen, zeigt die Bundesland-Übersicht in der [Kartenliste](https://Taeubel.github.io/zum-goldenen-merge/KARTEN.md).

## So entsteht eine Karte

```
Idee ──► Pull Request ──► CI: Format & Regeln ──► Bot spielt 2.000 Partien ──► Review ──► Merge
                                                        │                                   │
                                                        ▼                                   ▼
                                           Balance-Bericht im PR          Galerie + nächstes Print-and-Play
```

## Aufbau des Repos

```
REGELN.md            Spielregeln (die einzige Quelle der Wahrheit)
inhalte/<paket>/     Karten als YAML, eine Datei pro Karte
  basis/             Grundspiel
  heuriger/          Beispiel-Erweiterung mit neuer Mechanik
engine/              Regel-Engine und Bots (Python)
tools/               pruefen.py · simulieren.py · karten_bauen.py
schema/              Kartenformat (JSON Schema)
docs/                Balance, RFCs, Setup
.github/             CI, Vorlagen, Labels, Regeln für main
```

## Projekt

* [Mitmachen](CONTRIBUTING.md) · [Wie entschieden wird](GOVERNANCE.md) · [Stammtisch-Regeln](CODE_OF_CONDUCT.md) · [Balance-Methode](docs/BALANCE.md) · [Sicherheit](SECURITY.md) · [Änderungen](CHANGELOG.md)
* Inhalte: **CC BY-SA 4.0**, Code: **MIT**

*Entstanden aus einem Experiment: Was passiert, wenn man ein Brettspiel wie Open-Source-Software entwickelt?*
