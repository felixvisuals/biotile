# BIOTILE – Projektbrief für die Umsetzung mit Claude Code

> Arbeitstitel: **BIOTILE**. Stand: 03.10.2026. Sprache dieses Dokuments: Deutsch, Code und Bezeichner Englisch.
> Dieses Dokument ist die vollständige fachliche und technische Grundlage. Es enthält alle Entscheidungen, Begründungen, Zahlenwerte, Quellen, offenen Fragen und den Ideenspeicher aus der Konzeptphase.

---

## 0. Arbeitsanweisung an Claude Code

### 0.1 Prinzipien

1. **Keine API-Parameter erfinden.** Für die Tripo-API gelten ausschließlich die in Abschnitt 7 dokumentierten Parameter. Wo dort „verifizieren" steht, vor der Implementierung in der offiziellen Doku nachsehen (https://developers.tripo3d.ai/en/docs/introduction) und im Zweifel nachfragen.
2. **Mock-first.** Ein `TripoClient`-Interface mit zwei Implementierungen: `LiveTripoClient` und `MockTripoClient` (Record/Replay aus Fixtures in `tests/fixtures/tripo/`). Entwicklung und Tests laufen ohne Credit-Verbrauch. Umschalten per `TRIPO_MODE=mock|live`.
3. **Deterministische, versionierte Pipeline.** Gleiche Eingabe + gleiche Parameter + gleiche Seeds = gleiche Geometrie. Jede Pipeline-Änderung erhöht `PIPELINE_VERSION`; die Version wird an jedem Design gespeichert.
4. **Wissenschaftliche Konstanten zentral.** Alle Zahlenwerte aus der Literatur in `packages/biotile_geometry/constants.py`, jeweils mit Kommentar zur Quelle (Kurzzitat aus Abschnitt 17).
5. **API-Key nur serverseitig.** Der Tripo-Key erscheint nie im Browser, nie im Repo, nie in Logs. `.env.example` enthält nur den Platzhalter.
6. **Geometrie wird getestet**, nicht nur angeschaut (Tests in Abschnitt 13.3).
7. **Sprache der Oberfläche:** Englisch als Standard (internationale Jury), Deutsch als zweite Sprache (Schulen). i18n von Anfang an.
8. **Bei Konflikten zwischen diesem Dokument und einer naheliegenden Vereinfachung: nachfragen**, nicht stillschweigend abweichen.

### 0.2 Zeitkritischer Hinweis

Laut Wettbewerbsseite endet die Online-Einreichung am **05.10.2026 AoE (UTC−12)**, das entspricht **06.10.2026, 13:59 Uhr MESZ**. Bitte auf der Wettbewerbsseite gegenprüfen. Daraus folgt: Für die Einreichung zählt ausschließlich der **Hackathon-MVP** aus Abschnitt 14.1. Alles andere ist v1 oder v2.

---

## 1. Kontext: Tripothon S1

- Wettbewerb: **Tripothon S1** (Tripo3D / VAST), „The 1st World-Building Hackathon". Motto: „Build a world as a gift". Hier gelesen als: **Ein Geschenk für die Lebewesen der Stadt.**
- Online-Einreichung 15.09.–05.10.2026, Region **Europa**, Demo Day Paris 17.10.2026 (Barcelona TBD). Qualifikations-Jurierung 05.–25.10., Top-50-Bekanntgabe 25.10.
- Gewählter **Direction Track: App** (Web, AI-native Produkte, Kreativtools).
- **Tool Tracks** (0–3 möglich): **Tripo** (Pflicht für dieses Projekt), optional Heygears (Harzdruck), optional World Labs (v2). Tool-Track-Beiträge müssen das Tool tatsächlich nutzen, sonst Disqualifikation aus dem Track.
- Bewertung Direction Track: Kreativität 30 %, Vollständigkeit 25 %, Themenbezug 20 %, virales Potenzial 15 %, kommerzieller Wert 10 %.
- Bewertung Tool Track: erfinderische Tool-Nutzung 35 %, Tool-Synergie 25 %, Tool-Beitrag 20 %, Themenbezug 10 %, Breakout-Potenzial 10 %.
- **Pflichtabgaben:** (1) öffentliches Open-Source-Repo mit Code **und** Assets, klonbar; (2) Bildschirmaufnahme als Rundgang, kein Trailer-Schnitt; (3) Visual-Asset-Board (Schlüsselbilder, Turnarounds, Frames). Optional: öffentliches Build-Log.
- Offene Wettbewerbsfragen: Ob bestehender Code wiederverwendet werden darf, ist nicht geklärt (Ansprechpartner bei Tripo). Der Zuschnitt der Tool Tracks war bei letzter Prüfung noch nicht final.

---

## 2. Produktidee

### 2.1 In einem Satz

Eine Webapp, die aus einem Foto einer real besiedelten Naturoberfläche (oder aus einer Textbeschreibung) über die Tripo-API ein **druckbares Werkzeugset** (Matrize/Stempel, Gießrahmen, Rückenplatte) für genormte, bioreceptive Habitat-Kacheln erzeugt, und eine offene Datenbank, in der Schulen und Bürger:innen die aufgestellten Kacheln über Monate dokumentieren, sodass vergleichbare Freilanddaten zur Besiedlung verschiedener Oberflächengeometrien entstehen.

### 2.2 Das Geschenk-Narrativ

- Die Stadt bekommt eine Oberfläche zurück, die sie irgendwo zufällig hervorgebracht hat und die dort nachweislich besiedelt ist (abgeformte Rinde, Fels, Mauerfuge).
- Mit dem **Booster** (Abschnitt 5.8) wird die Kachel mit dem Leben der eigenen Nachbarschaft befüllt: lokale Bodenkruste, lokale Moossporen.
- Das Geschenk kommt ehrlich gesagt erst nach dem Wettbewerb an. Besiedlung braucht Monate (mit Booster) bis Jahre (ohne). Das wird offensiv kommuniziert, nicht kaschiert.
- Grundsatz: **Kunststoff ist Werkzeug, nie Habitat.** Kein gedrucktes Kunststoffteil bleibt dauerhaft draußen.

### 2.3 Ehrliche Abgrenzung zum Stand der Forschung

Was es **schon gibt**:
- Bioreceptive Betonpaneele mit gestalteter Geometrie, im Gewächshaus getestet (Mustafa et al. 2021).
- Freiland-Langzeitversuche mit Booster und Bewässerung (Jakubovskis 2025, 64 Paneele).
- Nachbau natürlicher Substrattopografien per additiver Fertigung zur Algenbesiedlung, aquatisch (PLOS ONE 2019).
- Bioreceptive Paneele an einer Grundschule in Südlondon mit Mehrstandortvergleich (Studio Biocene / Cruz).
- Keramisch gedruckte „Urban Reefs", auch ein Schulprojekt mit Mikroklimamessungen (Urban Reef, Rotterdam).
- Gedruckte, wiederverwendbare Recycling-Kunststoffformen für bioreceptive Paneele (Ecolve / Scape Agency).

Was **neu** ist:
- Offen, verteilt, von Laien generierte Designs in großer Zahl.
- Pipeline vom Foto bzw. Text zur gießbaren Werkzeuggeometrie, an publizierte Designrichtlinien gekoppelt.
- Standardisiertes Protokoll, standardisierte Kachel, offene Daten.
- Drei Designherkünfte als Versuchsgruppen: von der Natur abgeformt, von KI erfunden, nach Richtlinie konstruiert.
- Terrestrisch-urban, Schulen als Messnetz.

---

## 3. Wissenschaftliche Grundlage und Korrekturen

### 3.1 Kernbefunde, die in Code und Texte eingehen

- **Geometrie-Richtwerte (Mustafa et al. 2021, Abschnitt 4.2):** durchgehende Hindernisse „along the flow" in fließendem oder alternierendem Rhythmus; Makrotiefe maximal 20 mm bei H/W 0,2–0,3 (das ergibt **breite, flache Mulden von etwa 65–100 mm Breite**, keine schmalen Schlitze); Mikrorillen 5 mm tief. Paneel 3 scheiterte, weil seine Hindernisse quer zur Fließrichtung lagen und Wasser von den Mulden auf die Grate tropfte.
- **Betonrezeptur (Mustafa et al. 2021, Tabelle 1):** CEM III/B 32,5 N mit 75 % Hüttensand 300 kg/m³, Sand 0–4 mm 740 kg, Jurakies 5–8 mm 1142 kg, Wasser 180 kg (w/z 0,6), keine Nachbehandlung.
- **Formfehler (Mustafa et al. 2021, Abschnitt 4.1):** Silikon-Trennmittel hinterließ einen hydrophoben Film auf den gestalteten Paneelen; die ungeformten Referenzen saugten besser.
- **Verzögerer (Veeger et al. 2021):** Ein Oberflächenverzögerer verbesserte die Bioreceptivität am stärksten, weil er die verdichtete Zementschicht und Schalölreste entfernt; zweitstärkste Maßnahme war Knochenasche im Gemisch.
- **Freiland ≠ Labor (Jakubovskis 2025, Abschnitte 3 und 4):** Poröser Beton ohne Booster zeigte nach zwei Jahren keinerlei sichtbare Besiedlung. Moos entstand nur in Booster-Zonen (Altpapierpulpe + lokale Bodenkruste, ≥ 50 % Kruste), alle Paneele wurden per Tropfbewässerung feucht gehalten. Magnesiumphosphat-Proben, die im Labor mit *Chlorella* stark bewuchsen, zeigten im Freiland nichts. pH, Porosität und Rauheit korrelieren im Freiland schwächer mit Besiedlung als im Labor. Erste sichtbare Besiedlung unter günstigen Bedingungen nach etwa einem Jahr, dichter Algenbewuchs nach 2–5 Jahren. Gräser und die meisten Sedum-Versuche überlebten den ersten Winter nicht; am Ende dominierte Moos. Kontinuierliche, diagonale Booster-Formen verteilten Wasser am besten.
- **Feldkartierung urbaner Moose (Ecological Engineering 2024):** Oberflächenrauheit erklärte nur 2,4 % der Artenverteilung, direkte Sonne 1,9 %; beide signifikant. Gemessen wurde mit Profilkamm-Abdruck, abfotografiert, als Bitmap in einen Rauheitswert umgerechnet.
- **Skalenabhängigkeit (Klippenstudie):** Ein Rauheitsindex auf 1-cm-Skala war für Gefäßpflanzen am aussagekräftigsten; SfM-Photogrammetrie wird als Standardmethode empfohlen.
- **Nachbau natürlicher Topografien (PLOS ONE 2019):** Der Flächenkennwert Smr war robuster als Sa und Sv, weil sich Welligkeit beim Nachbau leichter reproduzieren lässt als Feinrauheit.
- **Mikrohabitat-Schwellen (Larrieu et al. 2018):** Rindentaschen zählen erst ab 1 cm Spaltbreite und 10 cm Tiefe (Fledermausgröße), Stammhöhlungen ab 10 cm Tiefe und Öffnung (Vogelgröße). Das sind Erfassungsgrenzen, keine biologischen Mindestmaße für Wirbellose. Folge: **Die Kachel adressiert Kryptogamen und Mikrofauna, nicht Wirbeltiere.**
- **Spaltrefugien (Loxosceles-Studie):** Getestet 3,2–21 mm, bevorzugt ab 6,4 bzw. 9 mm. Nur als Größenordnung, zwei nicht heimische Arten im Labor.

