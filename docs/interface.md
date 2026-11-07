# Bedienung und Rückmeldungen

Die Oberfläche unterstützt die private Einzelnutzung am Desktop. Der bestätigte Nutzungskontext steht in [PRODUCT.md](../PRODUCT.md). Die [Architekturentscheidungen](adr/index.md) bleiben verbindlich.

## Gestaltung

Die vier HTML-Ansichten verwenden gemeinsame Farben, Schriftrollen, Navigation und Bedienelemente aus [_theme.html](../src/newtvshowsng2/templates/_theme.html). Flächen, Navigation, Links, Schaltflächen und Fokusmarkierungen verwenden Schwarz und neutrale Grautöne. Helligkeit und Konturen unterscheiden aktive Elemente. Blau kennzeichnet den Badge «Neu». Gelb, Rot und Grün bleiben den jeweiligen Warnungen, Fehlern und weiteren fachlichen Statuswerten vorbehalten.

Alle anklickbaren Bedienelemente beziehen ihre Zustandsfarben aus derselben Graustufenpalette. Die gemeinsamen Regeln stehen in `_theme.html`. Die einzelnen Ansichten legen Grösse und Anordnung fest. Interne Aktionslinks wie «Serie zuordnen», «Raw-Log öffnen», Seitenwechsel im Log und der Rückweg aus der Serienauswahl erscheinen als Schaltflächen mit diesen gemeinsamen Farben.

| Zustand | Fläche | Kontur | Schrift |
| --- | --- | --- | --- |
| Normal | `#262626` | `#6b6b6b` | `#d0d0d0` |
| Hover | `#333333` | `#909090` | `#f0f0f0` |
| Gedrückt | `#1f1f1f` | `#a5a5a5` | `#f0f0f0` |
| Ausgewählt oder aufgeklappt | `#3b3b3b` | `#858585` | `#f0f0f0` |
| Ausgewählt mit Hover | `#484848` | `#909090` | `#f0f0f0` |
| Deaktiviert | `#1d1d1d` | `#3b3b3b` | `#808080` |

Buttons, Eingabefelder, Auswahllisten und Qualitätslinks verwenden die normale Fläche und Kontur. Für Navigation, aufklappbare Beschriftungen und Historienfilter ist der nicht ausgewählte Grundzustand transparent. Hover, Druck und Auswahl verwenden dieselben Zustandsfarben wie die übrigen Bedienelemente. Reine Textlinks behalten ihre Unterstreichung und erhalten dieselben Hover- und Druckfarben.

Tastaturfokus erhält durchgängig eine 2 Pixel starke Markierung in `#c5c5c5` mit 3 Pixeln Abstand. Bei umrandeten Elementen erhält auch die Kontur diese Farbe. Deaktivierte Elemente verwenden eigene Farben und reagieren optisch nicht auf Hover oder Druck. Die Historienfilter behalten native Checkboxen als Bedienelemente. Ihre sichtbare Fläche und ihr Häkchen verwenden die gemeinsame Palette. Im erzwungenen Kontrastmodus übernimmt der Browser ihre Darstellung.

Die Eckenradien folgen vier zentralen Rollen aus [_theme.html](../src/newtvshowsng2/templates/_theme.html). Komponenten verwenden diese Variablen statt eigener Zahlenwerte.

| Rolle | Variable | Wert | Verwendung |
| --- | --- | --- | --- |
| Detail | `--radius-detail` | 3 Pixel | Status-Badges, Logstufen, Qualitätslinks und Serienposter |
| Bedienelement | `--radius-control` | 6 Pixel | Schaltflächen, Eingabefelder und Auswahllisten |
| Fläche | `--radius-surface` | 10 Pixel | Panels, mobile Eintragskarten, Meldungen, Filter, Serienauswahl und Navigationsleiste |
| Kapsel | `--radius-pill` | 999 Pixel | Navigationseinträge |

Die Stufen unterscheiden kleine Details, bedienbare Elemente und übergeordnete Flächen. Der Kapselradius kennzeichnet die Navigation als zusammengehörige Auswahl.

