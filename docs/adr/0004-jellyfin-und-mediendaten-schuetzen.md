# ADR 0004: Jellyfin und bestehende Mediendaten schützen

Datum: 2026-11-01

Status: Angenommen

Präzisierung: [ADR 0006](0006-atomare-medienverschiebung.md) beschreibt die beauftragte atomare Verschiebung, den Erhalt derselben Inodes und das Verhalten nach Unterbrechungen.

## Kontext

Die Anwendung greift auf Jellyfin und auf Medienverzeichnisse zu. Fehlerhafte API-Aufrufe, unsichere Pfade oder unvollständige Dateiübertragungen dürfen die bestehende Instanz und ihre Medien nicht beschädigen.

## Entscheidung

Die Anwendung schützt die Jellyfin-Instanz, ihre Datenbank, Konfiguration, Metadaten, Benutzerinformationen und bestehenden Medien. Direkte Schreibzugriffe auf Jellyfin-Datenbanken oder Konfigurationsdateien sowie automatische Reparaturen oder Löschungen des Jellyfin-Bestands sind unzulässig.

API-Zugriffe dienen grundsätzlich der Informationsabfrage. Die bereits vorgesehenen Aufrufe für die Seriensuche über /Items/RemoteSearch/Series und den Bibliotheksscan über /Library/Refresh bleiben eng begrenzte Funktionen. Die HTTP-Methode allein beschreibt deren Wirkung nicht. Weitere schreibende Funktionen werden vor ihrer Umsetzung ausdrücklich geklärt. Die Anwendung verändert insbesondere keine Gesehen-Markierungen, Bibliothekskonfigurationen oder bestehenden Metadaten als Nebenwirkung einer Einsortierung.

Importe dürfen bestehende Ziele weder überschreiben noch bestehende Bibliotheksmedien löschen. Quell- und Zielpfade müssen innerhalb der vorgesehenen Verzeichnisse liegen. Pfadbestandteile aus Dateinamen oder API-Antworten werden als nicht vertrauenswürdig behandelt. Bei einem verschiebenden Import darf die Quelle erst nach vollständig geprüfter und dauerhaft gespeicherter Übernahme entfernt werden. Bei Unsicherheit bleiben die Quelldaten erhalten.

Bei API-Fehlern, widersprüchlichen Daten, gleichzeitigen Änderungen oder Zielkonflikten wird der betroffene Vorgang sicher blockiert. Die Anwendung versucht keine eigenständige Bestandskorrektur. Zugangsdaten werden weder im Repository noch in Ausgaben offengelegt. Zugriffsrechte werden auf das für die vorgesehenen Funktionen Erforderliche begrenzt.

## Konsequenzen

Änderungen an API-Aufrufen und Dateiübertragungen benötigen passende Prüfungen für Fehlerfälle, Mehrdeutigkeiten, Zielkonflikte und Abbrüche. Entwicklungstests verwenden simulierte API-Antworten und isolierte Testverzeichnisse. Versuche mit möglichen Schreibwirkungen an einer produktiven Instanz erfordern einen gesonderten Auftrag. Ein erfolgreich gestarteter Bibliotheksscan gilt nicht als abgeschlossene Verarbeitung durch Jellyfin.
