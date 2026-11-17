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

* **Gesamtbericht:** 2.000 Partien mit zwei „gierigen“ Bots: Spieldauer, Punkte, Siegquote nach Startposition (Ziel 44–56 %).
* **Fokus-Duell je geänderter Karte:** Ein Bot bevorzugt die Karte (Bewertungsbonus, max. 3 Exemplare), der andere spielt normal. Die Sitzplätze wechseln.
  * **40–60 %** Siegquote → ausgewogen ✅
  * darüber → vermutlich zu stark ⚠️
  * darunter → vermutlich zu schwach ⚠️

## Grenzen
Die Bots sind einfach. Sie bluffen nicht, planen nicht über mehrere Züge und spielen Kombos nur zufällig gut. Karten, deren Stärke in cleveren Kombinationen liegt, werden oft **unterschätzt**. Darum gilt: Simulation = Frühwarnsystem, **Spieltest am Tisch = Entscheidung.**

## Stand Grundspiel v0.1 (3.000 Partien je Messung)
* **2 Personen:** Ø 11,6 Runden (80 % der Partien zwischen 8 und 17), Startspieler gewinnt 49 %.
* **3 Personen:** Ø 11,5 Runden, Siegquoten 34 / 34 / 32 %. **4 Personen:** Ø 10,5 Runden, 25 / 28 / 23 / 25 %.
* Rund 0,2 % der Bot-Partien erreichen das Sicherheitslimit von 30 Runden. Das passiert, wenn beide Bots keinen Ausbau mehr bezahlen wollen. Menschen spielen das anders, im Auge behalten.
* **19 von 22 Marktkarten** liegen im Zielband. *Most*, *Stammgast* und *Kürbiskernöl* liegen knapp darunter (38–40 %), werden aber von den Bots am häufigsten gekauft. Das sind gute Kandidaten für die ersten Community-Spieltests.

## Bot verbessern?
Bessere Bots = bessere Prüfung. PRs für `engine/bots.py` sind sehr willkommen (z. B. ein MCTS-Bot).
