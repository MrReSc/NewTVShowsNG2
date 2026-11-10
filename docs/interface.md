# Bedienung und Rückmeldungen

Die Oberfläche unterstützt die private Einzelnutzung am Desktop. Der bestätigte Nutzungskontext steht in [PRODUCT.md](../PRODUCT.md). Die [Architekturentscheidungen](adr/index.md) bleiben verbindlich.

## Gestaltung

Tabellenbuttons, Qualitätslinks, Status-Badges und Logstufen verwenden eine gemeinsame kompakte Geometrie aus dem Theme. Die Mindesthöhe beträgt 1,625 rem beziehungsweise 26 Pixel bei normaler Browserbasis. Schriftgrösse, Gewicht und Innenabstände sind mit 13 Pixeln, Gewicht 500 und 2 × 8 Pixeln einheitlich. Die Breite folgt der Beschriftung. Die feste Statusspalte von 16 rem hält die vorhandenen Beschriftungen am Desktop einzeilig. In mobilen Karten bleiben mehrere Statuswerte und eine anschliessende Aktion auf derselben horizontal scrollbar erreichbaren Zeile.

Die vier HTML-Ansichten verwenden gemeinsame Farben, Schriftrollen, Navigation und Bedienelemente aus [_theme.html](../src/newtvshowsng2/templates/_theme.html). Flächen, Navigation, Links, Schaltflächen und Fokusmarkierungen verwenden Schwarz und neutrale Grautöne. Helligkeit und Konturen unterscheiden aktive Elemente. Blau kennzeichnet den Badge «Neu». Gelb, Rot und Grün bleiben den jeweiligen Warnungen, Fehlern und weiteren fachlichen Statuswerten vorbehalten.

Alle anklickbaren Bedienelemente beziehen ihre Zustandsfarben aus derselben Graustufenpalette. Die gemeinsamen Regeln stehen in `_theme.html`. Die einzelnen Ansichten legen Grösse und Anordnung fest. Interne Aktionslinks wie «Serie zuordnen», «Raw-Log öffnen», Seitenwechsel im Log und der Rückweg aus der Serienauswahl erscheinen als Schaltflächen mit diesen gemeinsamen Farben.

| Zustand | Fläche | Kontur | Schrift |
| --- | --- | --- | --- |
| Normal | `#262626` | `#6b6b6b` | `#c5c5c5` |
| Hover | `#333333` | `#909090` | `#f0f0f0` |
| Gedrückt | `#1f1f1f` | `#a5a5a5` | `#f0f0f0` |
| Ausgewählt oder aufgeklappt | `#3b3b3b` | `#858585` | `#f0f0f0` |
| Ausgewählt mit Hover | `#484848` | `#909090` | `#f0f0f0` |
| Deaktiviert | `#1d1d1d` | `#3b3b3b` | `#808080` |

Buttons, Eingabefelder, Auswahllisten, Qualitätslinks und Historienfilter verwenden die normale Fläche und Kontur. Für aufklappbare Beschriftungen ist der nicht ausgewählte Grundzustand transparent. Hover, Druck und Auswahl verwenden dieselben Zustandsfarben wie die übrigen Bedienelemente. Die Navigation unterscheidet ihre Auswahl und Hover-Fläche wie unten beschrieben. Reine Textlinks behalten ihre Unterstreichung und erhalten dieselben Hover- und Druckfarben.

Tastaturfokus erhält durchgängig eine 2 Pixel starke Markierung in `#c5c5c5` mit 3 Pixeln Abstand. Bei umrandeten Elementen erhält auch die Kontur diese Farbe. Deaktivierte Elemente verwenden eigene Farben und reagieren optisch nicht auf Hover oder Druck. Die Historienfilter behalten native Checkboxen als Bedienelemente. Ihre sichtbare Fläche und ihr Häkchen verwenden die gemeinsame Palette. Im erzwungenen Kontrastmodus übernimmt der Browser ihre Darstellung.

Die Eckenradien folgen drei zentralen Rollen aus [_theme.html](../src/newtvshowsng2/templates/_theme.html). Komponenten verwenden diese Variablen statt eigener Zahlenwerte.

| Rolle | Variable | Wert | Verwendung |
| --- | --- | --- | --- |
| Detail | `--radius-detail` | 3 Pixel | Checkboxen |
| Bedienelement | `--radius-control` | 6 Pixel | Schaltflächen, Eingabefelder, Auswahllisten, Status-Badges, Logstufen, Qualitätslinks, Serienposter sowie Auswahl und Hover-Fläche der Navigation |
| Fläche | `--radius-surface` | 10 Pixel | Panels, mobile Eintragskarten, Meldungen, Filter, Serienauswahl und Navigationsleiste |

