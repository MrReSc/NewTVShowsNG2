# ADR 0009: Erneute Feed-Veröffentlichungen bei gleicher GUID unterscheiden

Datum: 2026-11-05

Status: Angenommen

Ergänzung vom 5. November 2026: [ADR 0010](0010-erledigte-feed-eintraege-wieder-oeffnen.md) ergänzt die Erledigt-Markierungen um den Zeitpunkt eines manuellen Wiederöffnens. Eine aufgehobene Erledigung wird beim erneuten Einlesen derselben Veröffentlichung nicht wieder wirksam.

## Kontext

Bei einer weiteren Episode kann der Anbieter denselben Serienlink erneut im Feed veröffentlichen. Der Auftraggeber hat festgelegt, dass eine neue GUID oder ein neuer Veröffentlichungszeitpunkt als neue Meldung zählt. Ein unveränderter Link darf dies nicht verhindern. Ein GUID-Wechsel bei jeder weiteren Episode ist nicht nachgewiesen.

Die bisherige Kennung aus [ADR 0008](0008-feed-eintraege-manuell-erledigen.md) berücksichtigt den Zeitpunkt nicht. Eine erledigte Meldung würde daher auch eine erneute Veröffentlichung mit gleicher GUID verdecken.

## Entscheidung

Eine Meldung wird durch Feed, GUID beziehungsweise ersatzweise Link, Veröffentlichungszeitpunkt, Staffel und Episode identifiziert. Gleiche Zeitpunkte werden unabhängig von ihrer Zeitzonendarstellung auf UTC normalisiert. Eine neue GUID oder ein anderer gemeldeter Veröffentlichungszeitpunkt bildet eine eigenständige Meldung. Bereits bekannte Veröffentlichungen behalten ihre Erledigt-Markierung. Titel und Beschreibung allein begründen weiterhin keine neue Meldung.

Für RSS gilt der Veröffentlichungszeitpunkt des Eintrags aus `pubDate`. Die RSS-Bibliothek stellt ihn als `published` beziehungsweise `published_parsed` bereit. Wenn ausschliesslich ein Aktualisierungszeitpunkt verfügbar ist, verwendet die Anwendung `updated` beziehungsweise `updated_parsed`. Ein vorhandener gültiger Veröffentlichungszeitpunkt hat Vorrang vor einer späteren Inhaltsaktualisierung.

Ein fehlender oder ungültiger Feed-Zeitpunkt wird nicht durch die aktuelle Abrufzeit als neue Veröffentlichung gewertet. Wenn die Meldung noch gespeichert ist, bleibt ihr bisheriger Zeitpunkt erhalten. Ohne bisherigen Eintrag gilt die Kennung ohne Veröffentlichungszeitpunkt. Für erledigte Meldungen wird zusätzlich eine Kennung ohne Datum gespeichert, die ausschliesslich beim Fehlen eines bekannten Veröffentlichungszeitpunkts gilt. Sie verhindert ein erneutes Auftauchen nach der Historienbereinigung, wenn derselbe Feed-Eintrag später kein Datum mehr liefert. Eine neue GUID oder eine datierte Veröffentlichung bleibt davon unabhängig.

Ein neuer Eintrag wird gemäss [ADR 0001](0001-keine-jellyfin-schattendatenbank.md) und [ADR 0002](0002-jellyfin-api-als-datenquelle.md) anhand der aktuellen Jellyfin API geprüft. Nur weiterhin fehlende Inhalte erscheinen unter «Aktuell fehlend». Vorhandene oder durch Gesehen-Markierungen abgedeckte Inhalte bleiben ausgeblendet. Eine Erledigung gilt ausschliesslich für die im Formular enthaltenen Meldungen. Ein altes Formular erledigt keine neuere Veröffentlichung.

## Übernahme bestehender Meldungen

Beim erneuten Einlesen eines datierten Feed-Eintrags erhalten bestehende Meldungen derselben Feed-Kennung ihre neue Kennung anhand ihres jeweils gespeicherten Veröffentlichungszeitpunkts. Vorhandene Erledigt-Markierungen werden samt ursprünglichem Erledigungszeitpunkt übernommen. Frühere Veröffentlichungen bleiben bis zur regulären Historienbereinigung erhalten. Die Umstellung erfolgt innerhalb derselben Datenbanktransaktion wie die Aufnahme des Eintrags.

Wurde eine alte Meldung bereits aus der Historie entfernt, fehlt ihrer bisherigen Erledigt-Markierung der Veröffentlichungszeitpunkt. Für diese Altmarkierungen gilt der Erledigungszeitpunkt als Übergangsgrenze. Veröffentlichungen bis zu dieser Grenze bleiben erledigt. Spätere Veröffentlichungen werden unabhängig geprüft. Neu erzeugte Markierungen enthalten den Veröffentlichungszeitpunkt in ihrer Kennung und benötigen diese Übergangsregel nicht.

## Konsequenzen

`announcement_completions` behält die Felder `source_key` und `completed_at`. Der Veröffentlichungszeitpunkt ist Bestandteil der gehashten Kennung. Die Markierungen überleben weiterhin Neustarts und die Historienbereinigung. Es entstehen ausschliesslich zusätzliche Betriebsdaten zu Feed-Veröffentlichungen, kein Jellyfin-Ersatzbestand.

Die Anpassung führt keine schreibenden Jellyfin-Aufrufe aus und verändert keine Mediendateien. Die Schutzvorgaben aus [ADR 0004](0004-jellyfin-und-mediendaten-schuetzen.md) bleiben verbindlich.