Eine Systemschrift trägt Überschriften, Beschriftungen und Inhalte. Technische Kennungen und Tracebacks verwenden eine Schrift mit fester Zeichenbreite. Zahlen in Bestands- und Datumsfeldern nutzen gleich breite Ziffern. Überschriften und grössere Gruppen erhalten mehr Abstand, während zusammengehörige Informationen dicht beieinander bleiben.

Die Hauptnavigation steht in einer kompakten, dunkelgrauen Leiste mit feiner Kontur. Die aktive Ansicht erhält eine etwas hellere, abgerundete Kapsel. Produktname und Monogramm entfallen in der Kopfzeile. In schmalen Fenstern bleiben alle vier Ansichten mit kleineren Abständen in einer Zeile erreichbar. Die gemeinsame Kopfzeile bleibt beim Scrollen erreichbar. Feed, Medienimport, Historie und Log zeigen keine zusätzliche sichtbare Seitenüberschrift. Ihre Überschriften bleiben für assistive Technik verfügbar. Serienauswahl und Fehlerseiten verwenden weiterhin sichtbare Überschriften mit einer Schriftgrösse von 1,25 rem.

In der Feedansicht sind Bestand und die Anzahl bekannter fehlender Folgen direkt sichtbar. Die zusätzliche Gesehen-Zahl entfällt in Feed und Historie. Qualitätsvarianten stehen als direkte Links unter dem Serientitel. Der vollständige Veröffentlichungstitel steht am jeweiligen Link als Titelhinweis bereit. Auf Wunsch des Auftraggebers entfällt der zusätzliche aufklappbare Variantenbereich. Die festgelegten gleichen Zeilenhöhen und der Zugang zu langen Inhalten bleiben erhalten.

Besuchte Variantenlinks erhalten eine hellgraue Füllung mit dunkler Schrift aus `--control-visited` und `--control-on-visited`. Beim Überfahren wird die Fläche mit `--control-visited-hover` etwas heller. Noch nicht besuchte Varianten verwenden die normalen Bedienelementfarben. Die Kennzeichnung verwendet den Browserverlauf und bleibt auch beim Überfahren und Drücken des Links erkennbar. Sie beschreibt ausschliesslich den Linkbesuch.

## Serienauswahl und Importumfang

Jeder Treffer der Serienauswahl zeigt die Anzahl der zugehörigen Quellen sowie deren Staffel, Episode und relativen Quellpfad. Die Liste wird beim Öffnen anhand der aktuell vorhandenen Eingangsdateien und der aktuellen Jellyfin-Treffer ermittelt. Die Zugehörigkeit folgt denselben Prüfungen wie die manuelle Übernahme. Die Quellen sind einzelne Videodateien oder die bereits unterstützten Verzeichnisse mit jeweils einer Episode.

Wenn alle Treffer dieselben Quellen betreffen, erscheint die vollständige Liste einmal gemeinsam vor den Auswahlmöglichkeiten. Bei unterschiedlichen Quellen bleibt jede Liste beim jeweiligen Treffer. Die Bestätigung nennt weiterhin die Anzahl der Quellen und die gewählte Serie.

Die Auswahlkennung bindet den Jellyfin-Treffer und die Metadatensignaturen aller angezeigten Quellen. Die Bestätigung prüft den Umfang erneut. Eine hinzugekommene, entfernte oder veränderte zugehörige Quelle blockiert die veraltete Auswahl. Der Nutzer öffnet die Zuordnung danach erneut. Vor Beginn der Übernahme wird der bestätigte Umfang nochmals geprüft. Während des Laufs werden ausschliesslich bestätigte Quellen berücksichtigt. Die bestehende Prüfung vor der atomaren Verschiebung bleibt erhalten.

Diese Vorschau ist flüchtig. Sie erzeugt keine zusätzliche persistente Datenhaltung, keine Inhaltsprüfsummen und keinen Ersatzbestand von Jellyfin. Bestehende Ziele und nicht betroffene Quellen bleiben durch die bisherigen Importprüfungen geschützt.

