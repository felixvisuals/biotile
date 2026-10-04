# BIOTILE – Stand, Prüfung und Plan (03.10.2026, aktualisiert)

> Update: erledigt sind Einladungscodes, Kachelcode vorne, Moos-Nester (Standard) mit Rinnsalen,
> schräge Aufhängelöcher, Sechseck-Werkzeuge (Barcelona-Modus), Kachelgröße, optionale
> Koordinaten mit GPS, Code-Suche (Muster → alle Kacheln), Foto-Hover und Großansicht, echte Fotos.
> Offen: Live-Test Tripo, monochrome Karte (MapLibre), Logo/Name als Signatur, Hohlmatrize,
> Rahmen-Klammern, Zaunadapter-STL, Beton-Rückenplatte, Alembic, E-Mail-Bestätigung, surfalize-Lizenz.

## 1. Funktionsprüfung

### 1.1 Deine neuen Wünsche

| Funktion | Stand | Was fehlt |
|---|---|---|
| Kachel benennen | **teilweise**: Muster haben einen Namen, einzelne Kacheln nur eine ID | Spitzname pro Kachel (≤ 24 Zeichen) |
| Code vorne auf der Kachel | **fehlt** (laut Brief steht die ID hinten, damit das Muster nahtlos bleibt) | Signaturfeld in der Geometrie, siehe 2.2 |
| Logo (SVG/PNG freigestellt) als Signatur | **fehlt** | Upload, Vektorisierung, Prägung, siehe 2.2 |
| Optional Name statt Logo, Zeichenlimit | **fehlt** | Einstrich-Schrift, max. 12 Zeichen |
| Kachel über Code ansehen | **vorhanden** (`/instances/BT-…`, QR auf der Fotokarte) | — |
| Notizen/Hintergrund des Nutzers | **teilweise** (`notes` beim Aufhängen) | eigenes Feld „Geschichte“, später bearbeitbar |
| Ursprungsbild anzeigen | **fehlt bewusst**: Quellfotos werden aus Datenschutzgründen nie öffentlich ausgeliefert | Opt-in „Foto zeigen“ + Freigabe (keine Personen) |
| Bilder im Zeitverlauf | **vorhanden** (Beobachtungen mit Foto) | Vorher/Nachher-Slider, Thumbnails |
| GPS zum Kopieren / Karte | **fehlt**, Brief: „Standorte nur grob“ | siehe 2.3 (Konflikt, bitte entscheiden) |
| Generierungslimit pro Nutzer | **neu umgesetzt** | siehe 1.3 |

### 1.2 Hackathon-MVP aus dem Brief (14.1)

| # | Punkt | Stand |
|---|---|---|
| 1 | Repo, Compose, Mock/Live-Client, Lizenz | erledigt (Compose ungetestet: kein Docker auf dem Mac) |
| 2 | **Tripo-Test mit echten Fotos planer Flächen** | **offen**: Key ist da, Live-Modus noch aus |
| 3 | Pipeline bis Mindeststärke | erledigt, neu: Nahtheilung (0.2.0) |
| 4 | Matrize, 4 Rahmenwände, Ton-Rückenplatte, Bauraum, ZIP | erledigt, Befestigung siehe 3 |
| 5 | Wizard, Fortschritt, Editor, 3×3, Export | erledigt |
| 6 | Galerie | erledigt |
| 7 | Kachel registrieren, Beobachtung, Referenzkarte | erledigt |
| 8 | README, Methodenseite, **Screencast, Asset-Board** | Screencast und Asset-Board offen |
| 9 | Matrize drucken, Tonkachel pressen | offen (physisch) |

Nicht im MVP und weiter offen: Textmodus, Mikroband aus Normal-Map, Beton-Rückenplatte, Halbkanäle,
Wände/Randomisierung, Bohrschablone, ArUco-Auswertung, Moderation, Adapter-STLs.

### 1.3 Login und Limit (neu)

- Konten nur für Schulen/Projekte/Forschende, Passwort (scrypt), Session-Cookie (HttpOnly).
- Jede Tripo-Generierung wird **vor dem Start** mit einem atomaren `UPDATE … WHERE used < limit`
  abgebucht. Parallele Anfragen können das Limit nicht überholen, und der Browser bekommt den Key nie zu sehen.
- Grenzen in `.env`: `GENERATION_LIMIT_MOCK`, `GENERATION_LIMIT_LIVE`, `GLOBAL_DAILY_GENERATION_CAP`.
  Pro Konto über `accounts.generation_limit` überschreibbar.
