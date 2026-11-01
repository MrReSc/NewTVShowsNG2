# Architekturentscheidungen

Die Architecture Decision Records (ADR) halten die verbindlichen Architekturentscheidungen für NewTVShowsNG2 fest. Die folgenden Entscheidungen wurden am 1. November 2026 aufgrund der Projektvorgaben angenommen.

| ADR | Entscheidung | Status |
| --- | --- | --- |
| [0001](0001-keine-jellyfin-schattendatenbank.md) | Keine Schattendatenbank des Jellyfin-Bestands | Angenommen |
| [0002](0002-jellyfin-api-als-datenquelle.md) | Jellyfin API als Quelle für die Einsortierung | Angenommen |
| [0003](0003-readme-nur-konfigurationsbeispiele.md) | README ausschliesslich mit Konfigurationsbeispielen | Angenommen |
| [0004](0004-jellyfin-und-mediendaten-schuetzen.md) | Jellyfin und bestehende Mediendaten schützen | Angenommen |
| [0005](0005-bei-unklarheiten-nachfragen.md) | Bei Unklarheiten vor der Umsetzung nachfragen | Angenommen |
| [0006](0006-atomare-medienverschiebung.md) | Atomare Medienverschiebung ohne Inhaltsprüfsummen | Angenommen |

Der Status «Angenommen» beschreibt die verbindliche Entscheidung. Er bestätigt nicht, dass die bestehende Implementierung sie bereits vollständig erfüllt. Bekannte Abweichungen sind in den betroffenen ADRs beschrieben. Diese Dokumentation allein migriert keine Daten und ändert kein Laufzeitverhalten.

Neue Entscheidungen erhalten eine fortlaufende Nummer sowie Datum, Status, Kontext, Entscheidung und Konsequenzen. Eine spätere Änderung einer angenommenen Entscheidung wird mit einem neuen ADR und einem Verweis auf die abgelöste Entscheidung dokumentiert. Sie wird vor der Umsetzung mit dem Auftraggeber geklärt.

Die [API Referenz](../jellyfin-api.md) ergänzt die Entscheidungen um offizielle Quellen und Hinweise für die Entwicklung. Die [Projektregeln](../../AGENTS.md) machen diese Vorgaben für Agenten auffindbar.