## Laufende Vorgänge

Die Kopfbereiche von Feed, Medienimport und Historie zeigen keine Eintragszahlen, Statuspunkte oder Angaben zum nächsten Lauf. Hinweise zu laufenden Vorgängen sowie Fehler- und Warnmeldungen stehen im jeweiligen Inhaltsbereich.

Ein manueller Feed-Abgleich oder Medienimport lädt das Dokument nicht automatisch neu. Das von derselben Anwendung gelieferte [Skript](../src/newtvshowsng2/static/ui.js) liest während eines laufenden Vorgangs die bereits erzeugte Hauptseite in Abständen von drei Sekunden. Es aktualisiert ausschliesslich die Laufhinweise und die Verfügbarkeit der Startaktionen. Tabellen, Historienfilter, Scrollposition und Tastaturfokus bleiben bestehen.

Das Diagnoselog zeigt keine zusätzliche Sortierzeile, keinen Stand und keine Angabe zum ältesten gespeicherten Eintrag im Seitenkopf. Zeitangaben der einzelnen Meldungen, Filter und die ausdrückliche Aktualisierung bleiben verfügbar.

Die strukturierte Logansicht zeigt Zeitstempel, Logstufe, Meldung und Quelle jeweils einmal. Sie berücksichtigt die aktuelle Datei und vorhandene rotierte Dateien. Die vollständige aktuelle Logdatei ist über die Schaltfläche «Raw-Log öffnen» verfügbar.

«Raw-Log öffnen» öffnet ausschliesslich die aktuelle Logdatei unter /log/raw als reine Textdatei in einem neuen Tab. Die Antwort enthält die unveränderten Dateibytes ohne Filter, Umsortierung oder rotierte Dateien. Eine leere Datei ergibt eine leere Antwort. Bei einer fehlenden oder nicht lesbaren Datei erscheint eine Fehlerseite mit Rückweg zum Log. Beide Ansichten lesen nur die konfigurierte Logdatei beziehungsweise die bekannten Rotationen und verändern keine Dateien.

Nach dem Lauf weist die Oberfläche auf neue Ergebnisse hin. «Ansicht aktualisieren» lädt diese ausdrücklich. Ohne JavaScript sowie bei einem fehlgeschlagenen Statusabruf steht dieselbe manuelle Aktualisierung bereit. Die Hauptseite erlaubt für das Skript und dessen Abrufe ausschliesslich denselben Ursprung. Die übrigen HTML-Seiten benötigen keine Skriptfreigabe.

Der Statusabruf startet keine Verarbeitung und fragt Jellyfin nicht nach fachlichen Bestandsinformationen ab. Er liest lediglich die bereits erzeugte HTML-Ausgabe. Die serverseitige Serialisierung bleibt massgebend, auch wenn eine ältere Browseransicht noch eine Startaktion anbietet.

## Fehler und erneute Prüfung

Erwartbare Fehler bei Feedaktionen, Importen und Serienauswahlen behalten ihre HTTP-Statuscodes. Die Fehlerseite zeigt die Ursache, die Hauptnavigation und einen Rückweg zur betroffenen Ansicht. Sie führt keine automatische Wiederholung aus. Fehlermeldungen werden als Text ausgegeben und gegen HTML-Einschleusung geschützt.

Eine Fehlermeldung behauptet weder eine abgeschlossene Dateiübernahme noch eine vollständige Rücknahme. Vor einer Wiederholung prüft der Nutzer den aktuellen Stand. Dies berücksichtigt auch Fehler bei der Ausgabe nach einer bereits gespeicherten Aktion.

Die Prüfungen für geänderte Quellen, aktuelle Zuordnungen und bestehende Ziele liegen in [test_series_selection.py](../tests/test_series_selection.py). [test_logging_and_server.py](../tests/test_logging_and_server.py) prüft die Rückmeldungen, HTTP-Antworten, Sicherheitsheader und Rückwege mit isolierten Daten.
