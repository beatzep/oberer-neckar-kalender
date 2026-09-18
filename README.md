# oberer-neckar-kalender

Spielpläne der HSG Oberer Neckar (Herren, Herren II, Damen) als
abonnierbare Kalender und eine kleine Seite mit Mannschaftswahl.

Kleiner Ableger von [handball-kalender](https://github.com/beatzep/handball-kalender)
für ein zweites Team beim Doppelspielrecht - andere Quelle, deshalb eigenes
Repo statt gemeinsamer Datenpipeline.

## Die Quelle ist eine andere

Die HSG Mutterstadt/Ruchheim spielt im Bereich von handball.net, das eine
öffentliche JSON-API hat. Die HSG Oberer Neckar spielt beim
Baden-Württembergischen Handball-Verband, der noch das ältere
handball4all/nuLiga-System benutzt. Auch dort gibt es eine JSON-API, nur
nicht dokumentiert:

```
https://spo.handball4all.de/service/if_g_json.php?ca=0&cl=<liga_id>&cmd=ps&ct=<team_id>&do=<datum>&og=<verband_id>
```

Liga- und Team-IDs stehen in `teams.json`, eine Mannschaft pro Eintrag. Sie
ändern sich nicht während der Saison, aber vermutlich von Saison zu Saison -
dann auf der handball4all-Seite über "Kalender abonnieren" neu nachsehen
(Rechtsklick auf den iCal-Link, URL kopieren, `cl`/`ct`/`og` rauslesen) und
in `teams.json` eintragen.

**Falle, die schon zugeschnappt ist:** handball4all nennt jedes Team
zweimal, unterschiedlich geschrieben. In den Spielpaarungen (`gHomeTeam`/
`gGuestTeam`) steht die Abkürzung "HSG Ob. Neckar", in der Tabelle
(`tabTeamname`) der ausgeschriebene Name "HSG Oberer Neckar". `teams.json`
führt deshalb zwei Felder: `name_in_quelle` für die Spielpaarungen,
`name_tabelle` für die Tabellenzeile. Fehlt eins, wird entweder Heim/Gast
falsch erkannt oder die eigene Zeile in der Tabelle nicht gefunden.

Torverläufe oder Spielberichte liefert der Verband auf diesen Liga-Ebenen
nicht - nur Termine, Hallen und Endstände. Das steht auch so auf der Seite,
statt eine Lücke zu verstecken, die aussieht wie ein Fehler.

## Bauen

```bash
python3 hole_daten.py --teams teams.json --out daten.json
python3 baue_ics.py --daten daten.json --out-verzeichnis docs
python3 baue_seite.py --daten daten.json --out docs/index.html
```

`docs/` ist erzeugt, nicht von Hand bearbeiten - wie im MuRu-Projekt.

Ein GitHub-Actions-Workflow (`.github/workflows/aktualisieren.yml`) baut
einmal täglich neu, an Wochenenden zusätzlich stündlich von 12 bis 22 Uhr
UTC (Spieltage), und pusht die Änderungen. Übernommen aus dem MuRu-Projekt
(`handball-kalender/.github/workflows/spielplan.yml`).

## Änderungserkennung

`hole_daten.py` vergleicht bei jedem Lauf mit dem vorherigen `daten.json`
(pro Mannschaft, an der Spielnummer `gNo` festgemacht) und erkennt
Verlegungen, Hallenwechsel, neue und abgesetzte Spiele - wie im
MuRu-Projekt (`spielplan2ics.py`, `erkenne_aenderungen`). Erkannte
Änderungen erscheinen auf der Seite oben im jeweiligen Mannschafts-Reiter
und heben die `SEQUENCE` des betroffenen Kalendereintrags an, damit
abonnierte Kalender die Änderung auch wirklich übernehmen. Der Hinweis
verschwindet von selbst wieder, sobald der nächste Lauf keine neuen
Änderungen mehr findet.

## Logo

`docs/logo.png`, `apple-touch-icon.png` und `favicon-32.png` sind das echte
Vereinswappen von [hsg-oberer-neckar.de](https://www.hsg-oberer-neckar.de),
heruntergeladen und in drei Größen skaliert. Die Farben (`--marine
#0a2c73`, `--gold #ffda06` in `baue_seite.py`) sind aus dem Logo
ausgelesen, nicht frei erfunden. Diese Seite ist kein offizielles
Vereinsangebot - das steht auch im Seitenfuß.

## Prüfen

Die .ics-Dateien lassen sich mit `pruefe_streng.py` aus dem MuRu-Projekt
gegen RFC 5545 prüfen:

```bash
python3 /pfad/zu/handball-kalender/pruefe_streng.py docs/herren1.ics docs/herren2.ics docs/damen.ics
```
