# ADR 0006: Atomare Medienverschiebung ohne Inhaltsprüfsummen

Datum: 2026-11-01

Status: Angenommen

Ergänzung: [ADR 0007](0007-eine-anwendungsinstanz-ohne-dateisperre.md) legt den Betrieb mit einer Instanz und interner Serialisierung ohne zusätzliche Dateisperre fest.

## Kontext

Die vollständige Kopie und wiederholte Inhaltsprüfsummen verursachen unnötige Datenträgerzugriffe, wenn Income und Shows auf demselben Dateisystem liegen. Der Auftraggeber hat einen gemeinsamen Mount und einen ausschliesslich atomaren Verschiebepfad mit Blockierung bei nicht unterstützten Konfigurationen beauftragt. Income enthält ausschliesslich fertig geschriebene Downloads.

## Entscheidung

Diese Entscheidung präzisiert die Anforderungen an Übernahme und Quellerhalt aus [ADR 0004](0004-jellyfin-und-mediendaten-schuetzen.md). Die Quelldaten bleiben bei einer atomaren Umbenennung als dieselben Inodes erhalten. Der ursprüngliche Quellpfad entfällt mit der erfolgreichen Umbenennung. Eine spätere fehlgeschlagene Synchronisation darf keine Löschung oder automatische Rückverschiebung auslösen.

Die Anwendung verwendet ausschliesslich `renameat2` mit `RENAME_NOREPLACE` über verankerte Verzeichnisdeskriptoren. Die Vorprüfung vergleicht Geräte- und Mount-Kennungen sowie bei Btrfs die Untervolume-ID. Eingebettete Mounts, Untervolumes, symbolische Links und ungeeignete Dateitypen sind unzulässig. Nicht unterstützte Funktionen oder Dateisystemgrenzen blockieren die Übernahme. Es gibt keinen Kopierersatz.

Dateiinhalte werden weder zur Übernahme gelesen noch mit eigenen Inhaltsprüfsummen verglichen. Bestehende Metadatensignaturen für Stabilität und manuelle Auswahl bleiben zulässig. Die Quelldateien und Verzeichnisse werden vor der Umbenennung mit `fsync` gespeichert. Danach werden die Identitäten am Ziel sowie die dauerhafte Speicherung der geänderten Verzeichniseinträge geprüft. Inhaltsintegrität und Speicherung beruhen auf den Garantien des Dateisystems. Das Verfahren beweist nicht, dass ein Download vollständig oder ursprünglich fehlerfrei war.

Ein dauerhaft gespeichertes technisches SQLite-Protokoll hält relative Quell- und Zielpfade, Inode- und Dateisystemidentitäten sowie relevante Metadaten vor dem Dateisystemaufruf fest. Vorbereitete Vorgänge enthalten die Scanabsicht für den Fall einer erfolgreichen Verschiebung. Abschluss, Importstatus und Scanbedarf werden in einer gemeinsamen Transaktion verbucht. SQLite-Verbindungen verwenden `synchronous=FULL`.

Bei Wiederaufnahme werden unverändert vorhandene Quellen freigegeben und eindeutig zugehörige Ziele technisch abgeschlossen. Widersprüchliche Angaben bleiben zur manuellen Prüfung gesperrt. Fehlende Synchronisationsbestätigungen können erneut angefordert werden. Der ursprüngliche Pfad ist nach erfolgreicher Umbenennung keine Voraussetzung für den Erhalt der Daten.

Das Protokoll ist ein Betriebszustand gemäss [ADR 0001](0001-keine-jellyfin-schattendatenbank.md). Es bestätigt keine Jellyfin-Zuordnung und keinen Jellyfin-Bestand. Fachliche Entscheidungen beziehen weiterhin aktuelle Daten gemäss [ADR 0002](0002-jellyfin-api-als-datenquelle.md).

## Konsequenzen

Die Container-Konfiguration verwendet einen gemeinsamen Eltern-Mount für getrennte Income- und Shows-Unterordner. Der rein lesende Diagnosebefehl läuft unter denselben Benutzerrechten wie der Import. Ein tatsächlicher Verschiebeaufruf bleibt die endgültige Funktionsprüfung. Die Anwendung benötigt weder Administratorrechte für Btrfs-Abfragen noch zusätzliche externe Programme.

Prüfungen verwenden simulierte Jellyfin-Antworten und isolierte Verzeichnisse. Sie decken Zielkonflikte, Quelländerungen, Dateisystemgrenzen und Unterbrechungen vor und nach dem atomaren Aufruf ab. Bereits vorhandene Zwischenstände und Medien werden nicht automatisch bereinigt.

Technische Grundlagen sind [renameat2](https://man7.org/linux/man-pages/man2/rename.2.html), [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html) und die [Btrfs-Schnittstelle](https://btrfs.readthedocs.io/en/latest/btrfs-ioctl.html#btrfs-ioc-ino-lookup).