- Fehlgeschlagene Läufe, die Tripo nie angenommen hat, werden zurückgebucht.
- Rate-Limits für Login, Registrierung, Upload und Export (pro IP bzw. Konto).
- **Restlücke:** Wer viele E-Mail-Adressen hat, kann viele Konten anlegen. Dagegen helfen:
  `REGISTRATION_INVITE_CODE` (sofort nutzbar), E-Mail-Bestätigung (braucht einen Mailversand) und
  der globale Tagesdeckel als letzte Grenze für das Budget.

## 2. Backend-Plan für die neuen Funktionen

### 2.1 Datenmodell (Erweiterungen)

```
instances
  + nickname            varchar(24)        Spitzname der Kachel
  + story               text (≤ 2000)      Hintergrund, Markdown-light
  + show_source_photo   bool               Opt-in: Ursprungsfoto öffentlich
  + signature           jsonb              {kind: code|name|logo, text, logo_upload_id, corner}
  + geo_lat, geo_lon    numeric(9,6) null
  + geo_visibility      enum(hidden|district|approx|exact)   Standard: district
uploads
  + kind                enum(photo|logo|observation)
  + moderation_status   enum(pending|approved|rejected)
designs
  + signature_zone      jsonb              reservierte Ecke im Relief (wenn Signatur vorne)
```

Migrationen ab jetzt mit **Alembic** (die heutige Spalten-Ergänzung ist nur ein Dev-Behelf).

### 2.2 Signatur auf der Kachel (Code, Name oder Logo)

1. **Eingabe:** Code automatisch (`BT-XXXXXX`). Name ≤ 12 Zeichen (Einstrich-Schrift, z. B. Hershey,
   Zeichenhöhe 6–8 mm, Strich ≥ 1,2 mm). Logo als SVG oder freigestelltes PNG.
2. **Logo-Aufbereitung (Server):** SVG mit `resvg` rastern bzw. PNG-Alpha schwellen → Maske →
   morphologisches Öffnen, damit nichts feiner als 1 mm bleibt (FDM und Ton). Größe max. 20 × 20 mm.
3. **Geometrie:** Die Maske wird 1,2 mm tief in eine **Signaturzone** geprägt (auf der Matrize
   erhaben, gespiegelt). Damit das Muster nahtlos bleibt, wird die Zone über 3 mm weich in die
   Textur überblendet. Eine Prägung bricht die Periodizität **nur an dieser Stelle**, deshalb drei Optionen
   (bitte wählen):
   - a) **Ecke vorne** (wie das 8-mm-Herkunftszeichen im Brief): sichtbar, aber dezent.
   - b) **Unterkante** (die 40-mm-Stirnseite): unsichtbar in der Wand, lesbar abgenommen. Technisch über
     ein Einlege-Plättchen in der unteren Rahmenwand.
   - c) **Rückseite** (Brief-Standard): komplett unsichtbar.
4. **Pro Kachel oder pro Muster?** Die Prägung sitzt in der Matrize, also gilt sie für alle Abgüsse
   dieser Matrize. Eine kachelgenaue Nummer ist nur mit Wechsel-Plättchen (Setzkasten-Prinzip aus dem
   Brief) oder Punzen im Ton möglich.

### 2.3 Standort: GPS und Karte

- **Konflikt mit dem Brief:** Dort steht „Standorte nur grob“, wegen Schulen und Kindern. Vorschlag:
  - Speichern: optional exakt (Opt-in, Standard aus).
  - Öffentlich: `district` (nur Ortsname) oder `approx` (auf ~100 m gerundet). `exact` nur, wenn
    das Konto es ausdrücklich will, und nie für Schulen.
  - „Koordinaten kopieren“ liefert `lat, lon` und einen Google-Maps-Link `https://www.google.com/maps?q=lat,lon`.
- **Karte:** MapLibre GL JS (Open Source, ohne Key) mit monochromem Vektorstil (Protomaps
  „grayscale“ oder OpenFreeMap „positron“, selbst hostbar in der EU, kein Google-Tracking).
  Auf der Musterseite alle Kacheln als Punkte, Klick vergrößert die Karte als Overlay.
- Endpunkte: `GET /api/designs/{id}/locations` (gerundet je Sichtbarkeit),
  `PATCH /api/instances/{id}` (Spitzname, Geschichte, Standort; nur Besitzer).

### 2.4 Kachelseite

`/instances/BT-…`: Spitzname, Signatur-Vorschau, Geschichte, Ursprungsfoto (falls freigegeben),
Foto-Zeitleiste mit Vorher/Nachher-Slider, kleine Karte, Fotokarte (PDF).

### 2.5 Infrastruktur

