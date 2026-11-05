# Jellyfin API Referenz

## Offizielle Quellen

Die [offizielle API Dokumentation](https://api.jellyfin.org/) bietet die durchsuchbare Referenz. Die [offizielle OpenAPI Spezifikation der stabilen Version](https://api.jellyfin.org/openapi/jellyfin-openapi-stable.json) beschreibt Endpunkte, Parameter, Antwortmodelle und Authentifizierung maschinenlesbar. Der Stable-Link wird aktualisiert und ist keine dauerhaft an eine Serverversion gebundene Quelle.

Die eigene Jellyfin-Instanz stellt ihre versionsbezogene Dokumentation unter den folgenden Pfaden bereit. JELLYFIN_URL muss dabei einschliesslich eines allfälligen Basisverzeichnisses verwendet werden.

| Adresse relativ zu JELLYFIN_URL | Inhalt |
| --- | --- |
| /api-docs/swagger/index.html | Swagger UI der eigenen Instanz |
| /api-docs/openapi.json | OpenAPI Spezifikation der eigenen Instanz |

Diese Pfade sind im offiziellen [Jellyfin-Quellcode zur API Dokumentation](https://github.com/jellyfin/jellyfin/blob/master/Jellyfin.Server/Extensions/ApiApplicationBuilderExtensions.cs) definiert. Die Dokumentation zu lesen ist keine Freigabe, deren ausführbare Beispiele gegen eine produktive Instanz zu verwenden.

## Version und Vorgehen bei Änderungen

Der aktuelle [Jellyfin-Client](../src/newtvshowsng2/jellyfin.py) akzeptiert Jellyfin 12.x und prüft die Version über GET /System/Info/Public. Für eine Änderung ist zuerst die tatsächlich unterstützte Serverversion zu bestimmen. Danach werden Endpunkte, Parameter, Antwortfelder und Berechtigungen anhand der dazu passenden offiziellen Spezifikation geprüft. Eine neuere Stable-Spezifikation erweitert nicht automatisch die vom Projekt unterstützten Versionen.

Parameter und deren Schreibweise werden aus der Spezifikation übernommen. Aufzählungen sind vollständig zu paginieren. Eine fehlerhafte oder unvollständige Antwort darf nicht als leerer Medienbestand interpretiert werden. Staffelnummern, Episodennummern und Provider-IDs dürfen nicht aus unvollständigen Antworten ergänzt oder geraten werden.

## Derzeit verwendete Endpunkte

Die Tabelle beschreibt den vorhandenen Client. Sie ist keine Freigabe für zusätzliche API-Funktionen. Verbindlich bleiben [ADR 0002](adr/0002-jellyfin-api-als-datenquelle.md) und [ADR 0004](adr/0004-jellyfin-und-mediendaten-schuetzen.md). Methoden und Pfade wurden anhand der offiziellen Stable-Spezifikation geprüft.

| Methode | Pfad | Verwendung im Projekt |
| --- | --- | --- |
| GET | /System/Info/Public | Serverversion prüfen |
| GET | /Users | Konfigurierten Benutzer eindeutig auflösen |
| GET | /Items | Serien und vorhandene Episoden abfragen |
| GET | /Items/{itemId}/Images/Primary | Kleines Serienposter für Fehlend und Historie abrufen |
| GET | /Shows/{seriesId}/Episodes | Episoden und benutzerbezogenen Gesehen-Status abfragen |
| GET | /Library/VirtualFolders | Serienbibliotheken, Pfade und Bibliotheksoptionen lesen |
| POST | /Items/RemoteSearch/Series | Metadaten neuer Serien über Jellyfin suchen |
| POST | /Library/Refresh | Bibliotheksscan nach Importen anstossen |

Die Seriensuche verwendet einen POST-Request zur Suche. Sie ist vom Anwenden oder Ändern von Metadaten zu unterscheiden. Der Bibliotheksscan verändert den Verarbeitungszustand von Jellyfin. Eine erfolgreiche Antwort auf /Library/Refresh bestätigt nur den gestarteten Scan. Die OpenAPI Spezifikation weist dafür die Berechtigung RequiresElevation aus.

Der Bildabruf wurde zusätzlich anhand der OpenAPI Spezifikation einer Jellyfin-Instanz mit Version 12.4.0 geprüft. Der Endpunkt erwartet itemId als UUID und den Bildtyp Primary. Die Anwendung verwendet maxWidth=80, maxHeight=120 und format=Jpg. Die Antwort enthält die Bilddatei. Ein fehlendes Poster wird mit HTTP 404 beantwortet. Die verkleinerte API-Antwort wird in der Oberfläche mit 56 × 84 Pixeln angezeigt.

Der Browser erhält eine Adresse der Anwendung unter /series-image. Nur der Server sendet den Authorization-Header an Jellyfin. Bildadressen enthalten weder den API-Schlüssel noch eine frei wählbare Zieladresse. Der [Bildabruf und Cache](series-images.md) beschreibt Zuordnung, Begrenzungen und Fehlerverhalten.

## Authentifizierung und Datenverwendung

Die OpenAPI Spezifikation definiert den Header Authorization für die Authentifizierung. Der Client verwendet einen MediaBrowser-Header mit Clientinformationen und einem Token aus JELLYFIN_API_KEY. JELLYFIN_USERNAME wird über /Users zu einer Benutzer-ID aufgelöst. Benutzerbezogene Angaben wie UserData.Played werden für diesen Benutzer abgefragt. Ein API-Schlüssel allein legt keinen Benutzer für solche Angaben fest.

Echte Schlüssel oder vollständige Authorization-Header gehören weder in Dokumentation noch in Protokolle oder Testdaten. Die benötigten Rechte werden pro Endpunkt geprüft. Die Verwendung eines Benutzernamens bedeutet keine Einschränkung der Berechtigungen des API-Schlüssels.

API-Antworten dienen gemäss [ADR 0001](adr/0001-keine-jellyfin-schattendatenbank.md) ausschliesslich als aktuelle fachliche Datenquelle. Fehler, fehlende Angaben und Mehrdeutigkeiten blockieren die betroffene Einsortierung. Tests für den Client liegen in [tests/test_jellyfin.py](../tests/test_jellyfin.py) und verwenden simulierte Antworten.