### 3.2 Korrekturen gegenüber früheren Annahmen

1. „Algen nach 8–12 Wochen" war ein Gewächshauswert. Im Freiland ohne Booster ist in einem Schuljahr voraussichtlich nichts sichtbar. Deshalb ist der Booster Kernfeature.
2. Geometrie ist **ein Faktor unter mehreren** (Ausrichtung, Feuchte, Inokulum), nicht der Hauptfaktor.
3. Magnesiumphosphat-Zement ist als Ausbaustufe gestrichen.
4. Die früher genannten Spaltklassen (1–3 mm Springschwänze und Milben, 5–8 mm Spinnen und Ohrwürmer, 15–20 mm Eidechsen) sind **Arbeitshypothesen**, nur die mittlere Klasse ist grob gestützt.
5. Die Neuheitsbehauptung „niemand hat natürliche Oberflächen abgeformt" ist falsch (PLOS ONE 2019, aquatisch). Abgrenzung siehe 2.3.
6. Quelleninkonsistenz: Studio Biocene datiert „Bioreceptive Design (Cruz, Beckett, ARQ)" auf 2013, die MDPI-Arbeit auf 2016. Vor Zitation prüfen.
7. Werbeaussage von Ecolve („Moos bindet pro m² so viel CO₂ wie ein ausgewachsener Baum") wird **nicht** übernommen. Jakubovskis beziffert Kryptogamendecken auf 17–103 g C/m²·a, Begrünung mit Blütenpflanzen auf 410–950 g C/m²·a.

### 3.3 Skalenlogik: Wer erzeugt welche Struktur?

| Skala | Biologische Funktion | Erzeugt durch |
|---|---|---|
| µm bis 0,1 mm | Anheftung von Sporen, Algenzellen, Biofilm | **Material**: Porosität, freigelegter Zuschlag, Auswaschen. Nicht der Stempel. |
| 0,5–3 mm | Rhizoid-Verankerung, Wasserfilme, Mikroarthropoden | Stempel in Ton oder Feinmörtel; feiner FDM- oder Harzdruck |
| 3–10 mm | Wasserhaltende Rillen, Boosterbetten, Spaltrefugien | Stempel |
| 10–20 mm | Taschen für Moospolster, Verschattung | Stempel (Obergrenze nach Mustafa et al.) |
| ≥ 100 mm | Höhlen für Wirbeltiere, Nisthilfen | Nicht in einer Kachel machbar |

**Physikalische Grenze:** Strukturen feiner als das Größtkorn kann Beton nicht abbilden. Bei 5–8 mm Kies sind 2-mm-Rillen unmöglich. Für Feindetail ist eine **Feinmörtel-Vorsatzschicht** (Sand 0–2 mm) auf grober Hinterfüllung Pflicht.

---

## 4. Hypothesen und Versuchsdesign

### 4.1 Hypothesen

- **H1 (Booster):** Kacheln mit Booster zeigen in der ersten Saison mehr sichtbare Besiedlung als identische Kacheln ohne Booster.
- **H2 (Designherkunft):** Abgeformte Naturoberflächen unterscheiden sich in der Besiedlung von KI-erfundenen, richtlinienbasierten und glatten Oberflächen.
- **H3 (Ausrichtung, Kontrollvariable):** Nordexponierte Kacheln werden schneller besiedelt.
- **H4 (explorativ):** Skalengetrennte Oberflächenmetriken hängen mit dem Besiedlungsgrad zusammen.

Empfehlung für eine spätere Publikation: Hypothesen vor Start der Hauptkohorte präregistrieren.

### 4.2 Versuchsfaktoren (alle als Datenbankfelder)

- Geometriemetriken (Abschnitt 8.5)
- `source_type`: `photo | text | procedural | hybrid`
- Booster ja/nein (gleiche Geometrie, Booster-Rinnen bleiben ggf. leer)
- Ausrichtung, Neigung, Höhe, Verschattung
- Material, Prozess, Behandlung (verzögert und ausgewaschen ja/nein)
- Bewässert ja/nein (Standard v1: nein)
- Wandtyp (v1: `versuch`)

### 4.3 Pflicht-Referenzkacheln in jeder Wand

- **REF-FLAT:** glatte Platte, Nullreferenz.
- **REF-GEO:** Geometrie nach Richtwerten (20 mm Makrotiefe, H/W 0,25, 5-mm-Rillen, along the flow).

Ohne beide sind Standorte nicht normierbar. Die App warnt, wenn eine Wand ohne beide angelegt wird.

### 4.4 Replikation

Empfehlung: jedes Design mindestens zweimal pro Wand, Positionen randomisiert. Die App bietet einen Randomisierungshelfer beim Wandlayout an.

### 4.5 Wandtyp v1: Versuchswand

- Jede Kachel bekommt nur ihren eigenen Regen, die Kacheln sind hydraulisch getrennt.
- **Vertikaler Mindestabstand zwischen Reihen: 50 mm**, damit Tropfwasser der oberen Kachel nicht auf die untere fällt.
- **Horizontaler Mindestabstand: 20 mm**, damit die Halbkanäle zweier Nachbarn keine gemeinsame Rinne bilden (sonst Kopplung über die Fuge).
- Bohrschablonen-Raster Versuchswand: **170 mm horizontal × 200 mm vertikal** (150 + 20 bzw. 150 + 50).
- Feld `wall_type = 'versuch'` wird schon jetzt geführt.

### 4.6 Vorbereitung Kaskadenwand (v2)

Kaskadenwand: Die Tropfnase der oberen Kachel steht über der Sammelrinne der unteren, Wasser läuft durch die ganze Wand. Mehr Bewuchs, aber hydraulische Kopplung (untere Kacheln bekommen mehr Wasser) und deshalb nur als Schauwand. Damit v2 ohne neue Kachelgeometrie auskommt, sind **schon in v1 fest definiert:** die Lage von Tropfnase und Sammelrinne relativ zu den Aufhängepunkten (Konstanten in `constants.py`). v2 braucht dann nur eine neue Bohrschablone mit festem Kaskadenabstand (horizontales Raster 154 mm = 150 + 4 mm Fuge) und eine Anleitung.

---

## 5. Physisches System

### 5.1 Formate und Bauraum

- Drucker-Bauräume: **Bambu Lab A1 mini 180 × 180 × 180 mm** (bindend), **Bambu Lab P1S 256 × 256 × 256 mm**. Weitere Profile frei definierbar.
- **Kachelmodul: 150 × 150 mm, Dicke 40 mm** (gemessen von der Rückseite bis zur Bezugsebene = höchste Reliefpunkte bzw. Randsteg).
- Größen: 1×1 (150 × 150), 2×1 (300 × 150), 2×2 (300 × 300). Großformate entstehen durch **mehrere Abdrücke derselben Matrize** in einem Registrierrahmen; die periodische Textur versteckt die Stöße. Kein segmentierter Großstempel.
- Gewicht Beton massiv 1×1: ca. 2,1 kg; 2×2: ca. 8,6 kg. Ton als Schale deutlich leichter.
- Matrizen-Registrierflansch: **4–5 mm** umlaufend (nicht mehr), wegen Bauraum bei Tonschwindung (5.5).

### 5.2 Werkzeugsystem: vier Teile, aus der App exportiert

1. **Matrize/Stempel:** Relieffläche + Registrierflansch + Registrierstifte. Dasselbe Teil dient als Stempel (Relief nach unten) oder als Matrize (Relief nach oben).
2. **Gießrahmen:** vier einzeln gedruckte Wände mit Steckverbindern, zerlegbar (statt Entformungsschräge, damit senkrechte Kachelkanten entstehen). Die Wände tragen die Kantenprofile: Rippe für die Sammelrinne (oben), Rippe für die Tropfnut (unten), Halbzylinder-Rippen für die Halbkanäle (Seiten). Passungsspiel Rahmen/Matrize 0,3 mm. Lange Wände ggf. diagonal drucken.
3. **Rückenplatte:** definiert die Rückseite. Enthält Positionierung der Aufhängepunkte, ID-Setzkasten, Positionierbohrungen für Kanalkerne. Bei „Matrize unten" als Deckel auf die offene Oberseite gedrückt, bei „Stempel oben" als Boden des Rahmens. Austauschbar je Material/Variante.
4. **Kleinwerkzeuge:** Schlüsselloch-Schneider (Ton), konische Kernstifte (Kanäle, Beton), Ziffernlettern für den Setzkasten (spiegelverkehrt), Ziffernpunzen (Ton), Registrierrahmen für Großformate.

Bei Ton dient der Rahmen zusätzlich als **Begrenzungs- und Schneideschablone**.

### 5.3 Prozessvarianten

Das Kraftproblem wird durch Umdrehen des Prozesses gelöst, nicht durch mehr Kraft. Begründung Stempel statt Walze: volle Relieftiefe (10–20 mm), auch nicht-periodische Designs möglich, und **harter Anschlag** (Flansch auf Rahmen) macht die Eindrucktiefe reproduzierbar. Ohne Anschlag wäre die Relieftiefe eine unkontrollierte Variable.

| Prozess | Material | Ablauf | Vor-/Nachteile |
|---|---|---|---|
| `press_mould` (Pressformen) | Ton | Tonplatte auf die Matrize legen, von hinten mit Fingern/Rollholz einarbeiten, Rahmen begrenzt, Rückseite folgt der Vorderseite | kaum Kraft, volle Tiefe, gleichmäßige Wandstärke (wichtig fürs Brennen); **Standard für Schulen** |
| `matrix_down` (Matrize unten) | Feinmörtel/Beton | Matrize mit Relief nach oben, Rahmen drauf, Verzögerer auf Matrize, Feinmörtel-Vorsatz, dann grobe Hinterfüllung einstampfen, Rückenplatte als Deckel, nach dem Entformen auswaschen | volle Tiefe, Schichtung ergibt sich, Luft entweicht nach oben; Schalhaut entsteht, wird durch Verzögerer + Auswaschen entfernt; **Standard für Beton** |
| `stamp_down` (Stempel oben) | Ton, sehr erdfeuchte Mischungen | Form füllen, Stempel mit Fäustel auf Rückplatte eindrücken bis Anschlag | keine Schalhaut; braucht Kraft, Entlüftungsbohrungen nötig |

Die Texturwalze ist gestrichen (nur noch denkbar für flache periodische Texturen).

### 5.4 Fertigungsstufen

- **Stufe 1 „Klassenzimmer":** Ton, `press_mould`, PLA-Matrize, Rahmen als Schablone, Trennmittel Speisestärke oder Talkum, Brennen im Schulbrennofen (oft in der Kunstabteilung vorhanden, sonst Keramikwerkstatt). Ungebrannter Ton nur für Innen-Demos.
- **Stufe 2 „Werkraum":** Feinmörtel/Beton, `matrix_down`, PETG- oder rPETG-Matrize, Rahmen, Rückenplatte, Rapsöl als Trennmittel (kein Silikonspray), Verzögerer + Auswaschen, Gewindehülsen als Aufhängepunkte.
- **Stufe 3 „Makerspace":** Druckmaster → Silikonmatrize (Shore A 40–60) → Feinbeton, für Serien und Hinterschneidungen. Bei Harzmastern Zinnsilikon verwenden oder Master vollständig nachhärten und versiegeln, weil frisch gedrucktes Harz Platinsilikon in der Vernetzung hemmen kann.

### 5.5 Kachelanatomie

#### 5.5.1 Vorderseite: Funktionsschicht + Texturschicht

Die Vorderseite entsteht aus zwei getrennt erzeugten, addierten Höhenfeldern.

**Funktionsschicht** (prozedural, garantierte Maße), Vorlagen:
- `diagonal_cascade`: durchgehende diagonale Rinnen als Boosterbetten (entspricht Jakubovskis' diagonalen Booster-Formen und dem „along the flow"-Prinzip).
- `terraces`: horizontale Stufen mit Überlauf zur nächsttieferen (analog zum Überlaufauslass der Rain Reefs).
- `serpentine`: maximale Fließweglänge.
- `none`: nur Textur.

Startwerte:
- Makromulden ≤ 20 mm tief, H/W 0,2–0,3 (breit und flach).
- Boosterrinnen 10–15 mm tief, 12–20 mm breit.
- **Rinnenabstand muss ganzzahliger Teiler von 150 mm sein** (75 / 50 / 37,5 mm), sonst kachelt das Muster nicht.
- **Ankerlöcher** im Rinnenboden: Ø 3–4 mm, 8–10 mm tief, Abstand ca. 20 mm. Ersatz für eine hinterschnittene Schwalbenschwanznut, die ein starrer Stempel nicht entformen kann; die Fasern der Papierpulpe verzahnen sich in den Löchern.
- Diagonalrinnen münden an den Seitenkanten in die Halbkanäle.

**Texturschicht:** Tripo- bzw. Fotorelief, periodisch gemacht, auf Meso- und Mikroband skaliert.

**Gewinn der Trennung:** Gleiche Form mit oder ohne Booster (Rinnen leer lassen) → H1 ohne zweite Geometrie testbar. Textur gegen Funktion trennbar über `none`.

**Herkunftszeichen (optional):** kleines Glyph (ca. 8 × 8 mm) in einer Ecke, markiert das Originaldesign.

#### 5.5.2 Ränder

- **Oben – Sammelrinne:** Rinne in der Oberseite, leicht nach innen geneigt, leitet Wasser von oben ins Feld (Jakubovskis: der obere Bereich einer Wand bekommt Wasser von der Fläche darüber). Geformt durch eine Rippe an der oberen Rahmenwand. Startwert 8 mm breit, 6 mm tief.
- **Unten – Tropfnut:** Nut in der Unterseite nahe der Vorderkante, damit Wasser nicht zur Rückseite kriecht. Startwert 4 × 4 mm, 6 mm hinter der Vorderfläche.
- **Seiten – Halbkanäle:** senkrechte Halbzylinder Ø 8 mm (r = 4 mm), ca. 12 mm hinter der Vorderfläche. In der Versuchswand offene Randrinnen, in der Kaskadenwand (v2) bilden zwei Nachbarn eine volle Rinne.
- **Fuge:** Nennmaß 4 mm (Kaskade) bzw. ≥ 20 mm Abstand (Versuchswand).

#### 5.5.3 Randmodus

- `periodic` (Standard): Relief läuft bis an die Kante, Höhenfeld periodisch, Muster läuft über Fugen hinweg weiter. Kanten nur 2 mm gefast.
- `framed`: 10-mm-Randband mit Auslauf auf null über die letzten 5 mm; jede Kachel in sich geschlossen.

#### 5.5.4 Rückseite

- **Ton:** Schalenkachel, gleichmäßige Wandstärke ca. 12–15 mm (ergibt sich beim Pressformen von selbst), plus flacher Randsteg und zwei flache Polster für die Aufhängepunkte. Grund: massiver 40-mm-Ton ist beim Trocknen und Brennen rissgefährdet. Konkrete Grenzwerte beim Tonlieferanten prüfen.
- **Beton:** massiv 40 mm, oder optional Waffelrückseite zur Gewichtsreduktion.
- Die Hohlräume der Schalen- bzw. Waffelrückseite dienen zugleich als **trockener Rückraum für Wirbellose** (vorne feucht für Moos, hinten trocken als Unterschlupf).
- **Randsteg:** umlaufend 10 mm breit, Auflage- und notfalls Klebefläche.

#### 5.5.5 Kanäle (Option)

- `none` (Standard MVP), `edge_half` (Halbkanäle an den Seiten, Standard v1), `through` (Durchgangskanäle, Versuchsvariante).
- Durchgangskanäle: Ø 6–8 mm, **5–10° Gefälle nach vorne** (Regen läuft heraus), münden in die Rückseitenzellen. Ton: ausbrennende Papierhalme oder Schilfstängel als Opferkerne. Beton: geölte konische Kernstifte, positioniert durch Bohrungen in der Rückenplatte, nach dem Ansteifen gezogen.
- Zweck: Feuchteaustausch, Zugang zum Rückraum, später (v2) kapillare Speisung aus einem Rückreservoir oder feuchten Filz, um Sommerferien ohne Gießen zu überbrücken.
- Für Wildbienen sind die Kanäle bei 12–15 mm Wandstärke viel zu kurz. Nicht als Nisthilfe bewerben.
- Risiken: Regen läuft durch statt gehalten zu werden, Frost, Querschnittsschwächung. **An Gebäudewänden ohne hinterlüftete Ebene ausgeschlossen.** Kanäle dürfen die Aufhängepunkte nicht schneiden (App prüft).

#### 5.5.6 ID

- Auf der **Rückseite**, nicht vorne (stört sonst das nahtlose Muster).
- Beton: **Setzkasten** in der Rückenplatte, in den einzeln gedruckte, spiegelverkehrte Ziffernlettern eingesetzt werden (Prinzip Bleisatz).
- Ton: Ziffernpunzen zum Eindrücken.
- Zeichenhöhe 10 mm, Tiefe 1,5 mm.
- Bei Monitoringfotos übernimmt die Referenzkarte die Identifikation (Abschnitt 10).

### 5.6 Maße, Toleranzen, Regeln (alle in `constants.py`)

| Parameter | Wert | Hinweis |
|---|---|---|
| Modul | 150 × 150 mm | Fertigmaß |
| Dicke | 40 mm | |
| Makrotiefe | 0–20 mm, Standard 15 | H/W 0,2–0,3 |
| Mesotiefe (Rillen) | 0–5 mm, Standard 4 | |
| Mikrotiefe | 0–1,0 mm, Standard 0,6 | v1 aus Normal-Map |
| Mindestmaterialstärke unter tiefster Reliefstelle | 12 mm Ton, 15 mm Beton | App warnt/blockiert |
| Entformungsschräge Relief-Flanken | ≥ 3–5° bei starren Stempeln (max. Flankenwinkel 85°), Silikon bis 90° | |
| Entlüftungsbohrungen (nur `stamp_down`) | Ø 1–1,5 mm an tiefsten Stempelstellen | sonst Unterdruck beim Ziehen |
| Registrierflansch | 4–5 mm | |
| Passungsspiel | 0,3 mm | |
| Halbkanal | Ø 8 mm | |
| Sammelrinne | 8 × 6 mm | |
| Tropfnut | 4 × 4 mm, 6 mm hinter Front | |
| Randsteg | 10 mm | |
| Aufhängepunkte | 2, Achsabstand 100 mm, 30 mm unter Oberkante | Fertigmaß |
| Ankerlöcher | Ø 3–4 mm, 8–10 mm tief | |
| Rinnenabstand | 75 / 50 / 37,5 mm | Teiler von 150 |

**Tonschwindung (kritisch):** Ton schwindet vom nassen bis zum gebrannten Zustand je nach Masse grob 8–12 %. Werkzeuge für Ton werden um den Faktor `s = 1 / (1 − shrink)` vergrößert, sonst sind die Kacheln am Ende ca. 135 mm groß, passen nicht ins Raster, und die Aufhängepunkte treffen die Adapter nicht.
- Feld `shrink_pct` je Tonmasse, Standard 10 % (nur Platzhalter), mit Anleitung zur Messung an einem Probestab.
- **Bauraum-Folge:** bei 10 % → 166,7 mm Relieffläche; mit 4-mm-Flansch 174,7 mm (passt A1 mini). Bei Massen > ca. 11 % auf P1S ausweichen oder Matrize teilen. Die App prüft gegen das gewählte Druckerprofil.
- Beton schwindet vernachlässigbar (`shrink_pct = 0`).

### 5.7 Befestigung: eine Schnittstelle, viele Adapter

Grundsatz: **reversibel vor dauerhaft.** Abnehmbare Kacheln lassen sich wiegen (Wasserrückhalt) und unter Standardbedingungen fotografieren.

**Die Schnittstelle (v1, für alle Kacheln gleich):** zwei Aufhängepunkte, Achsabstand 100 mm, 30 mm unter der Oberkante, auf flachen Polstern (Ø ≥ 30 mm), plus umlaufender Randsteg 10 mm.

**Ausführung je Material** (Korrektur gegenüber früherer Planung: Ein klassisches Schlüsselloch ist hinterschnitten und lässt sich nicht aus einem starren Rückenplatten-Dorn entformen):
- **Ton:** Schlüssellöcher, im lederharten Zustand mit dem gedruckten Schlüsselloch-Schneider geschnitten (Kopfbohrung Ø 10 mm, Schlitz 5,5 mm breit, ca. 10 mm lang nach oben, Tasche 6 mm tief). Kein Metall eingießen (Brennschwindung).
- **Beton:** zwei einbetonierte Edelstahl-Gewindehülsen M6, positioniert durch die Rückenplatte.

**Adapter** (dauerhaft in Edelstahl; im Hackathon-Prototyp PETG zulässig, mit Hinweis):
- `screw`: direkt in Wand oder Gestell; druckbare Bohrschablone als PDF (Raster Versuchswand 170 × 200 mm).
- `fence`: Flachstahl mit zwei Befestigungen für die Aufhängepunkte und zwei Haken über den horizontalen Doppeldraht von Doppelstabmattenzäunen (an fast jeder Schule vorhanden, Maschenweite üblicherweise 50 × 200 mm, vor Ort nachmessen). Genehmigungsfrei auf Schulgelände. **Favorit für Schulen.**
- `rail`: Z-Leiste mit zwei Befestigungen, für Testwände.
- `post` (v2): Bandschelle bzw. Rohrschelle nach IVZ-Norm mit Halteblech.
- Schrauben an Terrakotta immer mit Unterlegscheibe + Gummischeibe gegen Abplatzen. Schrauben Edelstahl A2/A4.
- Kleben: nur mineralischer Fliesenkleber auf mineralischem Untergrund, irreversibel, nicht empfohlen.
- Stapelvarianten (Trockenmauer, Gabione) widersprechen Sammelrinne und Tropfnut → eigene Variante in v2.
- An Gebäudewänden und öffentlicher Infrastruktur: genehmigungspflichtig.

### 5.8 Booster

- Rezeptur nach Jakubovskis: Altpapierpulpe + lokale Bodenkruste, **mindestens 50 % Kruste**. Lokale Kruste enthält einheimische Bakterien, Moos-, Pilz- und Flechtensporen, die ans Lokalklima angepasst sind.
- Wird in die Boosterrinnen eingebracht, Ankerlöcher halten ihn.
- Eigene Datenfelder: Rezeptur, Herkunft (grob), Datum.
- **Sammelregeln für Schulen:** nur kleine Mengen, nur von schuleigenen Flächen, Pflasterfugen, Mauern; nicht in Schutzgebieten. Nach Kenntnisstand sind alle Torfmoose (*Sphagnum*) und *Leucobryum glaucum* nach Bundesartenschutzverordnung besonders geschützt → **vor Veröffentlichung von Schulmaterial prüfen.**
- Samen werden nicht versprochen (Gräser und die meisten Sedum überlebten bei Jakubovskis den ersten Winter nicht). Moosbrei mit Buttermilch ist nur im Gewächshaus belegt (Mustafa et al.), Freilandwirkung unbelegt.
- Hypothese für später: Vorkonditionierung der Kachel in biomolekülreicher Lösung (Jakubovskis, Ausblick).

### 5.9 Materialien

**Werkzeug:**

| Material | Eignung | Vorsicht |
|---|---|---|
| PLA | Matrizen für Ton, günstig, einfach | spröde; in Beton nur wenige Abdrücke |
| PETG / rPETG | Matrizen, Rahmen, Rückenplatten für Mörtel; robust | Trennmittel nötig |
| TPU 95A | flexible Stempel, Hinterschneidungen | schwerer zu drucken; Druckerprofil vorher testen |
| Harz | Feindetail-Master (Heygears) | unausgehärtetes Harz hautsensibilisierend → nicht für Schüler:innen; hemmt Platinsilikon |
| Silikon | beste Entformung, langlebig | teuer, Wartezeit |

**Trennmittel:** Ton: Speisestärke/Talkum. Beton: Rapsöl bzw. pflanzliches Schalöl; **kein Silikonspray**. (Hinweis mit Vorbehalt: Ein Abstract-Fragment einer marinen Studie berichtet, pflanzliches Schalöl habe Besiedlung gefördert; Quelle unklar, Verifikation empfohlen.)

**Kachel:**

| Material | pH / Handling | Haltbarkeit | Einschätzung |
|---|---|---|---|
| Gebrannter Ton | schwach alkalisch bis neutral, unproblematisch | frostgefährdet bei zu niedrigem Brand | **Schulstandard**; auch Urban Reef arbeitet keramisch |
| Beton CEM III/B mit Feinmörtel-Vorsatz | frisch stark alkalisch → Handschuhe, Schutzbrille | gut, frostfest | Stufe 2/3 |
| Kalkmörtel NHL | frisch alkalisch, karbonatisiert | mittel | Alternative |
| Ungebrannter Lehm | unproblematisch | nicht regenfest | nur innen/überdacht |
| Gips | unproblematisch | **nicht außentauglich** | nur Modelle; in der App explizit warnen |
| Geopolymer | aggressive Aktivatoren | gut | nicht für Schulen |
| Magnesiumphosphat-Zement | – | – | gestrichen (Laborerfolg, Feldmisserfolg) |

**Booster:** siehe 5.8.

### 5.10 Pfostenmanschetten: v2

- Begründung für Verschiebung: zylindrische Flächen lassen sich nicht flach stempeln (gekrümmte Matrize oder gewickelte Tonplatte nötig = eigenes Werkzeug), Zylinder verziehen beim Brennen stärker, Mikroklima schwach (nur Nordseite), Genehmigung nur an schuleigenen Pfosten.
- Ausgeschlossen: Kunststoff als Habitatoberfläche (hydrophob, unporös, Mikroplastik, Kommunikationsproblem), Laternen (Licht zieht nachts Insekten an = ökologische Falle), öffentliche Verkehrszeichenpfosten (Sondernutzung, Sicht, Wartung).
- Wert: 360°-Ausrichtungstransekt an einem Objekt.
- v2-Form: mineralische Halbschalen (Ton oder Feinbeton) aus gedruckter Form mit Kern bzw. über Schablone gewickelte Tonplatte, Edelstahl-Spannband oder IVZ-Schelle, nur schuleigene Holzpfosten, Pergolen, Zaunpfosten. Grobwert: 200 mm hohe Schale, 20 mm Wand auf 60-mm-Pfosten ≈ 2 kg. Rohrpfosten-Standarddurchmesser 60 und 76 mm, Schellen auch für 48 mm.
- **Jetzt schon vorbereitet:** Texturperiode als Parameter `texture_period_mm` (Standard 150). Eine Textur mit Periode U/n lässt sich später um einen Pfosten mit Außenumfang U wickeln. Beispiel: 2 × 150 mm = 300 mm Umfang → 95,5 mm Außendurchmesser → auf 60-mm-Pfosten ca. 18 mm Wand.

---

## 6. Software-Architektur

### 6.1 Stack

- **Backend:** Python 3.11, **FastAPI**; Worker mit **RQ** (einfacher) oder Celery, Redis als Queue.
- **Geometrie:** numpy, scipy, **trimesh**, **manifold3d** (robuste Booleans), Pillow, OpenCV (Monitoring-Auswertung, ArUco), **surfalize** (ISO 25178, Version pinnen), fast-simplification oder pyfqmr (Mesh-Dezimierung), optional embreex für schnelles Raycasting.
- **PDF:** reportlab (Referenzkarte, Bohrschablone, Anleitung).
- **DB:** PostgreSQL. PostGIS nicht nötig (Standorte grob).
- **Objektspeicher:** S3-kompatibel, lokal MinIO.
- **Frontend:** React + Vite + TypeScript, **three.js** (Reliefvorschau), Tailwind, i18n (react-i18next), Englisch Standard, Deutsch zweite Sprache.
- **Deployment:** Docker Compose, EU-Hosting.
- **Designsystem:** Neo-Brutalismus: Space Grotesk, harte schwarze Rahmen und Schatten, cremefarbener Hintergrund, Akzente Rot/Gelb/Violett.

### 6.2 Dienste

- `api`: REST, Auth, Accounts, Designs, Instanzen, Wände, Beobachtungen, Dateien.
- `worker`: Tripo-Jobs, Relief-Pipeline, Werkzeuggenerierung, Metriken, Monitoring-Bildauswertung, PDF-Erzeugung.
- `web`: Oberfläche.
- `minio`, `postgres`, `redis`.

---

## 7. Tripo-Integration

### 7.1 Grundlagen (aus der offiziellen v3-Doku, vom Nutzer bereitgestellt)

- Base URL: `https://openapi.tripo3d.ai/v3`
- Header: `Authorization: Bearer {api_key}`
- Erfolg: `{ "code": 0, "data": {...} }`; Fehler: `{ "code": <int>, "message": "...", "suggestion": "..." }`
- Asynchron: Task anlegen → `task_id` → Polling `GET /v3/tasks/{task_id}`; Status `queued | running | success | failed | cancelled`, Feld `progress`.
- Ergebnis: `data.output.model_url` (GLB), `data.output.rendered_image_url`, `credits_consumed`.
- Weitere Endpunkte: `POST /v3/files` (Upload), `POST /v3/generation/text-to-model`, `POST /v3/generation/image-to-model`, `POST /v3/generation/multiview-to-model`, `POST /v3/generation/text-to-image`, `POST /v3/generation/image-to-image`, `POST /v3/models/convert`, `POST /v3/mesh/decimate`, `POST /v3/tasks/list`, `GET /v3/account/balance`.

### 7.2 Upload

`POST /v3/files` → `file_token`. **Request-Schema vor Implementierung in der Doku verifizieren.** Clientseitige Validierung: PNG/JPEG/WebP, max. 20 MB, empfohlen ≥ 256 × 256 px.

### 7.3 Image-to-Model, Standard-Request

```json
{
  "input": "file_abc123",
  "model": "v3.1-20260211",
  "texture": true,
  "pbr": true,
  "texture_version": "v3.5-20260815",
  "texture_quality": "extreme",
  "delight": true,
  "texture_alignment": "geometry",
  "geometry_quality": "detailed",
  "face_limit": 1000000,
  "model_seed": 1234567,
  "texture_seed": 1234567,
  "enable_image_autofix": false,
  "export_uv": true
}
```

Begründungen:
- `pbr: true`: Die Normal-Map liefert die Mikrostruktur, die das Mesh nicht auflöst. Makro aus Geometrie, Mikro aus Normal-Map. Das ist der erfinderische Kern der Tool-Nutzung.
- `delight: true`: entfernt eingebackenes Licht; sonst werden Schlagschatten in Außenfotos zu Scheingeometrie. Wirkt nur mit Texturmodell `v3.5-20260815`.
- `model_seed`, `texture_seed`: werden gespeichert und mit der Design-ID versioniert → Reproduzierbarkeit.
- `enable_image_autofix: false`: KI-Ergänzung könnte Details erfinden; für wissenschaftliche Treue aus. Als Option im UI.
- `face_limit`: v3.1 Standard bis 1,5 Mio., Ultra (`geometry_quality: detailed`) bis 2 Mio. Dreiecke.
- **Nicht setzen:** `export_orientation` (Doku warnt: Nachverarbeitung liefert dann falsch orientierte Ergebnisse ohne Fehlermeldung; Orientierung am Ende über `/v3/models/convert`), `compress` (volles Mesh nötig), `quad` (erzwingt FBX), `generate_parts` (unverträglich mit `texture`/`pbr`), `auto_size` (wir normieren selbst).

### 7.4 Text-Modus

Aus der älteren offiziellen Doku (H3-Linie, `docs.tripo3d.ai`): Prompt max. 1024 Zeichen, Negativ-Prompt max. 255 Zeichen, eigener `image_seed` für den internen Bildschritt; Modellversionen `v3.1-20260211`, `v3.0-20250812`. Ein Drittanbieter nennt 1024 statt 255 Zeichen für den Negativ-Prompt; es gilt die offizielle Angabe. **Parameternamen für `/v3/generation/text-to-model` und `/v3/generation/text-to-image` in der v3-Doku verifizieren.**

Wege, in Reihenfolge der Empfehlung:
1. **Zweistufig mit Prüfpunkt (Standard):** `text-to-image` → Bild anzeigen, Nutzer akzeptiert oder verwirft → `image-to-model` mit `input = <task_id>` (laut v3-Doku zulässig). Spart Credits, eignet sich als Prompt-Workshop.
2. **Hybrid:** Nutzer beschreibt Ziel und Ort in natürlicher Sprache („für Moos an einer schattigen Nordwand, mit Spalten für Asseln"). Ein LLM übersetzt in Pipeline-Parameter + Tripo-Prompt. Funktionsmerkmale mit exakten Maßen prozedural (Funktionsschicht), Tripo liefert organische Variation (Texturschicht). `source_type = 'hybrid'`.
3. **Direkt `text-to-model`:** schnell, aber objekthafte Geometrie mit abgerundeten Kanten; funktioniert, weil nur das obere Höhenfeld verwendet wird.

Prompt-Muster: `square flat stone slab, top-down orthographic view, deeply weathered sandstone with honeycomb tafoni cavities, strong relief, even diffuse lighting`. Negativ: `statue, sphere, character, text, logo, smooth, glossy`. Je Oberflächentyp der Bibliothek (Abschnitt 16) eine Prompt-Vorlage hinterlegen.

### 7.5 Polling, Fehler, Budget

- Polling mit exponentiellem Backoff: Start 2 s, Deckel 15 s, Timeout 10 min.
- `2010` (Insufficient credits) → eigene Nutzermeldung, Account-Kontingent, Admin-Alarm.
- `1004` (ungültige Parameterkombination, z. B. `texture_quality: fast` ohne `texture_version v3.5-20260815`, oder `generate_parts` mit Textur) → nicht still auf Standard zurückfallen.
- `failed` → Task-ID, Rohantwort, Eingabe aufbewahren.
- `credits_consumed` je Job protokollieren; `GET /v3/account/balance` periodisch; Kontingent je Account.
- `POST /v3/tasks/list` für Batch-Status im Dashboard.

### 7.6 Risiko und Fallback

Zentrales technisches Risiko: Ob Bild-zu-3D bei planen Felsflächen brauchbare Geometrie liefert, ist offen. **Als Erstes testen.** Fallbacks, die Tripo weiter nutzen:
1. Nur die PBR-Normal-Map verwenden, Makrorelief aus deren Integration.
2. Zweigleisig: Tripo für objekthafte Proben (Totholz, Rinde am Stamm, Wurzelanlauf), monokulare Tiefenschätzung für plane Flächen. **Offen dokumentieren, welcher Pfad wann verwendet wird.**

---

## 8. Relief- und Werkzeug-Pipeline

### 8.1 Eingabewege

| Methode | Status | Bemerkung |
|---|---|---|
| Einzelfoto → Tripo | **MVP** | frontal, diffuses Licht, keine Schlagschatten, Maßstab im Bild |
| Text → Bild → Tripo | v1 | zweistufig mit Prüfpunkt |
| Hybrid (LLM → Parameter + Prompt) | v1 | |
| Multiview → Tripo | v2 | 3–4 Fotos desselben Ausschnitts |
| Photometric Stereo | v2 | feste Kamera, 4–8 Fotos mit wechselnder Lichtrichtung (Handylampe im Dunkeln) → Normalenkarte → Höhenfeld; für mm-Relief sehr gut, braucht Stativ und Dunkelheit |
| Photogrammetrie (SfM) | v2 | Handyvideo, metrisch mit Maßstab |
| Monokulare Tiefenschätzung | v1 (Fallback/Vorschau) | relative Tiefe, glättet/erfindet auf feinen Texturen |
| Profilkamm-Abdruck | v1 (Messung, nicht Design) | wie in der Moos-Feldstudie; metrisch, nur 2D |
| Smartphone-LiDAR | – | für mm-Texturen zu grob |

### 8.2 Pipeline-Schritte

1. **Eingang validieren**, Upload, Tripo-Job (Abschnitt 7).
2. **GLB laden** (Mesh + PBR-Maps; Normal-Map aus `normalTexture`).
3. **Ausrichten:** dominante Ebene per PCA oder RANSAC, Normale auf +Z.
4. **Höhenfeld rastern:** orthografisch, intern 2048 × 2048 über die Kachelfläche (≈ 0,07 mm/px), pro Zelle maximaler Z-Wert (ein Stempel kann ohnehin keine Hinterschneidung). Umsetzung per Raycasting (trimesh + embreex) oder orthografischem Depth-Render.
5. **Detrend:** Polynomfit 2. Ordnung abziehen.
6. **Periodisch machen** (Randmodus `periodic`): Periodic-plus-Smooth-Zerlegung nach Moisan (2011); Alternative bei Artefakten: Gradient-Domain-Blending an den Rändern. Periode = `texture_period_mm`.
7. **Bandtrennung in drei Stufen:** Gauß-Tiefpass → Makro; Residuum → Meso; Normal-Map per Poisson- oder Frankot-Chellappa-Integration → Mikro, hochpassgefiltert. (MVP: nur Makro + Meso aus dem Mesh; Mikro aus Normal-Map ab v1, weil dafür die Normal-Map über UV pro Rasterpunkt abgetastet werden muss.)
8. **Skalierung** je Band (Regler im UI, Defaults Abschnitt 5.6).
9. **Anisotropie:** Hauptrichtung aus 2D-FFT-Leistungsspektrum; Rotation, sodass die Hauptstruktur in Einbaulage „along the flow" liegt. Umschalter `auto_along_flow | cross | none`.
10. **Funktionsschicht addieren** (Vorlage, Abschnitt 5.5.1), periodisch zur Texturperiode.
11. **Entformbarkeitsprüfung:** maximaler Flankenwinkel je Werkzeugmaterial; morphologisches Öffnen mit kegelförmigem Strukturelement.
12. **Ränder:** `periodic` (2-mm-Fase) oder `framed` (Randband + Auslauf); Sammelrinne, Tropfnut, Halbkanäle kommen über die Rahmenwände.
13. **Mindestmaterialstärke prüfen** (12 mm Ton / 15 mm Beton).
14. **Schwindmaß anwenden** (Ton).
15. **Werkzeuge erzeugen:**
    - Matrize: Höhenfeld → Mesh (Gitter-Triangulierung + Seitenwände + Boden → wasserdicht), invertiert für Stempelnutzung bzw. direkt für Matrizennutzung (Prozess bestimmt Vorzeichen), Flansch, Registrierstifte, ggf. Entlüftungsbohrungen.
    - Rahmen: vier parametrische Wände (manifold3d), Rippen für Sammelrinne/Tropfnut/Halbkanäle, Eckverbinder.
    - Rückenplatte: je Material (Ton: Schablone mit Schneidmarken für Schlüssellöcher; Beton: Positionierung Gewindehülsen), Setzkasten, Kernbohrungen.
    - Kleinwerkzeuge: Schlüsselloch-Schneider, Kernstifte, Ziffernlettern, Registrierrahmen.
16. **Mesh-Export:** für Export auf 0,2 mm Raster neu triangulieren und per Quadric-Dezimierung auf ≤ 500 k Dreiecke reduzieren (FDM-Düse 0,4 mm löst Feineres ohnehin nicht auf; volle Auflösung ergäbe Hunderte MB STL). STL und 3MF.
17. **Bauraum-Check** gegen Druckerprofil.
18. **Metriken berechnen** (8.5) auf dem intern hoch aufgelösten Höhenfeld.
19. **Paket schnüren:** ZIP mit allen STL/3MF, Höhenfeld (PNG 16 bit + NPY), Vorschau-Renders, PDF-Anleitung, Bohrschablone, Referenzkarte, `design.json` (alle Parameter, Seeds, Versionen, Lizenz).

### 8.3 Druckhinweise im Paket

- Matrizen mit 0,08–0,12 mm Schichthöhe drucken; Schichtlinien erzeugen sonst eine horizontale Anisotropie, die das Messergebnis verfälschen kann. Designs mit Mikroanteil < 1 mm besser in Harz (Heygears).
- rPETG bevorzugen, wo verfügbar.

### 8.4 Nahtlosigkeits-Vorschau

Im Editor eine **3 × 3-Kachelvorschau**, damit Nahtlosigkeit sichtbar geprüft werden kann. Automatischer Test: linke/rechte und obere/untere Randzeile des Höhenfelds stimmen innerhalb Toleranz überein.

### 8.5 Metriken

- **ISO 25178** über surfalize (Version pinnen; Paket ist laut Autor frühes Projekt mit instabiler API), Validierung einzelner Werte mit Gwyddion: Sa, Sq, Sz, Sp, Sv, Ssk, Sku, Sdr, Sdq, Smr, Sk, Spk, Svk.
- **Skalengetrennt:** jeweils nach Filterung mit 1, 5, 10, 20 mm Grenzwellenlänge.
- **Eigene Kennwerte:** Taschenvolumen pro Fläche (potenzieller Wasserrückhalt), mittleres H/W der Makromulden, Anisotropie-Index + Hauptrichtung, Überhangsanteil (vor Entformungskorrektur), Spaltbreitenverteilung in den Hypothesenklassen 1–3 / 5–8 / 15–20 mm, Fließweglänge der Funktionsschicht.
- Annahme dokumentieren: Druck überträgt Welligkeit gut, Feinrauheit schlecht.

---

## 9. Datenmodell

### 9.1 `accounts`

`id`, `type` (`school | project | researcher | admin`), `name`, `region_coarse`, `contact_email` (Lehrkraft/Verantwortliche), `credit_quota`, `credits_used`, `created_at`. **Keine Einzelkonten für Schüler:innen.**

### 9.2 `designs`

`id` (`BT-D-XXXXXX`), `slug`, `title`, `description`, `author_account_id`, `parent_design_id` (Abstammung), `is_original`, `source_type` (`photo | text | procedural | hybrid`), `capture_method` (`single_photo | multiview | photometric_stereo | photogrammetry | depth_estimation | text`), `surface_type` (Bibliothek), `source_photo_key`, `source_prompt`, `source_negative_prompt`, `tripo_jobs` (FK-Liste), `tripo_model_version`, `tripo_texture_version`, `model_seed`, `texture_seed`, `image_seed`, `pipeline_version`, `pipeline_params` (JSONB), `functional_template` + Parameter, `edge_mode` (`periodic | framed`), `texture_period_mm`, `orientation_mode`, `interface_version`, `metrics` (JSONB), `files` (JSONB: Matrize, Rahmenwände, Rückenplatten je Material, Kleinwerkzeuge, Höhenfeld, Renders, PDFs, `design.json`), `license`, `status` (`draft | published | hidden`), `created_at`.

### 9.3 `walls`

`id`, `account_id`, `wall_type` (`versuch`; später `kaskade`), `location_coarse`, `orientation_deg`, `inclination_deg`, `gap_horizontal_mm`, `gap_vertical_mm`, `has_ref_flat`, `has_ref_geo`, `irrigated` (bool), `photo_key`, `created_at`.

### 9.4 `instances` (einzelne Kacheln)

`id` (`BT-XXXXXX-NNN`), `design_id`, `account_id`, `wall_id`, `position_row`, `position_col`, `format` (`1x1 | 2x1 | 2x2`), `material` (`ton | beton | kalk | lehm`), `material_details` (Mischung, Tonmasse, `shrink_pct`, Brenntemperatur), `process` (`press_mould | matrix_down | stamp_down`), `stage` (1/2/3), `tool_material`, `release_agent`, `retarder_washed` (bool), `back_type` (`shell | solid | waffle`), `channels` (`none | edge_half | through`), `booster` (bool), `booster_recipe`, `booster_source_coarse`, `booster_date`, `mounting_adapter` (`screw | fence | rail | post`), `cast_date`, `installed_date`, `orientation_deg` (**Pflicht**), `inclination_deg`, `height_above_ground_m`, `shading` (`full_sun | partial | shade | deep_shade`), `substrate`, `photo_installed_key`, `status` (`active | removed | destroyed`), `notes`.

Ohne Ausrichtung ist der Datensatz wertlos (Nord- und Südseite bekommen völlig verschiedene Organismengruppen).

### 9.5 `observations`

`id`, `instance_id`, `observed_at`, `photo_key`, `card_detected` (bool), `green_fraction`, `dark_fraction` (Proxy für Pilzverfärbung), `color_metrics` (JSONB), `weight_g` (optional), `species` (Array aus `{name, taxon_ref?, group: moss|lichen|algae|fungus|invertebrate|plant, certainty}`), `notes`, `observer_role` (`teacher | student_group | citizen | researcher`), `moderation_status` (`pending | approved | rejected`).

### 9.6 `tripo_jobs`

`id`, `design_id`, `kind` (`upload | text_to_image | image_to_model | text_to_model | convert | decimate`), `request` (JSONB, ohne Key), `task_id`, `status`, `progress`, `credits_consumed`, `error_code`, `raw_response` (JSONB), `created_at`, `completed_at`.

### 9.7 v2

`sensor_readings` (`instance_id`, `ts`, `temp_c`, `rh_pct`, `device_id`) für optionale ESP32-Logger hinter Kacheln.

---

## 10. ID-System, Referenzkarte, Abstammung

- **Design-ID** hängt an der Geometrie, nicht am Autor: `BT-D-` + 6 Zeichen (aus Hash der Höhenfeld-Datei + laufender Nummer).
- **Instanz-ID:** `BT-XXXXXX-NNN`.
- **Original und Remake** werden als **Abstammungskette** über `parent_design_id` modelliert, nicht als Echtheitssymbol. Das Herkunftszeichen auf der Vorderseite markiert Herkunft, nicht Echtheit. Passt zur Open-Source-Pflicht und zu CC BY-SA.
- **Referenzkarte** (PDF, A5, aus der App erzeugt): Farbfelder (Weiß, Grau 18 %, Schwarz, R, G, B, Grünreferenz), Maßstabsbalken 50 mm, **vier ArUco-Marker** an den Ecken (automatische Perspektiventzerrung und Maßstab), QR-Code mit Instanz-Link, Feld für handschriftliche Instanz-ID und Datum. Die Karte wird bei jedem Monitoringfoto ins Bild gehalten.
- Kalibrierung wird **nicht** in die Kachel gegossen (Beton hat keine Farbe; geprägte Codes sind mangels Kontrast schlecht scanbar).

---

## 11. Monitoring und Auswertung

- **Fotoprotokoll:** monatlich, feste Distanz, Referenzkarte im Bild, keine Personen, möglichst diffuses Licht. Optional Wiegen (abgenommene Kachel) für Wasserrückhalt.
- **Automatische Auswertung (OpenCV):** ArUco erkennen → Perspektive entzerren, Maßstab setzen → Weißabgleich über Graufeld → Kachel-ROI → Grünanteil über Excess-Green-Index (ExG = 2g − r − b auf normierten Chromatizitäten) mit Otsu-Schwelle → Dunkelanteil (niedriger V-Wert in HSV) als Proxy für Pilzverfärbung.
- Referenz für Plausibilisierung: Canopeo, validierte Gratis-App zur Grünbedeckung (Patrignani & Ochsner 2015).
- **Arten:** Freitext + optionale Taxon-Referenz + Gruppe + Sicherheit. Keine automatische Bestimmung bis v2.
- **Ansichten:** Zeitreihe je Kachel (Foto-Slider + Kurve), Wandvergleich (Raster mit Farbcode), globale Auswertung (Streudiagramm Metrik vs. Grünanteil nach n Wochen, Filter nach Ausrichtung, Material, Behandlung, Booster, `source_type`).
- **Erwartungsmanagement im UI:** Mit Booster erste sichtbare Besiedlung nach Monaten; ohne Booster etwa ein Jahr bis zum ersten sichtbaren Bewuchs, 2–5 Jahre bis zu dichtem Algenbewuchs (Jakubovskis 2025).

---

## 12. Oberfläche

### 12.1 Screens

1. **Gallery (Start):** Raster der Designs (Render, `source_type`-Badge, Herkunftszeichen, Anzahl Instanzen, mittlere Besiedlung), Filter, Kartenübersicht (grob) ab v1.
2. **Create Design (Wizard):**
   1. Quelle wählen: Foto / Text (v1) / Vorlage aus Bibliothek.
   2. Foto hochladen mit Fotoprotokoll-Tipps, bzw. Prompt mit Bildprüfung.
   3. Tripo-Fortschritt.
   4. **Relief-Editor:** three.js-Vorschau, Regler Makro/Meso/Mikro, Umschalter Fließrichtung, Funktionsvorlage + Parameter, Randmodus, **3 × 3-Kachelvorschau**, Auswahl Material/Prozess/Werkzeugmaterial (steuert Schwindmaß, Flankenwinkel, Mindeststärke), Prüfpanel (Entformbarkeit, Mindeststärke, Bauraum A1 mini/P1S, Periodizität).
   5. **Export:** ZIP-Download, Metadaten, Lizenzbestätigung, Veröffentlichen.
3. **Design Detail:** Renders, Metriken, Abstammungsbaum, Downloads, Instanzen, „Remix"-Button (legt Kind-Design an).
4. **Register Tile:** Design wählen, Instanz-ID erzeugen, Guss-/Materialdaten, Wand und Position, Adapter, Standort grob, **Ausrichtung mit Kompass-Hilfe** (DeviceOrientation API am Handy), Aufstellfoto, Referenzkarte drucken.
5. **Walls:** Wand anlegen, Rasterlayout, Prüfung REF-FLAT/REF-GEO, Randomisierungshelfer, Bohrschablone drucken.
6. **Add Observation (mobile-first):** Instanz per QR auf der Referenzkarte oder ID-Eingabe, Foto mit Karte, Arten, Notiz, optional Gewicht.
7. **Analysis:** Zeitreihen, Wandvergleich, globale Auswertung.
8. **Dashboard (Account):** Kontingent, Wände, fällige Beobachtungen, Moderationsliste.
9. **Method/About:** Wissenschaftliche Grundlage, Zeitskalen, Grenzen, Quellen, Sammelregeln Booster, Sicherheit (alkalische Materialien, Harz, Gips nicht außentauglich).
10. **Admin.**

### 12.2 REST-Endpunkte (Skizze)

```
POST   /api/uploads                     -> {upload_id}
POST   /api/designs                     -> Entwurf anlegen (source_type, Eingabe)
POST   /api/designs/{id}/generate       -> Tripo-Job + Pipeline starten
GET    /api/jobs/{id}                   -> Status/Fortschritt
PATCH  /api/designs/{id}/params         -> Pipeline-Parameter, Neuberechnung
GET    /api/designs/{id}/preview        -> Höhenfeld/Mesh für Vorschau
POST   /api/designs/{id}/export         -> Werkzeugpaket erzeugen
GET    /api/designs/{id}/package        -> ZIP
POST   /api/designs/{id}/publish
POST   /api/designs/{id}/remix          -> Kind-Design
GET    /api/designs?filter...
POST   /api/walls | GET /api/walls/{id}
POST   /api/instances | GET /api/instances/{id}
GET    /api/instances/{id}/reference-card.pdf
GET    /api/walls/{id}/drill-template.pdf
POST   /api/instances/{id}/observations
GET    /api/analysis/...
```

### 12.3 Datenschutz und Sicherheit

- Keine Einzelkonten für Schüler:innen, nur Schul- oder Projektkonten.
- Keine Gesichter/Personen auf Fotos (Hinweis im Upload; Freigabe durch das Schulkonto vor öffentlicher Anzeige).
- Standorte nur grob (Ort/Stadtteil), keine exakten Koordinaten.
- EU-Hosting, Datensparsamkeit, Löschkonzept.
- Tripo-Key nur serverseitig, Credit-Kontingente je Account, Rate-Limits.
- Offene Daten unter CC BY.

---

## 13. Repo, Lizenzen, Tests

### 13.1 Struktur

```
/apps/web                 React + Vite + TS
/services/api             FastAPI
/services/worker          Jobs, Pipeline-Aufrufe
/packages/biotile_geometry  Pipeline, Werkzeuggenerierung, Metriken, constants.py
/data/library             Startbibliothek (Seeds, Prompt-Vorlagen, Beispielbilder)
/docs                     dieses Dokument, Methodik, Druck- und Gussanleitungen
/tests                    Unit-, Geometrie-, API-Tests; fixtures/tripo
docker-compose.yml
.env.example              TRIPO_API_KEY=, TRIPO_MODE=mock
LICENSE / LICENSE-DESIGNS / LICENSE-DATA
README.md (EN), README.de.md
CLAUDE.md                 Kurzfassung der Prinzipien aus Abschnitt 0
```

### 13.2 Lizenzen

- Code: MIT oder AGPL-3.0, Entscheidung **vor** dem ersten öffentlichen Commit.
- Designs/STL: CC BY-SA 4.0.
- Daten: CC BY 4.0.
- **Blockierende offene Frage:** Tripo-Nutzungsbedingungen zur Weiterverbreitung generierter Meshes prüfen, bevor abgeleitete STLs unter CC BY-SA ins öffentliche Repo gehen.

### 13.3 Pflichttests Geometrie

- Periodizität: gegenüberliegende Randzeilen gleich (Toleranz).
- Wasserdichtheit aller exportierten Meshes (`trimesh.Trimesh.is_watertight`).
- Mindestmaterialstärke eingehalten.
- Maximaler Flankenwinkel eingehalten.
- Bauraum-Fit je Druckerprofil.
- Schwindmaß korrekt angewendet (Fertigmaß nach Rückrechnung = 150 mm).
- Aufhängepunkte und Kanäle schneiden sich nicht.
- Determinismus: zweimal gleiche Eingabe → identisches Höhenfeld (Hash).

---

## 14. Umfang und Phasen

### 14.1 Hackathon-MVP (Einreichung bis 05.10.2026 AoE)

Kritischer Pfad, in dieser Reihenfolge:
1. Repo-Gerüst, Docker Compose, `MockTripoClient`, `LiveTripoClient`, Lizenzentscheidung.
2. **Tripo-Test mit echten Fotos planer Oberflächen** (Risiko 7.6). Fixtures für Mock aufzeichnen.
3. Pipeline: Upload → Image-to-Model → Höhenfeld → Detrend → periodisch → Makro/Meso → Skalierung → Anisotropie → eine Funktionsvorlage (`diagonal_cascade`) → Entformbarkeit → Mindeststärke.
4. Werkzeuge: Matrize + vier Rahmenwände + eine Rückenplatte (Ton-Variante mit Schlüsselloch-Schablone) als STL, Bauraum-Check, ZIP.
5. Web: Wizard mit Foto-Upload, Fortschritt, Relief-Editor mit three.js und 3 × 3-Vorschau, Export.
6. Galerie mit veröffentlichten Designs.
7. Minimal: Instanz registrieren + Beobachtung erfassen (Formular, ohne automatische Auswertung), Referenzkarte als PDF.
8. README (EN), Methodenseite, Screencast-Rundgang, Visual-Asset-Board.
9. Wenn Zeit bleibt: eine Matrize drucken, eine Tonkachel pressen, Fotos fürs Asset-Board.

Im MVP **nicht** enthalten: Text-Modus, Mikroband aus Normal-Map, Beton-Rückenplatte, Kanäle, Wände/Randomisierung, automatische Bildauswertung, Moderation, Accounts mit Kontingenten (ein Demo-Account genügt).

### 14.2 v1 (nach dem Hackathon)

Text- und Hybridmodus, Mikroband aus Normal-Map, alle Funktionsvorlagen, Beton-Rückenplatte mit Gewindehülsen, Halbkanäle, Wände mit Referenzprüfung und Randomisierung, Bohrschablone, ArUco-Auswertung, Zeitreihen und Analyse, Schulkonten mit Kontingent, Moderation, DSGVO-Konzept, Abstammungsbaum, vollständige Metriken, monokulare Tiefenschätzung als Fallback.

### 14.3 v2

Kaskadenwand (neue Bohrschablone, Anleitung), Pfostenmanschetten (mineralisch), Stapelvarianten, Durchgangskanäle mit Rückreservoir/Docht, ESP32-Sensoren (Temperatur/Feuchte), Multiview, Photometric-Stereo-Aufnahmehelfer, Photogrammetrie, Artbestimmungs-Assistenz, World-Labs-Ansicht der Kohorte, Wang-Tiles bzw. drehbare Kacheln, Vorkonditionierung als Versuchsfaktor.

---

## 15. Wettbewerbsabgaben

- **Repo:** öffentlich, klonbar, `docker compose up` startet im Mock-Modus ohne Key; Beispiel-Designs mit Werkzeugpaketen enthalten (Lizenzfrage 13.2 beachten).
- **Screencast (Rundgang, kein Trailer):** Foto einer realen Oberfläche → Tripo-Job → Relief-Editor (Regler, Fließrichtung, Funktionsvorlage) → 3 × 3-Vorschau → Prüfpanel → Export → Galerie → Kachel registrieren → Beobachtung. Wenn vorhanden: gedruckte Matrize und gepresste Kachel.
- **Visual-Asset-Board:** Quellfoto, Höhenfeld, Bandzerlegung, Relief-Render, Werkzeugteile als Explosionsdarstellung, Schnitt durch die Kachel (Funktionsschicht, Texturschicht, Rückseite), gepresste Kachel, Wandlayout.
- **Build-Log:** öffentliche Fortschrittsposts.
- **Kernbotschaften:** Geschenk für die Lebewesen der Stadt; Kunststoff nur als Werkzeug; Tripo als Übersetzer zwischen Beobachtung und Fertigung (Makro aus Geometrie, Mikro aus Normal-Map); offenes Messnetz; ehrliche Zeitskalen.

---

## 16. Startbibliothek Oberflächen

| # | Oberfläche | Funktionale Begründung |
|---|---|---|
| 1 | Baumrinde | vertikale Risse unterschiedlicher Tiefe |
| 2 | Verwitterter Fels | Spalten, Poren, Mulden |
| 3 | Trockenrissiger Lehm | netzartig, quer zur Fließrichtung |
| 4 | Totholz | Fraßgänge, Hohlräume |
| 5 | Schiefer | schmale parallele Spalten |
| 6 | Sandstein | porös, rau |
| 7 | Lavagestein | stark porös, verschiedene Hohlraumgrößen |
| 8 | Wurzeloberfläche | längliche Rillen, geschützte Überhänge |
| 9 | Tafoni (Wabenverwitterung im Sandstein) | selbstbeschattende Hohlkehlen; entspricht der Muldenform des erfolgreichsten Paneels bei Mustafa et al.; im Stuttgarter Stubensandstein vorhanden |
| 10 | Karren (Lösungsrinnen im Kalk) | reinste Form von „along the flow"; Gegenprobe zum Trockenriss |
| 11 | Kalktuff / Travertin | extrem porös, wasserspeichernd; lokal in Bad Cannstatt |
| 12 | Platanenrinde | abblätternde Platten, Spalten, Überhänge; häufigster Straßenbaum |
| 13 | Alte Rebstockrinde | faserige Längsstruktur |
| 14 | Ausgewaschene Mörtelfuge einer Trockenmauer | die Fuge statt des Steins |
| 15 | Frostgesprengter Ziegel | scharfkantige offene Poren, Abfallmaterial |
| 16 | Muschelkalk mit Fossilanschnitt | harte/weiche Zonen, Relief vertieft sich über Jahre |
| 17 | Rissnetz in altem Asphalt | die Stadt kopiert ihren eigenen Verfall |
| 18 | REF-FLAT | Nullreferenz |
| 19 | REF-GEO | Richtliniengeometrie |

Je Eintrag in `/data/library`: Beispielbild(er) mit Lizenz, Prompt-Vorlage für den Text-Modus, empfohlene Funktionsvorlage, empfohlene Bandgewichtung.

---

## 17. Risiken und offene Fragen

| Risiko / Frage | Umgang |
|---|---|
| Tripo liefert bei planen Flächen schlechte Geometrie | sofort testen; Fallbacks 7.6 |
| Tripo-ToS zur Weiterverbreitung generierter Meshes | **blockierend** für öffentliche STLs; klären |
| Wiederverwendung bestehenden Codes erlaubt? | bei Tripo nachfragen |
| Tool-Track-Zuschnitt noch offen | Architektur nicht darauf festzurren |
| Deadline 05.10. AoE | MVP-Pfad 14.1 strikt |
| Credits | Mock-first, Kontingente, Logging |
| Geometrie wirkt im Freiland schwach | Hypothesen entsprechend; Booster als Faktor; Referenzkacheln |
| Kein Gießen in den Ferien | v1 passiv dokumentieren (`irrigated`), v2 Docht/Reservoir |
| Tonschwindung | Schwindmaß-Feld + Probestab-Anleitung |
| Genehmigungen | v1 nur Schulgelände, Zaunadapter |
| Datenschutz | 12.3 |
| Artenschutz beim Booster-Sammeln | Sammelregeln 5.8 prüfen |

---

## 18. Ideenspeicher (nicht Teil dieses Builds)

- **Sinkkasten-Einsatz:** Ausstiegshilfe in genormten Straßenabläufen, in denen jährlich viele Kleintiere verenden; in Deutschland fehlen laut einem Fachartikel einschlägige Normen, die Schweiz hat eine (VSS SN 640 699a). Konzeptuell scharf, schnell machbar, als physisches Mitbringobjekt geeignet. *Zahlen und Normangaben vor Verwendung erneut prüfen.*
- Weitere Stadtphänomene aus der Ideenphase: gegossene Steilwand für bodennistende Wildbienen, Pflasterfugen-Nistfuge, Lichtschacht-Ausstieg, Bordstein-Rampe, Totholz-Prothese, „Drei Tage Wasser"-Mulde, Leuchtenblende gegen Lichtverschmutzung, Thermogradient-Stein für Mauereidechsen.

---

## 19. Quellen

**Gesichert (Volltext oder Metadaten geprüft):**
- Mustafa, K. F., Prieto, A., & Ottele, M. (2021). The Role of Geometry on a Self-Sustaining Bio-Receptive Concrete Panel for Facade Application. *Sustainability*, 13(13), 7453. https://doi.org/10.3390/su13137453 (CC BY)
- Jakubovskis, R. (2025). Biophilic Façades: The Potentiality of Bioreceptive Concrete. *Buildings*, 15(20), 3646. https://doi.org/10.3390/buildings15203646
- Larrieu, L., Paillet, Y., Winter, S., Bütler, R., Kraus, D., Krumm, F., Lachat, T., Michel, A. K., Regnery, B., & Vandekerkhove, K. (2018). Tree related microhabitats in temperate and Mediterranean European forests: A hierarchical typology for inventory standardization. *Ecological Indicators*, 84, 194–207.
- Schell, F., Zwahr, C., & Lasagni, A. F. (2024). Surfalize: A Python Library for Surface Topography and Roughness Analysis Designed for Periodic Surface Structures. *Nanomaterials*, 14(13), 1076.
- Nečas, D., & Klapetek, P. (2012). Gwyddion: An Open-Source Software for SPM Data Analysis. *Open Physics*, 10. https://doi.org/10.2478/s11534-011-0096-2
- Tripo API v3 Dokumentation: https://developers.tripo3d.ai/en/docs/introduction (Introduction, Image to 3D Model — H Series)
- Tripo Text to model (H3), ältere API-Doku: https://docs.tripo3d.ai/model-generation/text-to-model-v3-0-v3-1.html
- Urban Reef, Projekte: https://www.urbanreef.nl/projects
- Studio Biocene, Poikilohydric Living Walls: https://www.studiobiocene.com/project/poikilohydric-living-walls
- Ecolve / Scape Agency: vom Nutzer bereitgestellte Projektbeschreibung, https://www.scape.agency

**Verifikation empfohlen:**
- Veeger, M., et al. (2021). Making bioreceptive concrete: Formulation and testing of bioreceptive concrete mixtures. *Journal of Building Engineering*. (Autorenreihenfolge, Band prüfen)
- Cruz, M., & Beckett, R. Bioreceptive design: A novel approach to biodigital materiality. *Architectural Research Quarterly*, 20, 51–64. https://doi.org/10.1017/S1359135516000130 (Jahr 2013 vs. 2016 widersprüchlich)
- Moss species for bioreceptive concrete: A survey of epilithic urban moss communities and their dynamics. *Ecological Engineering* (2024), ScienceDirect S0925857424003276. (Autoren prüfen)
- Engineering of bio-mimetic substratum topographies for enhanced early colonization of filamentous algae. *PLOS ONE* (2019). https://doi.org/10.1371/journal.pone.0219150 (Autoren prüfen)
- Refugia Preferences by the Spiders *Loxosceles reclusa* and *Loxosceles laeta*. *Journal of Medical Entomology*, 45(1), 36 ff. (Autoren, Jahr prüfen)
- Microtopographic control of vascular plant, bryophyte and lichen communities on cliff faces (ResearchGate). (Autoren, Zeitschrift prüfen)
- Moisan, L. (2011). Periodic Plus Smooth Image Decomposition. *Journal of Mathematical Imaging and Vision*, 39, 161–179.
- Patrignani, A., & Ochsner, T. E. (2015). Canopeo: A powerful new tool for measuring fractional green canopy cover. *Agronomy Journal*, 107(6).
- Marine Studie zu pflanzlichem Schalöl und Besiedlung (Zuordnung unklar).
- Bundesartenschutzverordnung: Schutzstatus *Sphagnum* spp. und *Leucobryum glaucum*.

---

## 20. Glossar

- **Matrize/Stempel:** gedrucktes Reliefteil; als Matrize (Relief oben, Material darauf) oder Stempel (Relief unten, eingedrückt).
- **Gießrahmen:** vier Wände, definieren Umriss, Dicke, Kantenprofile.
- **Rückenplatte:** definiert die Rückseite (Aufhängung, ID, Kanäle).
- **Funktionsschicht / Texturschicht:** prozedurale Wasser- und Boosterstrukturen / Natur- bzw. KI-Relief.
- **Booster:** Inokulum aus Papierpulpe und lokaler Bodenkruste.
- **Versuchswand / Kaskadenwand:** hydraulisch getrennte / gekoppelte Kachelanordnung.
- **REF-FLAT / REF-GEO:** Pflicht-Referenzkacheln.
- **Schwindmaß:** prozentuale Schrumpfung von Ton bis zum Brand.
- **along the flow:** Strukturen folgen der Fließrichtung des Wassers.
