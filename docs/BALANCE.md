# Wie die Balance-Prüfung funktioniert

## 1. Faustformel (sofort, in `tools/pruefen.py`)

Jeder Baustein hat ein **Kosten-Gewicht**, ermittelt per Regression aus dem balancierten Grundspiel v0.1:

| Baustein | Gewicht | | Baustein | Gewicht |
|---|---|---|---|---|
| geld | 1,0 je Punkt | | kaufen | 0,3 |
| arbeit | 1,8 | | entsorgen | 0,5 |
| ruf | 2,2 | | nehmen | 0,25 je Kostenpunkt |
| ziehen | 2,3 | | gegner_ablegen | 1,5 |

Kombo-Effekte zählen zur Hälfte. Weicht der Preis einer Marktkarte um mehr als **2** ab, gibt es eine Warnung. Neue Mechaniken ohne Gewicht fallen auf ihren Bot-Wert zurück. Nach jedem größeren Release sollten die Gewichte neu kalibriert werden.

## 2. Simulation (`tools/simulieren.py`, im PR automatisch)

Der Bot postet in jeden PR einen **Balance-Bericht** mit Ampel. Ganz oben steht das Gesamturteil (die schlechteste Ampel), darunter die Details. Keine Ampel blockiert den PR, sie sind Hinweise für Menschen.

| Ampel | Bedeutung |
|---|---|
| 🟢 | im Zielbereich |
| 🟡 | knapp daneben: anschauen, Spieltest empfohlen |
| 🔴 | deutlich daneben: Änderung vermutlich anpassen |
| ℹ️ | nur Information |

**Gesamtspiel:** 2.000 Partien mit zwei „gierigen“ Bots.

| Kennzahl | 🟢 | 🟡 |
|---|---|---|
| Spieldauer (Ø Runden) | 10–20 | 8–22 |
| Startspieler gewinnt (2 Personen) | 44–56 % | 40–60 % |
| Festgefahrene Partien (Rundenlimit erreicht) | ≤ 1 % | ≤ 3 % |
| Knappe Partien (≤ 3 Ruf Abstand) | nur Info | |

* **Fokus-Duell je geänderter Marktkarte:** Ein Bot bevorzugt die Karte (Bewertungsbonus, max. 3 Exemplare), der andere spielt normal. Die Sitzplätze wechseln.
  * **40–60 %** Siegquote → 🟢 ausgewogen, **35–65 %** → 🟡, sonst 🔴 (zu stark bzw. zu schwach)
  * bei mehr Personen: fair (1/Spielerzahl) ± 10 Punkte grün, ± 15 Punkte gelb
  * Zu jeder Quote steht die Messungenauigkeit (95 %), z. B. „48 % ± 4“.
  * Die Faustformel aus Abschnitt 1 wird danebengestellt. Widersprechen sich Simulation und Faustformel, sagt der Bericht das ausdrücklich.
* **Vergleich „vorher“:** Der Bericht simuliert zusätzlich den Kartenstand vor dem PR (gleiche Engine, gleiche Zufallszahlen). So sieht man auch die Wirkung geänderter Ausbauten und Anlässe, die sich nicht im Duell testen lassen.
* Lokal: `python tools/simulieren.py --geaendert origin/main` erzeugt denselben Bericht, `--ohne-vergleich` spart die Basis-Simulation.

## Grenzen
Die Bots sind einfach. Sie bluffen nicht, planen nicht über mehrere Züge und spielen Kombos nur zufällig gut. Karten, deren Stärke in cleveren Kombinationen liegt, werden oft **unterschätzt**. Darum gilt: Simulation = Frühwarnsystem, **Spieltest am Tisch = Entscheidung.**

## Stand Grundspiel v0.1 (3.000 Partien je Messung)
* **2 Personen:** Ø 11,6 Runden (80 % der Partien zwischen 8 und 17), Startspieler gewinnt 49 %.
* **3 Personen:** Ø 11,5 Runden, Siegquoten 34 / 34 / 32 %. **4 Personen:** Ø 10,5 Runden, 25 / 28 / 23 / 25 %.
* Rund 0,2 % der Bot-Partien erreichen das Sicherheitslimit von 30 Runden. Das passiert, wenn beide Bots keinen Ausbau mehr bezahlen wollen. Menschen spielen das anders, im Auge behalten.
* **19 von 22 Marktkarten** liegen im Zielband. *Most*, *Stammgast* und *Kürbiskernöl* liegen knapp darunter (38–40 %), werden aber von den Bots am häufigsten gekauft. Das sind gute Kandidaten für die ersten Community-Spieltests.

## Bot verbessern?
Bessere Bots = bessere Prüfung. PRs für `engine/bots.py` sind sehr willkommen (z. B. ein MCTS-Bot).
