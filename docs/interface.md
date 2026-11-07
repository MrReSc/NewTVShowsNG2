# Bedienung und Rückmeldungen

Die Oberfläche unterstützt die private Einzelnutzung am Desktop. Der bestätigte Nutzungskontext steht in [PRODUCT.md](../PRODUCT.md). Die [Architekturentscheidungen](adr/index.md) bleiben verbindlich.

## Gestaltung

Die vier HTML-Ansichten verwenden gemeinsame Farben, Schriftrollen, Navigation und Bedienelemente aus [_theme.html](../src/newtvshowsng2/templates/_theme.html). Flächen, Navigation, Links, Schaltflächen und Fokusmarkierungen verwenden Schwarz und neutrale Grautöne. Helligkeit und Konturen unterscheiden aktive Elemente. Gelb, Rot und Grün bleiben den jeweiligen Warnungen, Fehlern und fachlichen Statuswerten vorbehalten.

Status-Badges und Logstufen erscheinen als flache Rechtecke mit einem gemeinsamen Eckenradius von 3 Pixeln.

Eine Systemschrift trägt Überschriften, Beschriftungen und Inhalte. Technische Kennungen und Tracebacks verwenden eine Schrift mit fester Zeichenbreite. Zahlen in Bestands- und Datumsfeldern nutzen gleich breite Ziffern. Überschriften und grössere Gruppen erhalten mehr Abstand, während zusammengehörige Informationen dicht beieinander bleiben.

Produktname und Hauptnavigation teilen sich am Desktop eine kompakte Kopfzeile. Das Monogramm bleibt zurückhaltend. Seitenüberschriften verwenden eine Schriftgrösse von 1,25 rem. In schmalen Fenstern rückt die Navigation unter den Produktnamen. Die gemeinsame Kopfzeile bleibt beim Scrollen erreichbar.

In der Feedansicht sind Bestand und die Anzahl bekannter fehlender Folgen direkt sichtbar. Die zusätzliche Gesehen-Zahl entfällt in Feed und Historie. Qualitätsvarianten stehen als direkte Links unter dem Serientitel. Der vollständige Veröffentlichungstitel steht am jeweiligen Link als Titelhinweis bereit. Auf Wunsch des Auftraggebers entfällt der zusätzliche aufklappbare Variantenbereich. Die festgelegten gleichen Zeilenhöhen und der Zugang zu langen Inhalten bleiben erhalten.

Besuchte Variantenlinks erhalten eine hellgraue Füllung mit dunkler Schrift. Noch nicht besuchte Varianten bleiben dunkel und umrandet. Die Kennzeichnung verwendet den Browserverlauf und bleibt auch beim Überfahren des Links erkennbar. Sie beschreibt ausschliesslich den Linkbesuch.

## Serienauswahl und Importumfang

Jeder Treffer der Serienauswahl zeigt die Anzahl der zugehörigen Quellen sowie deren Staffel, Episode und relativen Quellpfad. Die Liste wird beim Öffnen anhand der aktuell vorhandenen Eingangsdateien und der aktuellen Jellyfin-Treffer ermittelt. Die Zugehörigkeit folgt denselben Prüfungen wie die manuelle Übernahme. Die Quellen sind einzelne Videodateien oder die bereits unterstützten Verzeichnisse mit jeweils einer Episode.

Wenn alle Treffer dieselben Quellen betreffen, erscheint die vollständige Liste einmal gemeinsam vor den Auswahlmöglichkeiten. Bei unterschiedlichen Quellen bleibt jede Liste beim jeweiligen Treffer. Die Bestätigung nennt weiterhin die Anzahl der Quellen und die gewählte Serie.

Die Auswahlkennung bindet den Jellyfin-Treffer und die Metadatensignaturen aller angezeigten Quellen. Die Bestätigung prüft den Umfang erneut. Eine hinzugekommene, entfernte oder veränderte zugehörige Quelle blockiert die veraltete Auswahl. Der Nutzer öffnet die Zuordnung danach erneut. Vor Beginn der Übernahme wird der bestätigte Umfang nochmals geprüft. Während des Laufs werden ausschliesslich bestätigte Quellen berücksichtigt. Die bestehende Prüfung vor der atomaren Verschiebung bleibt erhalten.

