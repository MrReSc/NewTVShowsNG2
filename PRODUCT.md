# NewTVShowsNG2

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Der Auftraggeber nutzt die Anwendung allein für seine private Jellyfin-Bibliothek. Die Bedienung erfolgt hauptsächlich am Desktop mit Maus und Tastatur. Der massgebende Bildschirm hat eine Auflösung von 1920 × 1080 Pixeln im Format 16:9.

## Product Purpose

NewTVShowsNG2 gleicht Serienveröffentlichungen aus RSS-Feeds mit Jellyfin ab und macht relevante, noch fehlende Inhalte sichtbar. Ergänzend lassen sich fertig heruntergeladene Mediendateien prüfen, Serien zuordnen und in die konfigurierte Serienablage einsortieren.

Die Oberfläche unterstützt das Prüfen fehlender Inhalte, das Bearbeiten einzelner Feed-Meldungen und das Nachvollziehen von Importen und Fehlern. Ein erfolgreicher Vorgang setzt eine verlässliche Zuordnung und den Schutz bestehender Medien voraus. Fehlende oder widersprüchliche Informationen dürfen keinen scheinbar erfolgreichen Abschluss ergeben.

## Positioning

Die Anwendung verbindet Feed-Meldungen, den aktuellen Informationsstand der eigenen Jellyfin-Instanz und den Import aus einem lokalen Eingangsverzeichnis. Jellyfin bleibt die fachliche Datenquelle für Zuordnung und Einsortierung. Feed-Bearbeitungsstatus und technische Importprotokolle beschreiben eigene Betriebsabläufe und ersetzen keinen Jellyfin-Bestand.

## Operating Context

Die Anwendung wird mit Docker Compose als eine Instanz betrieben. Konfiguration, Zugangsdaten, Medienpfade, Prüfintervall und Zeitzone werden über Umgebungsvariablen gesetzt. Die vorhandenen Konfigurationsbeispiele stehen in [compose.yaml](compose.yaml) und [.env.example](.env.example).

Automatische Verarbeitung und manuell ausgelöste Aktionen gehören zum bestehenden Funktionsumfang. Die Browseroberfläche umfasst Feed, Medienimport, Historie und Diagnoselog. Bei einer erforderlichen manuellen Serienzuordnung werden aktuelle Jellyfin-Treffer zur Auswahl angeboten. Die Bestätigung einer Auswahl löst den zugehörigen Import aus.

Die primäre Nutzungssituation ist der bestätigte Desktop-Arbeitsplatz. Die vorhandene Oberfläche berücksichtigt auch kleinere Fenster. Zusätzliche mobile Nutzungsszenarien oder weitere Nutzerrollen sind nicht festgelegt.

## Capabilities and Constraints

Unter «Aktuell fehlend» erscheinen relevante Feed-Meldungen mit Serienbezug, Staffel beziehungsweise Episode und verfügbaren Qualitätsvarianten. Die Aktion «Erledigt» betrifft ausschliesslich die angezeigten Feed-Veröffentlichungen. Sie bestätigt weder vorhandene noch gesehene Medien. Erledigte Meldungen bleiben in der Historie nachvollziehbar und können nach erneuter Prüfung wieder geöffnet werden. Eine neue GUID oder ein anderer Veröffentlichungszeitpunkt kennzeichnet eine eigenständige Meldung.

Der Medienimport unterscheidet das Prüfen des Eingangsverzeichnisses vom Einsortieren der Dateien. Unsichere Zuordnungen und Zielkonflikte blockieren den betroffenen Vorgang. Bestehende Bibliotheksmedien dürfen weder überschrieben noch gelöscht werden. Die atomare Übernahme und ihre Wiederaufnahme richten sich nach den angenommenen Architekturentscheidungen. Ein angeforderter Jellyfin-Bibliotheksscan bestätigt noch keinen durch Jellyfin abgeschlossenen Import.

