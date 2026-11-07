# Typografie

Diese Vorgaben definieren die Typografie der bestehenden Oberfläche von NewTVShowsNG2. Sie gelten für Feed, Medienimport, Historie, Diagnoselog, Serienauswahl und Fehlerseiten. Der Nutzungskontext steht in [PRODUCT.md](PRODUCT.md). Farben, Flächen und Bedienzustände sind in [docs/interface.md](docs/interface.md) beschrieben. Die verbindlichen CSS-Variablen stehen in [_theme.html](src/newtvshowsng2/templates/_theme.html).

## Ziel und Hierarchie

Die Oberfläche dient dem wiederholten Prüfen von Serien und Importen am Desktop. Eine Zeile wird in der Reihenfolge Serie, Episode, Bestand und Status gelesen. Die Typografie unterstützt diese Reihenfolge mit Gewicht, Abstand und klaren Textrollen. Sie benötigt keine zusätzlichen Akzentfarben oder wechselnden Schriftgrössen pro Ansicht.

Der Serientitel ist der Einstiegspunkt mit 16 Pixeln und mittlerem Gewicht. Ein Feed-Eintrag besteht aus drei Zeilen: Serientitel, Episodencode und Qualitätslinks. Der Titel beginnt an der oberen Bildkante, die Qualitätslinks enden an der unteren Bildkante. Der Episodencode steht dazwischen. In der Historie steht die Eintragsart in der dritten Zeile. Bestandswerte und Datumswerte verwenden übereinstimmend 16 Pixel, Gewicht 400 und die primäre Textfarbe. Quellen und weitere Metadaten treten zurück. Hauptaktionen behalten in allen Ansichten dieselbe Beschriftungsgrösse.

## Schrift und Funktionen

Inter 4.1 wird lokal als unveränderte variable WOFF2-Datei ausgeliefert. Herkunft und Lizenz sind in [docs/interface.md](docs/interface.md) dokumentiert. Die Systemschrift bleibt die Ersatzschrift während des Ladens. `font-display: swap` hält den Inhalt lesbar.

