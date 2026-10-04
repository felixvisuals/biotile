# BIOTILE

**Ein Geschenk für die Lebewesen der Stadt.** BIOTILE macht aus dem Foto einer in der Stadt
nachweislich besiedelten Naturoberfläche (Rinde, verwitterter Fels, ausgewaschene Mörtelfuge) über
die [Tripo](https://www.tripo3d.ai)-API ein **druckbares Werkzeugset** (Matrize/Stempel, Gießrahmen,
Rückenplatte) für genormte, bioreceptive Habitat-Kacheln. Schulen und Bürger:innen dokumentieren die
aufgestellten Kacheln über Monate in einer offenen Datenbank. So entstehen vergleichbare
Freilanddaten zur Besiedlung verschiedener Oberflächengeometrien durch Moose, Flechten, Algen und
Mikrofauna.

Kunststoff ist Werkzeug, nie Habitat. Vollständiges Konzept: [docs/PROJECT_BRIEF.de.md](docs/PROJECT_BRIEF.de.md)

## Schnellstart

**Docker (Mock-Modus, ohne Tripo-Key):**

```bash
cp .env.example .env
docker compose up --build
```

Danach <http://localhost:8080> öffnen.

**Ohne Docker:** [uv](https://docs.astral.sh/uv/) und Node.js ≥ 20 installieren, dann:

```bash
uv sync
uv run python scripts/seed_demo.py
uv run uvicorn biotile_api.main:app --port 8000
cd apps/web && npm install && npm run dev
```

## Tripo-Key eintragen

In `.env`: `TRIPO_MODE=live` und `TRIPO_API_KEY=…` (die Datei nie committen). Mit
`TRIPO_RECORD=true` wird jeder Live-Aufruf als Fixture gespeichert und im Mock-Modus für dasselbe
Foto wieder abgespielt. Danach API (und in Docker den Worker) neu starten.

## Tests

`uv run pytest` prüft die Pflichttests aus Abschnitt 13.3 des Briefs (Periodizität,
Wasserdichtheit, Mindeststärke, Flankenwinkel, Bauraum, Schwindmaß, Aufhängepunkte, Determinismus),
den Tripo-Client und die API.

## Lizenzen

Code MIT · Designs CC BY-SA 4.0 · Daten CC BY 4.0. Offen und blockierend für öffentliche STLs aus
echter Tripo-Ausgabe: Nutzungsbedingungen zur Weiterverbreitung (Brief 13.2).