Diese Vorschau ist flüchtig. Sie erzeugt keine zusätzliche persistente Datenhaltung, keine Inhaltsprüfsummen und keinen Ersatzbestand von Jellyfin. Bestehende Ziele und nicht betroffene Quellen bleiben durch die bisherigen Importprüfungen geschützt.

## Laufende Vorgänge

Ein manueller Feed-Abgleich oder Medienimport lädt das Dokument nicht automatisch neu. Das von derselben Anwendung gelieferte [Skript](../src/newtvshowsng2/static/ui.js) liest während eines laufenden Vorgangs die bereits erzeugte Hauptseite in Abständen von drei Sekunden. Es aktualisiert ausschliesslich die Statusfelder und die Verfügbarkeit der Startaktionen. Tabellen, Historienfilter, Scrollposition und Tastaturfokus bleiben bestehen.

Das Diagnoselog zeigt keinen zusätzlichen Stand oder Aktualisierungshinweis im Seitenkopf. Zeitangaben der einzelnen Meldungen, Filter und die ausdrückliche Aktualisierung bleiben verfügbar.

Jeder aus einer Logdatei gelesene Eintrag bietet «Original anzeigen». Der aufklappbare Bereich enthält den vollständigen Text mit ursprünglichem Zeitstempel, Logstufe, Quelle und allen Folgezeilen. Einrückungen und Zeilenenden bleiben beim Einlesen erhalten. Der Text wird für HTML maskiert und innerhalb des Bereichs gescrollt. Die strukturierte Ansicht berücksichtigt weiterhin die aktuelle Datei und vorhandene rotierte Dateien.

«Raw-Log öffnen» öffnet ausschliesslich die aktuelle Logdatei unter /log/raw als reine Textdatei in einem neuen Tab. Die Antwort enthält die unveränderten Dateibytes ohne Filter, Umsortierung oder rotierte Dateien. Eine leere Datei ergibt eine leere Antwort. Bei einer fehlenden oder nicht lesbaren Datei erscheint eine Fehlerseite mit Rückweg zum Log. Beide Ansichten lesen nur die konfigurierte Logdatei beziehungsweise die bekannten Rotationen und verändern keine Dateien.

Nach dem Lauf weist die Oberfläche auf neue Ergebnisse hin. «Ansicht aktualisieren» lädt diese ausdrücklich. Ohne JavaScript sowie bei einem fehlgeschlagenen Statusabruf steht dieselbe manuelle Aktualisierung bereit. Die Hauptseite erlaubt für das Skript und dessen Abrufe ausschliesslich denselben Ursprung. Die übrigen HTML-Seiten benötigen keine Skriptfreigabe.

Der Statusabruf startet keine Verarbeitung und fragt Jellyfin nicht nach fachlichen Bestandsinformationen ab. Er liest lediglich die bereits erzeugte HTML-Ausgabe. Die serverseitige Serialisierung bleibt massgebend, auch wenn eine ältere Browseransicht noch eine Startaktion anbietet.

## Fehler und erneute Prüfung

Erwartbare Fehler bei Feedaktionen, Importen und Serienauswahlen behalten ihre HTTP-Statuscodes. Die Fehlerseite zeigt die Ursache, die Hauptnavigation und einen Rückweg zur betroffenen Ansicht. Sie führt keine automatische Wiederholung aus. Fehlermeldungen werden als Text ausgegeben und gegen HTML-Einschleusung geschützt.

Eine Fehlermeldung behauptet weder eine abgeschlossene Dateiübernahme noch eine vollständige Rücknahme. Vor einer Wiederholung prüft der Nutzer den aktuellen Stand. Dies berücksichtigt auch Fehler bei der Ausgabe nach einer bereits gespeicherten Aktion.

Die Prüfungen für geänderte Quellen, aktuelle Zuordnungen und bestehende Ziele liegen in [test_series_selection.py](../tests/test_series_selection.py). [test_logging_and_server.py](../tests/test_logging_and_server.py) prüft die Rückmeldungen, HTTP-Antworten, Sicherheitsheader und Rückwege mit isolierten Daten.