`font-optical-sizing: auto` passt die Zeichenformen an die jeweilige Schriftgrösse an. Normales Kerning erhält ausgeglichene Zeichenabstände. Der Zeichensatz `ss04` unterscheidet ähnliche Buchstaben wie grosses I und kleines l, ohne die Null in normalem Text zu verändern. Diese Funktionen sind im [offiziellen Inter-Verzeichnis](https://rsms.me/inter/#features) beschrieben.

Bestände, Zeitangaben und Episodencodes verwenden gleich breite Ziffern mit `tabular-nums`. Episodencodes verwenden Inter mit normalen Nullen. Die durchgestrichene Null mit `slashed-zero` bleibt technischen Providerkennungen vorbehalten. Normale Texte behalten proportionale Ziffern. Providerkennungen verwenden weiterhin die vorhandene Monospace-Ersatzschrift. Schriftvarianten für Dekoration, künstlich erzeugte Kursivschrift und zusätzliche Schriftfamilien sind nicht Teil dieses Systems.

## Grössen und Rollen

Die Skala umfasst vier Grössen. Pixelangaben beziehen sich auf die übliche Browserbasis von 16 Pixeln. Die Umsetzung verwendet `rem` und berücksichtigt dadurch die eingestellte Basisschriftgrösse.

| Rolle | Grösse | Gewicht | Zeilenhöhe | Farbe und Einsatz |
| --- | --- | --- | --- | --- |
| Seitenüberschrift | 20 px / 1,25 rem | 600 | 1,4 | Primär, sichtbare Überschriften in Serienauswahl und Fehlerseiten |
| Abschnittsüberschrift | 16 px / 1 rem | 600 | 1,4 | Primär, Überschriften der Serienauswahl |
| Eintragstitel | 16 px / 1 rem | 500 | 1,4 | Primär, Seriennamen und Quelldateien |
| Inhalt | 16 px / 1 rem | 400 | 1,6 | Primär, Bestände, Datums- und Zeitspalten, Logmeldungen und erklärende Texte |
| Bedienung | 14 px / 0,875 rem | 500 | 1,4 | Sekundär mit Zustandsfarben, Navigation, Buttons, Tabellenköpfe und aufklappbare Bereiche |
| Ergänzende Angabe | 14 px / 0,875 rem | 400 | 1,4 oder 1,6 | Sekundär, Episodencodes, Formulareingaben, Importgründe und Hinweise |
| Metadaten | 13 px / 0,8125 rem | 400 | 1,4 | Gedämpft, Quellen, Dateiziele, Formularlabels und Erzeugungsstand |
| Status | 13 px / 0,8125 rem | 500 | 1,4 | Fachliche Statusfarbe, Badges und Logstufen |

Die CSS-Variablen `--type-heading`, `--type-body`, `--type-label` und `--type-caption` bilden diese Skala ab. `--weight-regular`, `--weight-medium` und `--weight-heading` begrenzen die Gewichte auf 400, 500 und 600. Zusätzliche Zwischenwerte und automatische Browsergewichte von 700 oder 800 werden nicht verwendet. `strong` erhält Gewicht 500 und damit eine begrenzte Hervorhebung innerhalb des Inhalts.

## Farbe und Laufweite

| Textrolle | Variable | Farbe |
| --- | --- | --- |
| Primär | `--text` | `#e0e0e0` |
| Sekundär | `--text-secondary` | `#c5c5c5` |
| Gedämpft | `--muted` | `#a5a5a5` |

Primärtext trägt die Information, Sekundärtext unterstützt Bedienung und Erklärung, gedämpfter Text kennzeichnet Zusatzangaben. Farbe allein unterscheidet keinen fachlichen Zustand. Status-Badges nennen den Zustand weiterhin ausdrücklich. Ihre vorhandenen Farben für Information, Warnung, Fehler und Erfolg bleiben an diese Bedeutung gebunden. Besuchte Links und Interaktionszustände folgen der bestehenden Palette.

Status-Badges, Logstufen, Release-Links und Serienbilder verwenden denselben Eckenradius wie die Buttons mit `--radius-control` und 6 Pixeln.

Normale Texte verwenden die natürliche Laufweite von Inter. Nur die Seitenüberschrift erhält mit `--tracking-heading` eine leichte Verdichtung von −0,015 em. Beschriftungen bleiben in normaler Gross- und Kleinschreibung. Kleine Grossbuchstabenlabels und zusätzlich gesperrte Texte entfallen. Die Grossschreibung technischer Logstufen bleibt Teil ihres Inhalts.

## Abstände und Trennung

Serientitel, Episodencode und Qualitätslinks beziehungsweise Eintragsart bilden drei getrennte Zeilen. Die erste und letzte Zeile sind an den Bildkanten ausgerichtet. Der verbleibende Platz verteilt sich gleichmässig zwischen den Zeilen. Mehrere Qualitätslinks bleiben nebeneinander und behalten 6 Pixel Abstand. Die Trennung entsteht durch Position und Abstand, ohne Mittelpunkte oder ersatzweise eingefügte dekorative Zeichen.

Importziele erhalten eine eigene Zeile. Der Episodencode und der ergänzende Serientitel folgen darunter in einer Metadatenzeile mit Abstand. Bei gleichen Qualitätsstufen folgt die Release-Gruppe mit einem Leerzeichen, beispielsweise `1080p WAYNE`. Die Beschriftung bleibt ein gemeinsamer Link. Browser-Titel verwenden einen Doppelpunkt, beispielsweise `Log: NewTVShowsNG2`. Zugängliche Aktionsbeschriftungen verbinden Serienname und Episodencode mit einem Komma als Satzzeichen.

## Lesbarkeit und schmale Fenster

Die gleichen Rollen und Schriftgrössen gelten auch in schmalen Fenstern. Die Darstellung wird durch Umbruch, Anordnung und kleinere Aussenabstände angepasst. Schrift wird nicht verkleinert, um zusätzliche Inhalte unterzubringen. Kein gestalteter Text ist kleiner als die Metadatenrolle mit 13 Pixeln bei normaler Browserbasis.

Erklärende Absätze in Serienauswahl und Fehlerseiten bleiben auf etwa 72 Zeichen pro Zeile begrenzt. Die Tabellen und gleich hohen Einträge behalten ihre bestehende Struktur. Die Höhen der Textbereiche und die Bildgrössen verwenden `rem` und wachsen bei vergrösserter Basisschrift mit. Der dreizeilige Titelbereich und das Bild erhalten mit `--release-row-height` dieselbe Höhe von 5,25 rem beziehungsweise 84 Pixeln bei normaler Browserbasis. Serientitel bleiben einzeilig. Lange Titel werden mit einem Auslassungszeichen gekürzt, der vollständige Titel steht als Tooltip bereit. Bei Tastaturfokus lässt sich der Titel horizontal scrollen. Der vollständige Text bleibt im Dokument erhalten. Andere lange Texte und Pfade umbrechen weiterhin. Qualitätsvarianten bleiben direkt erreichbar.

## Weiterentwicklung und Prüfung

Neue Elemente übernehmen eine vorhandene Textrolle. Eine neue Rolle wird zuerst anhand ihres Informationszwecks begründet und hier dokumentiert. Neue lokale Zahlenwerte für Schriftgrösse oder Schriftgewicht sind keine zulässige Abkürzung.

Zur visuellen Prüfung gehören kurze und lange Serientitel, mehrere Qualitätsvarianten, offene und abgeschlossene Importe, Datumswerte, Warnungen, Fehler, leere Ansichten und Serienauswahl. Die Prüfung umfasst den bestätigten Desktop mit 1920 × 1080 Pixeln sowie schmale Fenster und eine vergrösserte Darstellung. Schriftladung, Umbruch, vollständiger Inhaltszugang, Tastaturfokus und Textkontraste sind gemeinsam zu beurteilen.
