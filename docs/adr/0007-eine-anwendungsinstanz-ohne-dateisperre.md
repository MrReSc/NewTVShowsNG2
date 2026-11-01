# ADR 0007: Eine Anwendungsinstanz ohne Dateisperre

Datum: 2026-11-01

Status: Angenommen

## Kontext

Der Auftraggeber betreibt genau einen Container mit einem Anwendungsprozess und hat die Entfernung der zusätzlichen Dateisperre beauftragt. Seit [ADR 0006](0006-atomare-medienverschiebung.md) werden keine Zwischenkopien mehr benötigt. Das frühere Staging-Verzeichnis enthält nur noch die prozessübergreifende Sperrdatei und eine `.ignore`-Datei.

## Entscheidung

Die Anwendung unterstützt eine gleichzeitig laufende Instanz für die konfigurierten Medienverzeichnisse. Automatische und manuelle Importe, Income-Scans und bestätigte Serienauswahlen werden durch die bestehende interne Sperre im Scanner serialisiert. Die Wiederaufnahme beim Start erfolgt vor dem Start der Hintergrundthreads und des HTTP-Servers.

Die zusätzliche Dateisperre mit `flock` und das automatische Anlegen von `.newtvshowsng2-staging`, `.import.lock` und `.ignore` entfallen. Das SQLite-Vorgangsprotokoll, die atomare Verschiebung mit Schutz vor Überschreiben, die Dateisystemprüfungen und die dauerhafte Speicherung gemäss ADR 0006 bleiben verbindlich.

## Konsequenzen

Mehrere gleichzeitig importierende Anwendungsprozesse oder Container mit Zugriff auf dieselben Medienverzeichnisse sind nicht unterstützt. Die rein lesende Vorprüfung darf parallel ausgeführt werden.

Vorhandene Staging-Verzeichnisse werden nicht automatisch gelöscht, da sie noch Daten früherer Versionen enthalten können. Der Auftraggeber kann einen ausschliesslich technischen Restordner bei gestopptem Dienst manuell entfernen. Die Anwendung legt ihn danach nicht erneut an. Bereits vorhandene unvollständige Importziele bleiben zur manuellen Prüfung erhalten.

Prüfungen bestätigen die interne Serialisierung sowie erfolgreiche Importe und Wiederaufnahmen ohne neu angelegtes Sperrverzeichnis.
