# Lokale Gestaltungsvorschau

Die Vorschau dient zur gemeinsamen Beurteilung von GUI-Anpassungen. Sie rendert die aktuellen Templates aus dem Checkout mit synthetischen Daten. Theme, Navigation, Schrift und JavaScript entsprechen der Anwendung. Alle Serientitel, Dateipfade, Providerkennungen und Bestandsangaben sind erfunden. Drei eigens generierte Poster liegen als lokale Dateien im Projekt.

## Starten

Die Vorschau benötigt Python ab Version 3.11 und die Projektabhängigkeiten aus [pyproject.toml](../pyproject.toml). Für die erste Einrichtung im Projektverzeichnis:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Danach genügt für jeden Start:

```sh
.venv/bin/python scripts/preview_ui.py
```

Mit aktivierter virtueller Umgebung lautet derselbe Befehl `python scripts/preview_ui.py`. Die Ausgabe nennt den Link zur Vorschau: [http://127.0.0.1:28733/preview](http://127.0.0.1:28733/preview). Der Server bleibt bis zum Beenden mit `Ctrl+C` im Terminal aktiv. Ein anderer lokaler Port lässt sich mit `--port 28734` wählen.

Bei GUI-Anpassungen wird die Vorschau gestartet, im Browser geprüft und dem Benutzer der Link zur laufenden Vorschau genannt. Diese Vorgabe steht auch in [AGENTS.md](../AGENTS.md).

## Änderungen beurteilen

Die Übersicht unter `/preview` verlinkt Feed, Medienimport, Historie, Log, Serienzuordnung und Fehlerseite. Zusätzliche Beispiele zeigen leere Ansichten, laufende Vorgänge, deaktivierte Aktionen und Fehlermeldungen. Die Tabellen enthalten die jeweiligen Status-Badges, Qualitätslinks und Aktionsbuttons. Beispiele mit langen Titeln, Dateipfaden und fehlenden Bildern bleiben enthalten.

Änderungen an HTML, CSS im gemeinsamen Theme, JavaScript und Bildern erscheinen nach dem Neuladen der Seite. Der Server liest diese Dateien bei Anfragen erneut. Nach Änderungen am Python-Code oder an den Beispieldaten wird der Server mit `Ctrl+C` beendet und mit demselben Befehl neu gestartet. Ein zusätzlicher Frontend-Build ist nicht erforderlich.

Für die Diskussion kann der direkte Link zur betroffenen Ansicht verwendet werden, beispielsweise `http://127.0.0.1:28733/#history`. Fensterbreite und Browserzoom lassen sich wie in der Anwendung verändern.

## Beispieldaten und Bilder erweitern

Die Daten entstehen beim Start in `PreviewData` in [scripts/preview_ui.py](../scripts/preview_ui.py). `current`, `history` und `imports` bestimmen die Tabellenzeilen. `selection`, `log` und die Szenarien in `index` ergänzen die übrigen Ansichten. Neue Beispiele werden dort eingetragen und nach einem Neustart sichtbar.

Die drei erfundenen Serien mit Postern heissen «Falkenquai 17», «Die Staubgrenze» und «Archiv der stillen Uhren». Die Bilder wurden für diese Vorschau mit einem Bildgenerator als neue Motive erstellt. Sie zeigen erfundene Schauplätze ohne Darsteller, Figuren oder Logos bestehender Serien. Die PNG-Dateien liegen unter [scripts/preview_assets](../scripts/preview_assets). Die Zuordnung von Titel zu Datei steht in `SERIES_POSTERS`. Für weitere Bilder wird eine lokale Datei ergänzt und dort eingetragen. Der Server benötigt zur Laufzeit weder einen Bildgenerator noch einen externen Bilddienst.

Die Vorschau verwendet denselben Bild-URL-Filter wie die Anwendung. Synthetische Serienkennungen und Importtitel werden ausschliesslich auf die hinterlegten lokalen Dateien abgebildet. Unbekannte Titel und die absichtlich mehrdeutige Serienzuordnung zeigen den normalen Platzhalter.

## Ausführung

Der Python-Server bindet ausschliesslich an `127.0.0.1`. Er lädt keine `.env`, öffnet keine Datenbank und erzeugt keine Medienverarbeitung. Jellyfin, Feeds und Medienverzeichnisse werden nicht angesprochen. Formularaktionen liefern eine Musterrückmeldung, Release-Links führen zu einer lokalen Beispielseite. So bleibt die optische Prüfung mit denselben Daten wiederholbar.

Die Vorschau ergänzt die fachlichen Tests. Sie führt keine echten Feed-Abgleiche, Imports, Zuordnungen oder Änderungen an Einträgen aus.

## Rückkehr zum Tab prüfen

Die wiederholbare [Browserprüfung](../tests/browser/return_refresh.mjs) benötigt Node.js ab Version 22, Firefox und die laufende lokale Vorschau. In einem zweiten Terminal wird ein isoliertes Browserprofil gestartet:

```sh
mkdir -p out/ui-return-check/firefox
firefox --headless --no-remote --profile "$PWD/out/ui-return-check/firefox" --remote-debugging-port 9334
```

In einem dritten Terminal startet die Prüfung:

```sh
node tests/browser/return_refresh.mjs
```

Die Prüfung wechselt echte Browsertabs und simuliert den Zeitablauf sowie erfolgreiche, fehlgeschlagene, unvollständige und verzögerte Seitenantworten. Sie prüft die Aktualisierung von Feed, Medienimport, Historie und Log sowie den Erhalt von Filtern, Fokus, Textauswahl und Scrollposition. Weitere Fälle decken gleichzeitige Laufstatusabfragen, leere Ergebnisse, Wiederholungen und die mobile Darstellung ab. Bildschirmaufnahmen liegen anschliessend unter `out/ui-return-check`.

Vorschauadresse, WebDriver-BiDi-Adresse und Ausgabeverzeichnis können in dieser Reihenfolge als Argumente übergeben werden. Die Standardadressen sind `http://127.0.0.1:28733` und `ws://127.0.0.1:9334/session`. Die Prüfung verwendet ausschliesslich die synthetischen Vorschaudaten. Nach der Prüfung kann der separate Firefox-Prozess mit `Ctrl+C` beendet werden.
