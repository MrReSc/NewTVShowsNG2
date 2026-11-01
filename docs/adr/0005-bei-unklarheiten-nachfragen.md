# ADR 0005: Bei Unklarheiten vor der Umsetzung nachfragen

Datum: 2026-11-01

Status: Angenommen

## Kontext

Unausgesprochene Annahmen über Serienzuordnungen, Datenhaltung oder Dateiverarbeitung können die Projektvorgaben verletzen und bestehende Daten gefährden.

## Entscheidung

Bei fachlichen oder technischen Zweifeln während der Entwicklung wird vor der betroffenen Umsetzung beim Auftraggeber nachgefragt. Dies gilt insbesondere für widersprüchliche Anforderungen, fehlende API-Informationen, mehrdeutige Zuordnungen, neue persistente Daten, Dateilöschungen, weitere Jellyfin-Schreibzugriffe und Abweichungen von angenommenen ADRs.

Die Rückfrage benennt die konkrete Unklarheit, die betroffene Entscheidung, die möglichen Folgen und eine begründete Empfehlung. Eine ausstehende Antwort ist keine Zustimmung. Bis zur Klärung wird keine abhängige Verhaltensänderung umgesetzt. Unabhängige Untersuchungen und eindeutig beauftragte Arbeiten können weitergeführt werden.

Bereits geklärte Anforderungen werden umgesetzt und nicht erneut zur Entscheidung gestellt. Der bestehende Code begründet keine stillschweigende Ausnahme von den dokumentierten Vorgaben.

## Konsequenzen

Offene Entscheidungen und bekannte Abweichungen werden sichtbar dokumentiert. Änderungen an der Architektur werden nach der Klärung in einem ADR festgehalten. Bei Mehrdeutigkeiten im laufenden Betrieb wird die betroffene Einsortierung blockiert oder eine anhand aktueller API-Daten geprüfte Auswahl verlangt. Die Anwendung ersetzt eine fehlende Entscheidung nicht durch eine Vermutung.
