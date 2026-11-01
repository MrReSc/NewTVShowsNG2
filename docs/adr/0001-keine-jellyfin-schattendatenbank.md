# ADR 0001: Keine Schattendatenbank des Jellyfin-Bestands

Datum: 2026-11-01

Status: Angenommen

## Kontext

Eine lokale Kopie des Jellyfin-Bestands kann von der tatsächlichen Bibliothek abweichen. Eigene Abgleichsregeln für Serien, Episoden, fehlende Medien oder den Gesehen-Status würden eine zweite fachliche Datenhaltung schaffen.

## Entscheidung

Die Anwendung führt keine persistente Schattendatenbank des Jellyfin-Bestands. Sie synchronisiert oder rekonstruiert keinen eigenen Serien-, Episoden- oder Gesehen-Bestand. Dies gilt unabhängig davon, ob die Daten in SQLite, Dateien, einem Cache oder einer anderen Ablage liegen.

Für einen Verarbeitungslauf dürfen aktuelle API-Antworten im Arbeitsspeicher verarbeitet werden. Ein späterer Lauf bezieht die benötigten Informationen erneut von Jellyfin. Ein persistenter Bestand mit regelmässigen Abgleichen oder ein Rückgriff auf gespeicherte Jellyfin-Werte bei API-Ausfällen ist unzulässig.

Eigene Betriebsdaten wie Feed-Eingänge, Laufzeiten, Fehlermeldungen und technische Importzustände dürfen gespeichert werden. Sie dürfen keinen Jellyfin-Bestand spiegeln oder als Ersatz für aktuelle API-Daten zur Einsortierung dienen. Ein Importprotokoll belegt insbesondere nicht, dass Jellyfin eine Episode bereits kennt oder weiterhin besitzt.

## Konsequenzen

Die Verarbeitung ist von aktuellen, vollständigen API-Antworten abhängig. Fehlende Informationen werden gemäss [ADR 0002](0002-jellyfin-api-als-datenquelle.md) behandelt. Eine technische Wiederaufnahme nach einem Abbruch darf keine eigene Bestandsverwaltung voraussetzen.

## Bestehende Abweichung

[storage.py](../../src/newtvshowsng2/storage.py) speichert derzeit unter anderem Jellyfin-Episodenzahlen, erwartete Episodenzahlen und Gesehen-Zahlen in announcements. [scanner.py](../../src/newtvshowsng2/scanner.py) aktualisiert diese gespeicherten Werte über refresh_library_state. Diese persistierten Bestandswerte und ihre Abgleichslogik entsprechen nicht dieser Entscheidung. Ihre Bereinigung und eine allfällige Datenmigration sind gesondert zu klären. Die übrigen lokalen Betriebsdaten sind nach ihrer tatsächlichen Verwendung zu beurteilen.
