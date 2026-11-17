# RFC 0001: Mechanik `je_tag` (skalierender Bonus)

* **Status:** angenommen (als Beispiel für den Ablauf, Paket „Beim Heurigen“)
* **Autor:in:** @Taeubel

## Problem
Kombos belohnen „mindestens N“ Karten eines Merkmals. Es fehlt ein Baustein, der *mit jeder* passenden Karte stärker wird – thematisch der Heurige, bei dem jedes Achterl die Stimmung hebt.

## Vorschlag
> `je_tag`: Bonus für **jede** in diesem Zug gespielte Karte mit Merkmal M (diese eingeschlossen). Wird zusammen mit den Kombos abgerechnet.

## Beispielkarten
* *Heurigenwirt* (4): je Getränk-Karte +1 Geld
* *Schrammelmusik* (5): je Getränk-Karte +1 Ruf

## Design-Säulen
| Säule | Passt? | Begründung |
|---|---|---|
| In 10 Minuten erklärt | ✅ | ein Satz |
| Österreich mit Augenzwinkern | ✅ | Heuriger, Schrammeln |
| Modular statt kompliziert | ✅ | nur im Paket `heuriger` |
| Simulierbar | ✅ | in der Kombo-Phase abgerechnet |

## Entscheidung
Angenommen für das Paket `heuriger` (Status `experimentell`). Die Simulation zeigt, dass *Schrammelmusik* noch zu schwach ist – das ist eine gute erste Aufgabe für die Community.
