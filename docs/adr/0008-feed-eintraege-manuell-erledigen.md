# ADR 0008: Feed-Einträge manuell erledigen

Datum: 2026-11-01

Status: Angenommen

Präzisierung vom 5. November 2026: [ADR 0009](0009-feed-veroeffentlichungen-unterscheiden.md) ersetzt die nachfolgende Regel zur Kennung einer Meldung. Eine neue Veröffentlichung kann auch bei gleicher GUID und gleichem Link wieder erscheinen. Titel- oder Beschreibungsänderungen allein heben eine Erledigung weiterhin nicht auf.

## Kontext

Eine Feed-Meldung kann bereits bearbeitet sein, obwohl Jellyfin die angekündigten Medien noch nicht kennt. Der Auftraggeber möchte einzelne Zeilen unter «Aktuell fehlend» mit einem Klick erledigen. Neue RSS-Einträge sollen unabhängig davon weiterhin angezeigt werden.

## Entscheidung

Der Button «Erledigt» markiert ausschliesslich die Feed-Einträge, die in der angezeigten Zeile enthalten sind. Zusammengefasste Qualitätsvarianten werden gemeinsam erledigt. Die Meldungen verschwinden aus «Aktuell fehlend» und bleiben mit dem Status «Erledigt» in der bestehenden Historie. Eine zusätzliche Verwaltung oder Sperre für Serien, Staffeln oder Episoden entsteht nicht.

Die Tabelle announcement_completions speichert nur den bestehenden source_key und den Erledigungszeitpunkt in UTC. Die Kennung berücksichtigt Feed, GUID beziehungsweise ersatzweise Link sowie Staffel und Episode. Die Markierungen bleiben bei Neustarts und bei der Historienbereinigung erhalten. Ein erneut gelesener Eintrag bleibt dadurch erledigt. Änderungen an Titel oder Beschreibung bei gleicher Kennung heben die Markierung nicht auf. Ein neuer Eintrag mit eigener Kennung wird unabhängig geprüft.

Die Markierung beschreibt ausschliesslich den Bearbeitungsstatus einer Feed-Meldung gemäss [ADR 0001](0001-keine-jellyfin-schattendatenbank.md). Sie bestätigt weder vorhandene noch gesehene Medien und dient nicht als Grundlage für Zuordnungen oder Importentscheidungen. Dafür bleibt gemäss [ADR 0002](0002-jellyfin-api-als-datenquelle.md) die aktuelle Jellyfin API massgebend. Die gesondert zu klärende Migration bestehender Jellyfin-Bestandsdaten ist nicht Bestandteil dieser Änderung.

## Konsequenzen

Die Erledigung verwendet die interne Prozesssperre gemäss [ADR 0007](0007-eine-anwendungsinstanz-ohne-dateisperre.md). Nur die übermittelten Kennungen werden gemeinsam markiert. Wiederholte Klicks sind erfolgreich, ohne den ursprünglichen Zeitpunkt zu verändern. Nicht mehr verfügbare Kennungen blockieren die gesamte Aktion. Der HTTP-Endpunkt akzeptiert nur Formulare desselben Ursprungs und leitet nach erfolgreicher Erledigung zur Übersicht zurück.

MAX_HISTORY begrenzt weiterhin die gespeicherten Feed-Meldungen. Erledigte Meldungen werden dabei wie abgeschlossene Einträge behandelt. Ihre Erledigt-Markierungen werden unabhängig davon dauerhaft aufbewahrt und wachsen mit der Anzahl erledigter Feed-Einträge.

Die Aktion führt keine Jellyfin-Abfragen oder Schreibzugriffe aus und verändert keine Mediendateien. Die Schutzvorgaben aus [ADR 0004](0004-jellyfin-und-mediendaten-schuetzen.md) bleiben verbindlich.