Fachliche Entscheidungen benötigen aktuelle, vollständige Jellyfin-API-Antworten. Persistente Ersatzbestände und der Rückgriff auf gespeicherte Jellyfin-Statuswerte als Entscheidungsgrundlage für spätere Läufe sind ausgeschlossen. Die Instanz, ihre Konfiguration, Metadaten und Medien sind zu schützen. Weitere Jellyfin-Schreibfunktionen und Abweichungen von angenommenen Entscheidungen erfordern eine vorgängige Klärung.

Die [Projektregeln](AGENTS.md) und die angenommenen Entscheidungen der [ADR-Übersicht](docs/adr/index.md) sind verbindlich. Dort dokumentierte Abweichungen der bestehenden Umsetzung gelten weiterhin als offene Abweichungen. Diese Produktbeschreibung bestätigt keine vollständige Umsetzung und trifft keine neue Architekturentscheidung. Architektur-, Entwicklungs- und API-Hinweise gehören nach docs. Das [README](README.md) bleibt auf die beiden Konfigurationsbeispiele beschränkt.

## Brand Commitments

Der bestehende Produktname lautet NewTVShowsNG2. Texte verwenden Schweizer Rechtschreibung und einen nüchternen, gut lesbaren technischen Stil. Im Fliesstext werden keine Emojis, Semikolons, Gedankenstriche oder Hervorhebungen durch Fett- oder Kursivschrift verwendet. Aufzählungen bleiben sparsam.

Der Auftraggeber bevorzugt ein dunkles Erscheinungsbild in Schwarz und neutralen Grautönen mit sauberer, klarer Typografie. Die Oberfläche soll leicht und luftig wirken. Informationen werden zurückhaltend dosiert und bei Bedarf zugänglich gemacht. Dezente Farbakzente kennzeichnen fachliche Statuswerte, Warnungen und Fehler. Anpassungen entwickeln das bestehende Design behutsam weiter.

## Evidence on Hand

Die vorhandenen Ansichten und ihre tatsächlichen Beschriftungen stehen in [index.html](src/newtvshowsng2/templates/index.html), [series_selection.html](src/newtvshowsng2/templates/series_selection.html) und [log.html](src/newtvshowsng2/templates/log.html). Der bestehende technische Aufbau verwendet Python, Jinja2 und serverseitig erzeugtes HTML mit CSS.

Serienposter werden über die konfigurierte Jellyfin-Instanz bezogen. Bei fehlender oder unsicherer Zuordnung steht ein vorhandener Platzhalter bereit. Die Herkunft, Grenzen und Darstellung dieser Bilder beschreibt [Serienbilder in Fehlend und Historie](docs/series-images.md). Das vorhandene [Favicon](src/newtvshowsng2/static/favicon.svg) und der [Serienplatzhalter](src/newtvshowsng2/static/series-placeholder.svg) sind Projektressourcen.

Die [automatisierten Prüfungen](tests) enthalten simulierte Jellyfin-Antworten und isolierte Dateisystemfälle. Sie dienen als technische Nachweise für die jeweils geprüften Verhaltensweisen. Sie ersetzen keine bestätigten Angaben zur Nutzung oder zum Produktnutzen.

## Product Principles

Die Sicherheit der Jellyfin-Instanz und bestehender Medien bestimmt die Grenzen der Automatisierung. Unklarheiten bleiben sichtbar und blockieren den betroffenen Vorgang, bis eine verlässliche Entscheidung möglich ist.

Feed-Bearbeitung, Dateiübernahme und Bestätigung durch Jellyfin müssen fachlich unterscheidbar bleiben. Statusanzeigen beschreiben den tatsächlich erreichten Zustand.

Die Bedienung richtet sich nach der privaten Einzelnutzung am Desktop. Wiederkehrende Prüfungen und gezielte Eingriffe sollen mit Maus und Tastatur nachvollziehbar ausführbar sein.

Produktentscheidungen stützen sich auf bestätigte Anforderungen und vorhandene Nachweise. Offene Fragen werden benannt und vor einer davon abhängigen Verhaltensänderung geklärt.
