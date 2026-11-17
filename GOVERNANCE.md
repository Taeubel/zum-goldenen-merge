# Wie hier entschieden wird

## Design-Säulen

Jeder Beitrag wird an diesen vier Säulen gemessen. Passt etwas nicht dazu, ist das ein guter Grund für ein freundliches „Nein, danke“.

1. **In 10 Minuten erklärt.** Die Kernregeln passen auf zwei Seiten. Komplexität gehört auf Karten, nicht ins Regelheft.
2. **Österreich mit Augenzwinkern.** Liebevoll, regional, selbstironisch – nie herabwürdigend.
3. **Modular statt kompliziert.** Neues kommt als Karte oder Paket dazu. Das Grundspiel bleibt schlank. Jede Partie nutzt nur 10 Marktsorten, darum darf der Pool beliebig wachsen.
4. **Simulierbar.** Jede Regel muss sich in der Engine abbilden lassen. Was der Bot nicht spielen kann, kann die CI nicht prüfen.

## Rollen

| Rolle | Wer | Darf |
|---|---|---|
| **Gast** | alle | Issues, Ideen, Spieltests, Pull Requests |
| **Stammtisch** (Maintainer) | aktive Beitragende, auf Einladung | Inhalte reviewen und mergen, Labels vergeben |
| **Bundesland-Pat:in** | je Regionspaket eine Person | erstes Review für ihr Paket (eingetragen in `CODETaeubelS`) |
| **Wirt** (Projektleitung) | Gründer:in | letzte Entscheidung über Kernregeln, Engine, Grundspiel und Releases |

Wer **3 gemergte PRs** hat und freundlich reviewt, kann in den Stammtisch eingeladen werden.

## Was braucht welche Freigabe?

| Änderung | Weg | Freigabe |
|---|---|---|
| Neue Karte in einem Paket mit Status `experimentell` | PR | 1 Review + grüne CI |
| Neue/geänderte Karte in `spieltest`/`stabil` | PR | 1 Review + grüne CI + Simulation ohne ⚠️ (oder ⚠️ begründet) |
| Neues Paket | PR mit `paket.yaml` (Status `experimentell`) | 1 Review aus dem Stammtisch |
| Paket-Status hochstufen | PR | ≥ 3 Spieltest-Berichte von ≥ 2 verschiedenen Runden |
| Neue Mechanik, Regeländerung, Spielparameter | **RFC-Issue** → 14 Tage Diskussion → PR | Wirt entscheidet und begründet öffentlich |
| Grundspiel (`inhalte/basis/`) | PR | Wirt |

## RFC-Ablauf (Request for Comments)

1. Issue mit der Vorlage „Neue Mechanik / Regeländerung“ öffnen.
2. Mindestens **14 Tage** öffentliche Diskussion. Gerne mit Prototyp-Karten im Paket `experimentell`.
3. Der Wirt entscheidet: **angenommen**, **abgelehnt** (mit Begründung) oder **zurück an den Start** (mit konkreten Fragen).
4. Erst nach „angenommen“: PR mit `engine/effekte.py` + `REGELN.md` + Test + Beispielkarte. Die angenommene Fassung wird unter `docs/rfcs/NNNN-titel.md` abgelegt.

## Versionen

Wir nutzen *Semantic Versioning* für das Spiel:

* **MAJOR** (1.0 → 2.0): Kernregeln ändern sich so, dass alte Karten anders funktionieren.
* **MINOR** (0.1 → 0.2): neue Karten, Pakete oder Mechaniken.
* **PATCH** (0.1.0 → 0.1.1): Balance-Anpassungen, Texte, Fehler.

Geplant ist ein **„Monatsausschank“**: Jeden ersten Montag im Monat gibt es ein Release mit Print-and-Play-PDF.

## Konflikte

Inhaltliche Uneinigkeit wird im Issue sachlich geklärt. Wenn's hakt, entscheidet der Wirt. Persönliches regelt der `CODE_OF_CONDUCT.md`.
