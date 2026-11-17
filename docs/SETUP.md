# Repository einrichten (einmalig, ca. 30 Minuten)

Voraussetzung: [GitHub CLI](https://cli.github.com/) (`gh auth login`). Konto (`Taeubel`), Name in `LICENSE` und Kontakt im Verhaltenskodex sind bereits eingetragen.

## 1. Repository anlegen und hochladen

```bash
git init -b main && git add . && git commit -m "Erster Ausschank: Zum Goldenen Merge v0.1.0"
gh repo create zum-goldenen-merge --public --source . --push \
  --description "Das Open-Source-Wirtshausspiel aus Österreich – gebaut per Pull Request 🍺" \
  --homepage "https://Taeubel.github.io/zum-goldenen-merge/"
```

## 2. Repository-Einstellungen

```bash
gh repo edit \
  --enable-discussions --enable-issues --enable-wiki=false --enable-projects \
  --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false \
  --delete-branch-on-merge --allow-update-branch \
  --add-topic brettspiel,boardgame,open-source,austria,oesterreich,deckbuilding,print-and-play,game-design,hacktoberfest
```

Im Browser unter **Settings → General**:
* *Pull Requests:* „Always suggest updating pull request branches“ ✅
* *Features → Discussions:* Kategorien anlegen: **Stammtisch** (allgemein), **Ideen** (Formular aus `.github/DISCUSSION_TEMPLATE/ideen.yml`), **Spielabende** (Fotos & Berichte), **Ankündigungen** (nur Maintainer)
* *Social preview:* Bild 1280 × 640 px hochladen (z. B. ein Foto vom gedruckten Spiel)

## 3. main schützen (Ruleset)

```bash
gh api repos/Taeubel/zum-goldenen-merge/rulesets --method POST --input .github/rulesets/main-schuetzen.json
```

Alternativ: **Settings → Rules → Rulesets → New ruleset → Import a ruleset** und die JSON-Datei wählen.

Das Ruleset bewirkt:
* main kann nicht gelöscht oder per Force-Push überschrieben werden.
* Änderungen nur per PR, mit **1 Freigabe** durch einen Code Owner und offenen Review-Kommentaren aufgelöst.
* Gemergt wird nur per **Squash**: ein PR = ein Commit = eine saubere Changelog-Zeile.
* Die Checks `pruefen` und `simulation` müssen grün sein.
* Admins (du) dürfen das umgehen, damit du als Einzelperson am Anfang nicht blockiert bist.

## 4. Actions und Pages

* **Settings → Actions → General → Fork pull request workflows:** „Require approval for first-time contributors“ ✅ (Schutz vor Missbrauch der CI-Minuten)
* **Settings → Actions → General → Workflow permissions:** „Read repository contents“ (Standard). Die Workflows fordern ihre Rechte selbst an.
* **Settings → Pages → Source:** „GitHub Actions“. Oder per CLI:
  ```bash
  gh api repos/Taeubel/zum-goldenen-merge/pages --method POST -f build_type=workflow
  ```
* Labels anlegen: **Actions → Labels → Run workflow**. Das liest `.github/labels.yml`.
* Galerie erstmals bauen: **Actions → Kartengalerie → Run workflow**.

## 5. Sicherheit

* **Settings → Code security:** Private vulnerability reporting ✅ (dahin verweist `SECURITY.md`), Dependabot alerts ✅, Dependabot security updates ✅, Secret scanning ✅, Push protection ✅. Für öffentliche Repos ist das kostenlos.
  ```bash
  gh api repos/Taeubel/zum-goldenen-merge/private-vulnerability-reporting --method PUT
  ```
* Die CI läuft für PRs aus Forks **nur mit Leserechten**. Der Bot-Kommentar kommt aus einem separaten Workflow (`pr-kommentar.yml`), der keinen fremden Code ausführt. Diese Trennung bitte nicht aufheben.

## 6. Erstes Release

```bash
git tag v0.1.0 && git push --tags
```

Der Release-Workflow baut das Print-and-Play-PDF und hängt es ans Release.

## 7. Projekt-Board (optional)

```bash
gh project create --owner Taeubel --title "Zum Goldenen Merge – Roadmap"
```

Spalten: *Ideen → Angenommen → In Arbeit → Spieltest → Fertig*. Unter **Workflows** im Board „Auto-add“ für Issues mit den Labels `karte`, `rfc` und `spieltest` aktivieren.

## 8. Good First Issues vorbereiten (vor dem Launch!)

Lege vor dem ersten LinkedIn-Post **8–10 Issues** mit dem Label `good first issue` an, zum Beispiel:
* „Tirol braucht eine Speise“ (je Bundesland eines, mit Label `region: …`)
* „*Most* und *Stammgast* sind laut Simulation etwas zu schwach – Vorschlag?“
* „*Schrammelmusik* (Heuriger) ist zu schwach“
* „Englische Übersetzung der Kartennamen (`text_en`)“
* „Spielplan-Übersichtskarte (Zugablauf) als PDF gestalten“

Neue Besucher:innen brauchen einen konkreten Einstieg, sonst bleibt es beim ⭐.

## Checkliste

- [ ] `Taeubel` ersetzt, Name in `LICENSE` und Kontakt in `CODE_OF_CONDUCT.md` eingetragen
- [ ] Repo öffentlich, Topics gesetzt, Social Preview hochgeladen
- [ ] Discussions mit 4 Kategorien
- [ ] Ruleset aktiv
- [ ] Pages auf „GitHub Actions“, Galerie erreichbar
- [ ] Labels synchronisiert
- [ ] Erstzugriff-Freigabe für Fork-PRs aktiv
- [ ] Private vulnerability reporting, Dependabot und Secret Scanning aktiv
- [ ] Release v0.1.0 mit PDF
- [ ] 8–10 Good First Issues
- [ ] Testlauf: einen eigenen PR aus einem Zweit-Account oder Fork stellen und prüfen, ob der Bot-Kommentar erscheint