Buttons, Badges, Qualitätslinks und Bilder verwenden denselben Eckenradius. Die weiteren Stufen unterscheiden Checkboxen und übergeordnete Flächen. Die Navigationsleiste verwendet den Flächenradius von 10 Pixeln. Ihre Auswahl und Hover-Fläche verwenden wie die übrigen Bedienelemente 6 Pixel Radius.

Inter trägt Überschriften, Beschriftungen und Inhalte. Die unveränderte variable WOFF2-Datei stammt direkt aus dem offiziellen Repository [rsms/inter, Version 4.1](https://github.com/rsms/inter/tree/v4.1). [Fontdatei](../src/newtvshowsng2/static/fonts/inter-4.1.woff2) und [SIL Open Font License 1.1](../src/newtvshowsng2/static/fonts/LICENSE.txt) sind im Anwendungspaket enthalten und werden auch im Docker-Image mitgeliefert. Der Browser lädt die Schrift unter `/fonts/inter-4.1.woff2` vom eigenen Anwendungsserver. Externe Font-Dienste werden nicht benötigt. Die versionierte URL erlaubt eine langfristige Zwischenspeicherung. Das gemeinsame Theme lädt die Schrift vorab, und `font-display: swap` hält Texte während des Ladens mit der Systemschrift lesbar. Die Sicherheitsrichtlinien aller HTML-Ansichten erlauben Schriften ausschliesslich vom eigenen Ursprung.

Die variable Schrift deckt die Schriftgewichte 100 bis 900 ab. Die Oberfläche verwendet daraus die Gewichte 400, 500 und 600. Das [Designsystem](../DESIGN.md) beschreibt die wiederverwendbaren Farben, Abstände, Radien, Komponenten und Schriftrollen. Es definiert vier Schriftgrössen mit 13, 14, 16 und 20 Pixeln bei normaler Browserbasis. Alle Ansichten beziehen diese Werte aus den gemeinsamen CSS-Variablen. Schrift wird in schmalen Fenstern nicht verkleinert. Kleine Grossbuchstabenlabels entfallen. Inter nutzt die automatische optische Grössenanpassung und den Zeichensatz `ss04` für besser unterscheidbare Buchstaben. Zahlen in Bestands- und Datumsfeldern nutzen gleich breite Ziffern. Technische Providerkennungen verwenden weiterhin eine Schrift mit fester Zeichenbreite.

Serienname, Episodencode und Qualitätslinks bilden drei getrennte Zeilen. Der Titel beginnt an der oberen Bildkante, die Release-Links enden an der unteren Bildkante. In der Historie steht die Eintragsart in der dritten Zeile. Bild und Textbereich verwenden dieselbe Höhe von 5,25 rem. Lange Serientitel bleiben einzeilig mit Auslassungszeichen. Vollständige Titel sind über Tooltip und horizontalen Bildlauf bei Tastaturfokus zugänglich. Episodencodes verwenden ebenfalls Inter mit normalen Nullen. Die Datums- und Zeitspalten in Tabellen und Diagnoselog verwenden wie die Bestandszeile 16 Pixel, Gewicht 400 und die primäre Textfarbe. Die gestalteten Beschriftungen enthalten keine Mittelpunkte als Trennzeichen. Bei mehreren Varianten derselben Qualität folgt die Release-Gruppe mit einem Leerzeichen. Unter Importzielen stehen Episodencode und ergänzender Titel in einer gemeinsamen Metadatenzeile mit Abstand. Die drei neutralen Textrollen verwenden `--text`, `--text-secondary` und `--muted`. Status-Badges und Logstufen nutzen einheitlich 13 Pixel und Gewicht 500 mit den jeweiligen fachlichen Farben. Überschriften und grössere Gruppen erhalten mehr Abstand, während zusammengehörige Informationen dicht beieinander bleiben.

Die Hauptnavigation steht in einer kompakten, dunkelgrauen Leiste mit feiner Kontur. Die aktive Ansicht erhält eine gefüllte hellgraue Fläche. Produktname und Monogramm entfallen in der Kopfzeile. In schmalen Fenstern bleiben alle vier Ansichten mit kleineren Abständen in einer Zeile erreichbar. Die gemeinsame Kopfzeile behält beim Scrollen ihre Position mit 24 Pixeln Abstand zum oberen Fensterrand, in schmalen Fenstern mit 16 Pixeln. Eine deckende Fläche hält den oberen Abstand frei von durchlaufenden Inhalten. Feed, Medienimport, Historie und Log zeigen keine zusätzliche sichtbare Seitenüberschrift. Ihre Überschriften bleiben für assistive Technik verfügbar. Serienauswahl und Fehlerseiten verwenden weiterhin sichtbare Überschriften mit einer Schriftgrösse von 1,25 rem.

In der Feedansicht sind Bestand und die Anzahl bekannter fehlender Folgen direkt sichtbar. Die zusätzliche Gesehen-Zahl entfällt in Feed und Historie. Qualitätsvarianten stehen als direkte Links unter dem Serientitel. Der vollständige Veröffentlichungstitel steht am jeweiligen Link als Titelhinweis bereit. Auf Wunsch des Auftraggebers entfällt der zusätzliche aufklappbare Variantenbereich. Die festgelegten gleichen Zeilenhöhen und der Zugang zu langen Inhalten bleiben erhalten.

In der Historie erhält «Bestand / Ziel» am Desktop 24 Prozent und die Datumsspalte 16 Prozent der Tabellenbreite. Importziele zeigen den letzten Ordner und den Dateinamen mit höchstens zwei Zeilen. Ein vorangestelltes Auslassungszeichen kennzeichnet ausgelassene Ordner. Der vollständige Zielpfad steht beim Überfahren als Tooltip bereit. Kurze Pfade bleiben vollständig sichtbar. Die gleiche Kürzung gilt in den mobilen Karten.

Die Historienfilter «Feed» und «Import» verwenden dieselbe Höhe, Schrift und Innenabstände wie die übrigen Buttons. Die zusätzliche Gruppenbeschriftung ist nur für assistive Technik verfügbar. «Import Ordner scannen» prüft das Eingangsverzeichnis. Auf der Logseite stehen «Raw-Log öffnen» und «Aktualisieren» linksbündig wie die Aktionen der übrigen Ansichten. Der Abstand zwischen den Aktionen und dem folgenden Inhaltsbereich beträgt durchgängig 24 Pixel, auch vor den Logeinstellungen.

Besuchte Variantenlinks erhalten eine hellgraue Füllung mit dunkler Schrift aus `--control-visited` und `--control-on-visited`. Beim Überfahren wird die Fläche mit `--control-visited-hover` etwas heller. Noch nicht besuchte Varianten verwenden die normalen Bedienelementfarben. Die Kennzeichnung verwendet den Browserverlauf und bleibt auch beim Überfahren und Drücken des Links erkennbar. Sie beschreibt ausschliesslich den Linkbesuch.

Die sichtbare Schrift des Serientitels wird über Versalhöhe und Zeilenhöhe an der oberen Posterkante ausgerichtet. In mobilen Feed- und Historienkarten verwenden die Felder für Bestand, Status und Datum dieselbe Bildbreite von 3,5 rem und denselben Abstand von 14 Pixeln wie der Titelbereich. Ihre Werte beginnen dadurch an einer gemeinsamen linken Kante mit Titel, Episodencode und Qualitätslinks.

Die Navigation verwendet dieselben Eckenradien wie die übrigen Flächen und Bedienelemente. Die aktive Seite erhält eine hellgraue Auswahlfläche aus `--accent` mit dunkler Schrift aus `--background`. Eine separate dunkle Fläche gleitet beim Überfahren zwischen den nicht aktiven Einträgen und passt ihre Breite an. Die aktive Auswahl bleibt dabei sichtbar. Auf der aktiven Seite und ausserhalb der Navigation verschwindet die Hover-Fläche. Bei reduzierter Bewegung erfolgen die Wechsel ohne Animation. Ohne JavaScript bleiben die Farben und die Navigation erhalten.

## Serienauswahl und Importumfang

Jeder Treffer der Serienauswahl zeigt die Anzahl der zugehörigen Quellen sowie deren Staffel, Episode und relativen Quellpfad. Die Liste wird beim Öffnen anhand der aktuell vorhandenen Eingangsdateien und der aktuellen Jellyfin-Treffer ermittelt. Die Zugehörigkeit folgt denselben Prüfungen wie die manuelle Übernahme. Die Quellen sind einzelne Videodateien oder die bereits unterstützten Verzeichnisse mit jeweils einer Episode.

Wenn alle Treffer dieselben Quellen betreffen, erscheint die vollständige Liste einmal gemeinsam vor den Auswahlmöglichkeiten. Bei unterschiedlichen Quellen bleibt jede Liste beim jeweiligen Treffer. Die Bestätigung nennt weiterhin die Anzahl der Quellen und die gewählte Serie.

Die Auswahlkennung bindet den Jellyfin-Treffer und die Metadatensignaturen aller angezeigten Quellen. Die Bestätigung prüft den Umfang erneut. Eine hinzugekommene, entfernte oder veränderte zugehörige Quelle blockiert die veraltete Auswahl. Der Nutzer öffnet die Zuordnung danach erneut. Vor Beginn der Übernahme wird der bestätigte Umfang nochmals geprüft. Während des Laufs werden ausschliesslich bestätigte Quellen berücksichtigt. Die bestehende Prüfung vor der atomaren Verschiebung bleibt erhalten.

Diese Vorschau ist flüchtig. Sie erzeugt keine zusätzliche persistente Datenhaltung, keine Inhaltsprüfsummen und keinen Ersatzbestand von Jellyfin. Bestehende Ziele und nicht betroffene Quellen bleiben durch die bisherigen Importprüfungen geschützt.

## Laufende Vorgänge

Die Kopfbereiche von Feed, Medienimport und Historie zeigen keine Eintragszahlen, Statuspunkte oder Angaben zum nächsten Lauf. Hinweise zu laufenden Vorgängen sowie Fehler- und Warnmeldungen stehen im jeweiligen Inhaltsbereich.

Ein manueller Feed-Abgleich oder Medienimport lädt das Dokument nicht automatisch neu. Das von derselben Anwendung gelieferte [Skript](../src/newtvshowsng2/static/ui.js) liest während eines laufenden Vorgangs die bereits erzeugte Hauptseite in Abständen von drei Sekunden. Es aktualisiert ausschliesslich die Laufhinweise und die Verfügbarkeit der Startaktionen. Tabellen, Historienfilter, Scrollposition und Tastaturfokus bleiben bestehen.

Beim Zurückkehren zu einem Tab oder Browserfenster aktualisiert das Skript die Ergebnisse, wenn die letzte vollständig geladene Ansicht mindestens eine Minute zurückliegt. Dasselbe gilt beim Wiederherstellen einer Seite aus dem Navigationscache. Feed, Medienimport und Historie übernehmen Tabellen, Meldungen und Erzeugungszeitpunkt aus der bereits erzeugten Hauptseite. Die Logansicht übernimmt die Ergebnisse für ihre aktuelle URL einschliesslich Filter und Ergebnisseite. Der Abruf startet keine Verarbeitung.

Navigation, Historienfilter und Logeingaben bleiben erhalten. Die Hauptseite hält die Scrollposition möglichst am bisher sichtbaren Eintrag fest. Falls dieser entfällt, verwendet sie einen nachfolgenden Eintrag oder die bisherige Scrollposition. Ein fokussiertes Bedienelement oder markierter Text im betroffenen Ergebnisbereich verschiebt die Aktualisierung bis nach dem Verlassen beziehungsweise Aufheben der Auswahl. Während eines laufenden Logfilters hat dessen Abruf Vorrang.

Gleichzeitige Rückkehrereignisse erzeugen nur einen Abruf. Hauptseite und Laufstatus teilen laufende Anfragen. Statusabfragen pausieren in unsichtbaren Tabs und werden beim Zurückkehren fortgesetzt. Die Rückkehrfunktion selbst erzeugt keine periodischen Abrufe. Bei einem Fehler bleiben die bisherigen Inhalte sichtbar. Ein Hinweis mit «Erneut versuchen» erlaubt einen neuen Abruf ohne vollständiges Neuladen.

Das Diagnoselog zeigt keine zusätzliche Sortierzeile, keinen Stand und keine Angabe zum ältesten gespeicherten Eintrag im Seitenkopf. Zeitangaben der einzelnen Meldungen, Filter und die ausdrückliche Aktualisierung bleiben verfügbar.

Die strukturierte Logansicht zeigt Zeitstempel, Logstufe, Meldung und Quelle jeweils einmal. Sie berücksichtigt die aktuelle Datei und vorhandene rotierte Dateien. Die vollständige aktuelle Logdatei ist über die Schaltfläche «Raw-Log öffnen» verfügbar.

Zeitraum und Mindeststufe filtern das Log unmittelbar nach der Auswahl. Die Textsuche aktualisiert die Ergebnisse nach 350 Millisekunden Eingabepause. Das Leeren des Suchfelds und die Eingabetaste wirken sofort. Der Abruf ersetzt ausschliesslich die Ergebnisse und erhält Fokus sowie Textauswahl im Suchfeld. Filteränderungen beginnen auf der ersten Ergebnisseite. URL und Aktualisierungslink entsprechen den angewendeten Filtern. Neuere Eingaben verwerfen noch laufende Abrufe. Ohne JavaScript bleibt «Anzeigen» als Formularaktion verfügbar.

«Raw-Log öffnen» öffnet ausschliesslich die aktuelle Logdatei unter /log/raw als reine Textdatei in einem neuen Tab. Die Antwort enthält die unveränderten Dateibytes ohne Filter, Umsortierung oder rotierte Dateien. Eine leere Datei ergibt eine leere Antwort. Bei einer fehlenden oder nicht lesbaren Datei erscheint eine Fehlerseite mit Rückweg zum Log. Beide Ansichten lesen nur die konfigurierte Logdatei beziehungsweise die bekannten Rotationen und verändern keine Dateien.

Nach dem Lauf weist die Oberfläche auf neue Ergebnisse hin. «Ansicht aktualisieren» lädt diese ausdrücklich. Ohne JavaScript sowie bei einem fehlgeschlagenen Statusabruf steht dieselbe manuelle Aktualisierung bereit. Die Hauptseite erlaubt für das Skript und dessen Abrufe ausschliesslich denselben Ursprung.

Alle HTML-Ansichten laden das gemeinsame UI-Skript für die Hover-Fläche und den aktuellen Navigationseintrag. Die Freigabe bleibt auf Skripte desselben Ursprungs beschränkt. Hauptseite und Log erlauben zusätzlich Abrufe vom selben Ursprung für den Laufstatus beziehungsweise die Filterergebnisse.

Der Statusabruf startet keine Verarbeitung und fragt Jellyfin nicht nach fachlichen Bestandsinformationen ab. Er liest lediglich die bereits erzeugte HTML-Ausgabe. Die serverseitige Serialisierung bleibt massgebend, auch wenn eine ältere Browseransicht noch eine Startaktion anbietet.

## Fehler und erneute Prüfung

Erwartbare Fehler bei Feedaktionen, Importen und Serienauswahlen behalten ihre HTTP-Statuscodes. Die Fehlerseite zeigt die Ursache, die Hauptnavigation und einen Rückweg zur betroffenen Ansicht. Sie führt keine automatische Wiederholung aus. Fehlermeldungen werden als Text ausgegeben und gegen HTML-Einschleusung geschützt.

Eine Fehlermeldung behauptet weder eine abgeschlossene Dateiübernahme noch eine vollständige Rücknahme. Vor einer Wiederholung prüft der Nutzer den aktuellen Stand. Dies berücksichtigt auch Fehler bei der Ausgabe nach einer bereits gespeicherten Aktion.

Die Prüfungen für geänderte Quellen, aktuelle Zuordnungen und bestehende Ziele liegen in [test_series_selection.py](../tests/test_series_selection.py). [test_logging_and_server.py](../tests/test_logging_and_server.py) prüft die Rückmeldungen, HTTP-Antworten, Sicherheitsheader und Rückwege mit isolierten Daten.

## Lokale Gestaltungsvorschau

Die [Vorschau](../scripts/preview_ui.py) verwendet erfundene Serien und lokal gespeicherte, generierte Poster mit den aktuellen Templates. Sie lässt sich aus dem Projektverzeichnis starten:

```sh
.venv/bin/python scripts/preview_ui.py
```

Unter `http://127.0.0.1:28733/preview` stehen alle Beispielansichten bereit. Feed, Import und Historie zeigen die vorhandenen Badge- und Tabellenaktionsvarianten. Das Log enthält alle fünf Logstufen und Seitenwechsel. Die Serienzuordnung zeigt mehrere Treffer, Providerangaben und Bestätigungsbuttons. Ergänzende Ansichten zeigen laufende Vorgänge, deaktivierte Aktionen, Fehlermeldungen und leere Ergebnisse. Formularaktionen öffnen eine Musterrückmeldung. Die Beispieldaten und Rückmeldungen bleiben von den betrieblichen Abläufen getrennt.

Die [Anleitung zur Gestaltungsvorschau](ui-preview.md) beschreibt Einrichtung, Aktualisierung und Erweiterung der Beispieldaten. Bei GUI-Anpassungen wird die Vorschau gestartet und der Link dem Benutzer genannt.
