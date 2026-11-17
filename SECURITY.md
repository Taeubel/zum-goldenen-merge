# Sicherheit

„Zum Goldenen Merge“ ist ein Brettspiel. Sicherheitsrelevant sind vor allem die **GitHub-Workflows** (`.github/workflows/`), die bei jedem Pull Request laufen, und die Python-Werkzeuge in `engine/` und `tools/`.

## Lücke melden

Bitte **kein öffentliches Issue** öffnen. Melde Sicherheitsprobleme vertraulich über
**Security → Report a vulnerability** in diesem Repository (GitHub „Private vulnerability reporting“).

Hilfreich sind:

* welche Datei oder welcher Workflow betroffen ist,
* wie sich das Problem nachstellen lässt (z. B. ein Beispiel-PR aus einem Fork),
* was jemand damit anstellen könnte.

Wir melden uns innerhalb von **7 Tagen**. Behobene Lücken nennen wir in den Release Notes, auf Wunsch mit deinem Namen.

## Was wir besonders ernst nehmen

* Workflows, die Code aus fremden PRs mit Schreibrechten oder Secrets ausführen („Pwn Requests“)
* Wege, über die Bot-Kommentare, Labels oder Releases von außen manipuliert werden können
* Abhängigkeiten mit bekannten Lücken (Dependabot ist aktiv)

Unterstützt wird jeweils nur der aktuelle Stand von `main` und das neueste Release.
