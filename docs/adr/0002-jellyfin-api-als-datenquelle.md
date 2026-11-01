# ADR 0002: Jellyfin API als Quelle für die Einsortierung

Datum: 2026-11-01

Status: Angenommen

## Kontext

Die Einsortierung von Episoden und ganzen Serien benötigt verlässliche Informationen über Serienidentität, Staffeln, Episoden, Provider-IDs und Bibliothekspfade. Abweichende lokale Annahmen können zu falschen Zielordnern oder doppelten Importen führen.

## Entscheidung

Alle fachlichen Informationen, die für die Zuordnung und Einsortierung benötigt werden, müssen über die Jellyfin API abgefragt werden. Dazu gehören insbesondere Serienidentität, Titel, Erscheinungsjahr, Provider-IDs, bestehende Serienpfade, vorhandene Episoden sowie benötigte Informationen zu fehlenden oder gesehenen Episoden.

Auch die Metadatensuche für neue Serien erfolgt über Jellyfin. Direkte Abfragen externer Metadatenanbieter, Zugriffe auf die Jellyfin-Datenbank, eingelesene NFO-Dateien oder ein lokaler Bibliotheksindex ersetzen die API nicht. Namen aus RSS-Einträgen und Eingangsdateien dienen als Suchkriterien. Sie bestätigen keine Zuordnung zur Bibliothek.

Bestehende Zielpfade werden aus den API-Daten und der konfigurierten Pfadzuordnung abgeleitet. Neue Ordnernamen werden anhand der von Jellyfin gelieferten Serieninformationen gebildet. Prüfungen im Dateisystem dienen dem Schutz vor Kollisionen, Pfadausbrüchen und Datenverlust. Sie begründen keine fachliche Serienzuordnung und keinen eigenen Medienbestand.

## Konsequenzen

Bei nicht erreichbarer API, unvollständigen Antworten, widersprüchlichen Angaben oder mehreren möglichen Zuordnungen wird die betroffene Einsortierung blockiert. Es gibt keinen Rückgriff auf einen lokalen Ersatzbestand. Eine manuelle Auswahl muss anhand aktueller Jellyfin-Daten erneut geprüft werden.

Ein angestossener Bibliotheksscan bestätigt noch nicht, dass ein neuer Import über die API sichtbar ist. Bis zur erforderlichen Bestätigung bleibt dieser Zustand offen. Die [API Referenz](../jellyfin-api.md) beschreibt die offiziellen Quellen und die derzeit verwendeten Endpunkte.

## Prüfung der bestehenden Umsetzung

[media_importer.py](../../src/newtvshowsng2/media_importer.py) enthält neben API-Abfragen lokale Suchen nach Serienordnern und Episodendateien. Bei einer Anpassung ist zu prüfen, dass diese ausschliesslich Sicherheitsprüfungen bleiben und keine fachliche Zuordnung oder Ersatzbestandsführung übernehmen.
