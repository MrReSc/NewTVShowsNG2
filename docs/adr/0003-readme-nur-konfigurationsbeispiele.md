# ADR 0003: README ausschliesslich mit Konfigurationsbeispielen

Datum: 2026-11-01

Status: Angenommen

## Kontext

Das README soll eine unmittelbar nutzbare Vorlage für den Docker-Betrieb bieten. Weitere Projektdokumentation soll diese beiden Beispiele nicht erweitern.

## Entscheidung

Das README enthält ausschliesslich ein Docker-Compose-Beispiel und ein .env-Beispiel. Dateinamen als Überschriften zur Kennzeichnung der beiden Codeblöcke sind zulässig. Weitere Beschreibungen, Anleitungen, Links, Badges, Architekturhinweise oder API-Dokumentation werden dort nicht ergänzt.

Das Compose-Beispiel entspricht [compose.yaml](../../compose.yaml). Das .env-Beispiel entspricht [.env.example](../../.env.example). Beispiele enthalten ausschliesslich Platzhalter und keine echten Zugangsdaten.

## Konsequenzen

Bei Änderungen an den Konfigurationsvorlagen werden die entsprechenden README-Beispiele im gleichen Arbeitsschritt angepasst. Architekturentscheidungen liegen unter docs/adr. Hinweise zur Jellyfin API liegen in [docs/jellyfin-api.md](../jellyfin-api.md). Agenten finden diese Dokumentation über [AGENTS.md](../../AGENTS.md).
