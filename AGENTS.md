# Projektregeln

## Sprache und Stil

Immer Schweizer Rechtschreibung verwenden. Keine Emojis, Semikolons oder Gedankenstriche im Fliesstext verwenden. Aufzählungen sparsam einsetzen. Nüchternen technischen Textstil mit gut lesbarem Fliesstext verwenden. Wörter im Fliesstext nicht fett oder kursiv hervorheben. Kommentare im Code beschreiben hauptsächlich, weshalb etwas gemacht wird.

## Architekturentscheidungen

Vor Entwicklungsarbeiten die [ADR-Übersicht](docs/adr/index.md) und die für die Änderung relevanten ADRs lesen. Die angenommenen Entscheidungen sind verbindliche Vorgaben. Der bestehende Code ist kein Beleg dafür, dass eine abweichende Architektur erlaubt ist. Abweichungen benennen und das weitere Vorgehen vor einer Verhaltensänderung klären.

Keine Schattendatenbank des Jellyfin-Bestands und keine Synchronisation eines solchen Bestands führen. Alle für die fachliche Zuordnung und Einsortierung von Episoden oder ganzen Serien benötigten Informationen über die Jellyfin API beziehen. Gespeicherte Jellyfin-Statuswerte dürfen keine Entscheidungsgrundlage für spätere Läufe sein.

Die Jellyfin-Instanz, ihre Datenbank, Konfiguration, Metadaten und bestehenden Medien schützen. Bei fehlenden oder widersprüchlichen Informationen den betroffenen Vorgang blockieren. Keine destruktiven API-Aufrufe oder Versuche an der produktiven Instanz zur Verifikation ausführen. Für Tests simulierte API-Antworten und isolierte Testverzeichnisse verwenden.

Bei fachlichen oder technischen Zweifeln vor der betroffenen Umsetzung nachfragen. Die offene Frage, mögliche Folgen und eine Empfehlung konkret benennen. Keine stillschweigenden Annahmen über Datenquellen, Zuordnungen, Dateilöschungen oder Jellyfin-Schreibzugriffe treffen. Bereits eindeutig entschiedene Vorgaben umsetzen.

## Dokumentation und Prüfung

Das [README](README.md) enthält ausschliesslich ein Docker-Compose-Beispiel und ein .env-Beispiel. Die Beispiele entsprechen [compose.yaml](compose.yaml) und [.env.example](.env.example). Architektur, Entwicklung und API-Hinweise gehören nach docs.

Vor Änderungen am Jellyfin-Client die [API Referenz](docs/jellyfin-api.md) lesen und Endpunkte, Parameter und Antwortfelder anhand der passenden offiziellen Spezifikation prüfen. Keine Endpunkte oder deren Wirkung erraten.

Prüfungen passend zur Änderung ausführen. Bei Dokumentationsänderungen lokale Links und Konfigurationsbeispiele prüfen. Bei Änderungen an Importen oder API-Aufrufen insbesondere Fehlerfälle, mehrdeutige Zuordnungen, bestehende Ziele und den Erhalt der Quelldaten prüfen.

Bei GUI-Anpassungen die [lokale Gestaltungsvorschau](docs/ui-preview.md) starten und die betroffenen Ansichten im Browser prüfen. Dem Benutzer zum Abschluss immer den Link zur laufenden Vorschau nennen. Nach Änderungen am Python-Code die Vorschau neu starten. Beispieldaten verwenden ausschliesslich erfundene Serientitel und lokal gespeicherte, eigens generierte Poster.