| Baustein | Wahl | Warum |
|---|---|---|
| DB | PostgreSQL 16 + Alembic | schon im Compose |
| Dateien | S3 (MinIO lokal; EU-Anbieter in Produktion) | schon vorbereitet |
| Jobs | RQ + Redis | schon vorbereitet; Rate-Limits auch nach Redis verlagern |
| Mail | EU-SMTP-Dienst | E-Mail-Bestätigung, Passwort vergessen |
| Bilder | Thumbnails beim Upload (WebP 400/1200 px) | Galerie und Karte schnell |
| Moderation | Fotos `pending`, bis das Konto sie freigibt | Personen- und Datenschutz |
| Admin | Kontingente, Sperren, Tripo-Guthaben (`/v3/account/balance`) mit Warnung | Budget im Griff |
| Hosting | EU (z. B. Hetzner), HTTPS, `COOKIE_SECURE=true` | DSGVO |

## 3. Geometrie- und Befestigungsprüfung

| Thema | Befund | Vorschlag |
|---|---|---|
| Nahtlosigkeit | Höhe stetig, **aber Knick im feinen Band** (2–3× stärker als im Inneren) → im Streiflicht als Linie sichtbar | **behoben** (0.2.0): varianzerhaltende Überblendung mit halbversetzter Kopie, Knick jetzt ≈ 1×; als Prüfung und Test ergänzt |
| Wasserrinnen | Diagonal und starr, unabhängig vom Foto | siehe Abschnitt 4 (Moos-Nester) |
| Matrize | massiv 177 × 177 × 29 mm → ca. 0,6 kg PLA, lange Druckzeit | Hohlmatrize mit 3 mm Haut und Rippen |
| Rahmen | Wände nur durch Stifte und Zapfen gehalten; beim Stampfen von Beton können sie aufgehen | Eck-Klammern drucken oder Spanngurt empfehlen |
| **Schlüsselloch (Ton)** | **Ohne Hinterschnitt hält der Schraubenkopf nicht** | Optionen siehe Frage im Chat |
| Aufhängepolster | Beim Pressformen folgt die Rückseite der Vorderseite: Die Polster sind nicht eben | Rückenplatte als Abziehlehre für zwei ebene Polster (Ø 30) und den Randsteg |
| Beton-Rückenplatte, M6-Hülsen | fehlt (v1) | einplanen |
| Entlüftung (Stempel oben) | fehlt | Ø 1,2 mm an den tiefsten Stempelstellen |
| Adapter (Zaun, Schraube, Leiste) | fehlen als STL | Zaunadapter zuerst (Schulen) |
| Lizenz surfalize | **GPL**, unser Code ist MIT | als optionales Extra kennzeichnen oder ISO-Werte selbst rechnen |

## 4. Moos-Anbringung: Optionen (Bild: `docs/moss_options.png`)

- **A Diagonale Rinnen (heute):** Nach Jakubovskis 2025 verteilten durchgehende, schräge
  Booster-Formen das Wasser am besten. Sie sind aber geometrisch, unabhängig vom Foto und sehen technisch aus.
- **B Moos-Nester:** organisch verteilte Taschen (Blue-Noise auf dem Torus). Unten steil (eine kleine
  Ablage, die Moos hält, wenn die Kachel hängt), oben flach (dort läuft Wasser hinein). Die Taschen
  werden ohne Hinterschnitt entformt.
- **C Nester + Rinnsale:** wie B, dazu feine Rinnsale, die den **natürlichen Tälern des Fotos**
  folgen (kürzeste Wege auf dem Torus, bergauf teuer) und Regenwasser in die Nester leiten.
- Alle drei sind mathematisch periodisch auf dem Torus, deshalb ohne sichtbare Fuge
  (gemessen und getestet).
- Prototyp: `packages/biotile_geometry/moss.py`, noch nicht im Editor.

## 5. Nächste Schritte (Vorschlag, Reihenfolge)

1. **Live-Test Tripo** mit 3–5 echten Fotos planer Flächen und Fixtures aufzeichnen (Brief 7.6, größtes Risiko).
2. Moos-Variante festlegen und in den Editor bringen (Template + Regler: Anzahl, Größe, Rinnsale an/aus).
3. Befestigung festlegen und neu bauen (Rückenplatte als Lehre, Zaunadapter-STL).
4. Hohlmatrize und Rahmen-Klammern.
5. Signatur (Variante nach deiner Wahl), Spitzname, Geschichte.
6. Standort + monochrome Karte (nach deiner Entscheidung zur Genauigkeit).
7. Screencast-Rundgang und Asset-Board, eine Matrize drucken, eine Kachel pressen.
8. Danach (v1): Alembic, E-Mail-Bestätigung, Moderation, Mikroband, ArUco-Auswertung, Gaudí-Hexagon als druckbare Werkzeuge.
