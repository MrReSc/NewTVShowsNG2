# ADR 0010: Erledigte Feed-Einträge wieder öffnen

Datum: 2026-11-05

Status: Angenommen

## Kontext

Der Auftraggeber möchte eine versehentlich erledigte Meldung wieder öffnen können. Die Aktion ergänzt die Erledigung aus [ADR 0008](0008-feed-eintraege-manuell-erledigen.md) und berücksichtigt die eigenständigen Veröffentlichungen aus [ADR 0009](0009-feed-veroeffentlichungen-unterscheiden.md).

## Entscheidung

Jede erledigte Feed-Zeile der Historie erhält den Button «Wieder öffnen». Er hebt die Erledigung genau dieser Veröffentlichung, Staffel, Episode und Qualitätsvariante auf. Andere Meldungen und spätere Veröffentlichungen bleiben unverändert. Der HTTP-Endpunkt akzeptiert ausschliesslich Formulare desselben Ursprungs und leitet nach erfolgreicher Verarbeitung zur Historie zurück. Mehrere ausdrücklich übermittelte Kennungen werden gemeinsam verarbeitet.

Vor der Änderung liest die Anwendung aktuelle Jellyfin-Daten. Der ursprüngliche Feed-Titel und die aus dem Feed gelesene IMDb-ID dienen als Suchkriterien. Eine gespeicherte Jellyfin-Zuordnung oder ein gespeicherter Bestandswert begründet keine Entscheidung. Die Serie muss anhand der aktuellen API eindeutig zugeordnet werden. Fehlende Serien, mehrdeutige Zuordnungen, API-Fehler, unvollständige Gesehen-Angaben oder widersprüchliche Episodenangaben blockieren die gesamte Aktion. Die bisherigen Erledigungen bleiben dann erhalten.

Nach erfolgreicher Prüfung erscheint die Meldung unter «Aktuell fehlend», wenn die aktuelle Jellyfin-Antwort weiterhin fehlende Inhalte ergibt. Vorhandene oder durch Gesehen-Markierungen abgedeckte Inhalte bleiben ausgeblendet. Eine nicht bekannte Sollzahl wird wie beim regulären Feed-Abgleich als unbekannt angezeigt. Das manuelle Wiederöffnen erzeugt keine neue Feed-Veröffentlichung und keine «Neu»-Markierung.

Die Aktion verwendet die interne Prozesssperre gemäss [ADR 0007](0007-eine-anwendungsinstanz-ohne-dateisperre.md). Abgleich und Wiederöffnen erfolgen serialisiert mit anderen Läufen. Bei fehlenden Kennungen wird die ganze Aktion abgelehnt. Ein bereits wieder geöffneter, noch gespeicherter Eintrag kann erneut übermittelt werden. Der Zeitpunkt des ersten Wiederöffnens bleibt dabei erhalten. Eine vor einem späteren Feed-Eingang geöffnete Historie wirkt ausschliesslich auf die übermittelten Kennungen.

## Speicherung und Wiederholung

`announcement_completions` erhält das nullable Feld `reopened_at` mit dem Zeitpunkt des Wiederöffnens in UTC. Ein Datensatz mit gesetztem `reopened_at` gilt als nicht mehr erledigt. Der ursprüngliche Erledigungszeitpunkt bleibt als Betriebsinformation erhalten. Die Migration ergänzt das Feld ohne Änderung bestehender Erledigungen und ist wiederholbar.

Der Datensatz bleibt auch bei der Historienbereinigung erhalten. Dadurch können ältere Erledigt-Markierungen ohne Veröffentlichungszeitpunkt eine ausdrückliche Aufhebung nicht rückgängig machen. Die Migration älterer Feed-Kennungen übernimmt den Wiederöffnungszeitpunkt. Eine erneute ausdrückliche Erledigung setzt einen neuen Erledigungszeitpunkt und hebt den Wiederöffnungsstatus auf. Wiederholte Erledigungen bereits erledigter Einträge bleiben unverändert.

Die zusätzliche Kennung für Einträge ohne Datum übernimmt ebenfalls die ausdrückliche Aufhebung. Dadurch bleibt das Wiederöffnen wirksam, wenn derselbe Feed-Eintrag nach der Historienbereinigung ohne Veröffentlichungsdatum zurückkehrt. Bereits erledigte Veröffentlichungen mit bekanntem Datum bleiben dabei erledigt.

Die neue Prüfung und die Aufhebung werden für alle betroffenen Meldungen gemeinsam übernommen. Ein anschliessender Fehler bei der HTML-Ausgabe nimmt die bereits gespeicherte Aufhebung nicht zurück. Die Anfrage kann wiederholt werden, um die Ausgabe zu erneuern.

## Konsequenzen

Die Aktion liest Jellyfin, ruft aber keine RSS-Feeds ab und verändert keine Mediendateien. Sie führt weder einen Medienimport noch schreibende Jellyfin-Aufrufe aus. Ein bereits aus der Historie entfernter Eintrag kann mangels Feed-Angaben nicht über ein altes Formular wieder geöffnet werden.

Die gespeicherten Zeitpunkte beschreiben ausschliesslich den Bearbeitungsstatus einer Feed-Veröffentlichung. Es entsteht kein Jellyfin-Ersatzbestand. Die Schutzvorgaben aus [ADR 0001](0001-keine-jellyfin-schattendatenbank.md), [ADR 0002](0002-jellyfin-api-als-datenquelle.md) und [ADR 0004](0004-jellyfin-und-mediendaten-schuetzen.md) bleiben verbindlich.
