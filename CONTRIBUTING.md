# Mitmachen beim Goldenen Merge 🍺

Du musst nicht programmieren können. Es gibt drei Wege, je nachdem, wie tief du einsteigen willst.

## Weg 1: Ohne Code (2 Minuten)

* **Kartenidee:** [Issue „Kartenidee“](../../issues/new?template=1-karte.yml) ausfüllen. Jemand aus dem Stammtisch setzt sie mit dir um.
* **Spieltest:** Print-and-Play-PDF aus den [Releases](../../releases) ausdrucken, spielen, dann [Spieltest-Bericht](../../issues/new?template=2-spieltest.yml) schreiben. **Das ist der wertvollste Beitrag überhaupt.**
* **Plaudern:** Ideen am Stammtisch in den [Discussions](../../discussions).

## Weg 2: Karte direkt im Browser (10 Minuten)

1. Öffne eine ähnliche Karte, z. B. [`inhalte/basis/markt/stammgast.yaml`](inhalte/basis/markt/stammgast.yaml), und kopiere den Inhalt.
2. Geh in den Ordner deines Pakets (z. B. `inhalte/tirol/markt/`) → **Add file → Create new file**.
3. Dateiname = ID der Karte, nur Kleinbuchstaben und Bindestriche, z. B. `kaiserschmarrn.yaml`.
4. Inhalt anpassen (siehe Format unten) → **Propose new file** → **Create pull request**.
5. Die CI prüft deine Karte. Wenige Minuten später postet ein Bot den **Balance-Bericht** in deinen PR.

GitHub legt dafür automatisch einen Fork für dich an. Du brauchst nur einen kostenlosen GitHub-Account.

## Weg 3: Lokal (für Tüftler:innen)

```bash
git clone https://github.com/Taeubel/zum-goldenen-merge && cd zum-goldenen-merge
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python tools/pruefen.py                      # Format & Regeln prüfen
python -m pytest -q                          # Tests
python tools/simulieren.py --karten kaiserschmarrn --pakete basis,tirol
python tools/karten_bauen.py                 # PDFs, Galerie, Kartenliste (in build/)
```

## Kartenformat

```yaml
id: kaiserschmarrn            # = Dateiname
name: Kaiserschmarrn          # max. 28 Zeichen
typ: markt                    # markt | ausbau | anlass
kosten: 4                     # Marktkarten: Geld · Ausbauten: Arbeit
region: tirol                 # alle | wien | niederoesterreich | oberoesterreich | salzburg | tirol | vorarlberg | kaernten | steiermark | burgenland
tags: [speise]                # personal | gast | speise | getraenk | geld
effekte:                      # Bausteine aus REGELN.md → „Mechaniken“
  - geld: 2
kombo:                        # optional
  tag: getraenk
  mindestens: 1
  effekte:
    - ruf: 1
flavor: „Mit Zwetschkenröster, bitte.“   # optional, max. 90 Zeichen
autor: dein-github-name
```

Den **Kartentext schreibst du nicht selbst**. Er wird aus den Effekten erzeugt. So stimmen Regeln und Karten immer überein.

Für Ausbauten gibt es zusätzlich `ruf`, `jede_runde`, `beim_bau` und `endwertung`, für Anlässe `fuer_alle`, `tag_bonus`, `ablegen`, `fuehrender_ablegen`, `bau_rabatt` und `kein_bau`. Beispiele findest du in `inhalte/basis/`. Das vollständige Format steht in `schema/karte.schema.json`.

## Was die CI prüft

| Prüfung | Bei Fehler |
|---|---|
| Schema, Dateiname = ID, ID eindeutig, richtiger Ordner | ❌ PR blockiert, Meldung zeigt die Zeile |
| Nur bekannte Mechaniken, im Paket deklariert | ❌ blockiert |
| Kosten passen grob zur Faustformel | ⚠️ Hinweis |
| Simulation: 2.000 Partien, Fokus-Duell deiner Karte | ⚠️ Hinweis im PR-Kommentar |
| Kartenvorschau-PDF | wird als Download („Artifacts“) an den CI-Lauf gehängt |

**Den Balance-Bericht lesen:** Im Fokus-Duell bevorzugt ein Bot deine Karte, ein zweiter spielt normal. Eine Siegquote **zwischen 40 % und 60 %** heißt „ausgewogen“. Darüber ist die Karte vermutlich zu stark (Kosten rauf oder Effekt runter), darunter zu schwach. Die Bots spielen einfach und regelbasiert. Ein ⚠️ ist ein Gesprächsanlass, kein Urteil.

## Eigenes Paket (z. B. ein Bundesland)

```
inhalte/tirol/
  paket.yaml        # id: tirol, status: experimentell, benoetigt: [basis], mechaniken: []
  markt/…yaml
  ausbauten/…yaml
  anlaesse/…yaml
```

Neue Pakete starten immer als `experimentell`. Nach 3 Spieltest-Berichten aus 2 verschiedenen Runden kann das Paket auf `spieltest` und später auf `stabil` hochgestuft werden (siehe `GOVERNANCE.md`).

## Neue Mechanik

Erst ein **RFC-Issue**, dann Code. Ein Mechanik-PR enthält immer:
1. die Funktion mit `@effekt(...)` in `engine/effekte.py` (Wirkung, Kartentext, Bot-Wert),
2. die Zeile in `REGELN.md` → Mechaniken (ein Test prüft das),
3. einen Test in `tests/`,
4. mindestens eine Karte, die sie nutzt, in einem `experimentell`-Paket. Die Mechanik wird dort in `paket.yaml → mechaniken` deklariert.

Beispiel: `je_tag` aus dem Paket `heuriger`.

## Grafik

Illustrationen kommen als SVG oder PNG (mind. 600 × 400 px) nach `grafik/<paket>/<karten-id>.svg` und werden in der Karte mit `illustration:` verknüpft. Nur eigene Werke oder CC-BY-SA-kompatible Quellen (z. B. CC0, CC BY, CC BY-SA), mit Quellenangabe im PR. **KI-generierte Bilder bitte im PR kennzeichnen.** Keine realen Marken, Logos oder erkennbaren Personen.

## Lizenz deiner Beiträge

Mit deinem PR stellst du Inhalte unter **CC BY-SA 4.0** und Code unter **MIT** zur Verfügung (siehe `LICENSE-INHALTE.md`). Dein GitHub-Name steht auf jeder Karte, die du beigetragen hast.
