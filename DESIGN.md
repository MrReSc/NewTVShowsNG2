---
version: alpha
name: Neutrale Anwendungsoberfläche
description: Dunkles, wiederverwendbares Designsystem mit lokalem Inter, Graustufen und klaren Datenrollen.
colors:
  background: '#121212'
  surface: '#191919'
  surface-hover: '#222222'
  border: '#333333'
  text: '#e0e0e0'
  text-secondary: '#c5c5c5'
  muted: '#a5a5a5'
  accent: '#c5c5c5'
  accent-soft: '#282828'
  link: '#c5c5c5'
  visited: '#b0b0b0'
  info: '#98bee8'
  info-soft: '#1e2b3b'
  success: '#a0c8af'
  success-soft: '#202d26'
  warning: '#dfc18e'
  warning-soft: '#30291e'
  danger: '#e6aaa4'
  danger-soft: '#352522'
  control: '#262626'
  control-hover: '#333333'
  control-pressed: '#1f1f1f'
  control-selected: '#3b3b3b'
  control-selected-hover: '#484848'
  control-disabled: '#1d1d1d'
  control-border: '#6b6b6b'
  control-border-hover: '#909090'
  control-border-pressed: '#a5a5a5'
  control-border-selected: '#858585'
  control-border-disabled: '#3b3b3b'
  control-text: '#c5c5c5'
  control-text-hover: '#f0f0f0'
  control-text-disabled: '#808080'
  control-focus: '#c5c5c5'
  control-visited: '#c5c5c5'
  control-visited-hover: '#dedede'
  control-on-visited: '#161616'
  selection: '#555555'
  selection-text: '#ffffff'
  warning-border: '#63513a'
  danger-border: '#704d47'
  notice-border: '#585858'
  current-border: '#414141'
  image-placeholder: '#252525'
  image-placeholder-stroke: '#777777'
  transparent: transparent
typography:
  heading:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 1.25rem
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: -0.015em
    fontFeature: '"ss04" 1'
  section-heading:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  title:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 1rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  body:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  label:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  secondary:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  secondary-prose:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  caption:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  badge:
    fontFamily: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 0.8125rem
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: '"ss04" 1'
  code:
    fontFamily: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0em
    fontFeature: normal
rounded:
  detail: 3px
  control: 6px
  surface: 10px
spacing:
  micro: 2px
  related: 4px
  inline: 6px
  control-block: 8px
  compact: 10px
  group: 12px
  item: 14px
  panel: 16px
  row: 18px
  cell: 20px
  section: 24px
  page: 32px
  page-bottom: 56px
  selection-bottom: 64px
components:
  button:
    backgroundColor: '{colors.control}'
    textColor: '{colors.control-text}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 8px 14px
  button-hover:
    backgroundColor: '{colors.control-hover}'
    textColor: '{colors.control-text-hover}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 8px 14px
  button-pressed:
    backgroundColor: '{colors.control-pressed}'
    textColor: '{colors.control-text-hover}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 8px 14px
  button-disabled:
    backgroundColor: '{colors.control-disabled}'
    textColor: '{colors.control-text-disabled}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 8px 14px
  button-compact:
    backgroundColor: '{colors.control}'
    textColor: '{colors.control-text}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 5px 10px
  input:
    backgroundColor: '{colors.control}'
    textColor: '{colors.control-text}'
    typography: '{typography.secondary}'
    rounded: '{rounded.control}'
    padding: 8px 10px
  navigation:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.control-text}'
    typography: '{typography.label}'
    rounded: '{rounded.surface}'
    padding: 5px
  navigation-item:
    backgroundColor: '{colors.transparent}'
    textColor: '{colors.control-text}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 9px 17px
  navigation-item-selected:
    backgroundColor: '{colors.accent}'
    textColor: '{colors.background}'
    typography: '{typography.label}'
    rounded: '{rounded.control}'
    padding: 9px 17px
  source-link:
    backgroundColor: '{colors.control}'
    textColor: '{colors.control-text}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 9px
  source-link-visited:
    backgroundColor: '{colors.control-visited}'
    textColor: '{colors.control-on-visited}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 9px
  panel:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    typography: '{typography.body}'
    rounded: '{rounded.surface}'
  choice-card:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    typography: '{typography.body}'
    rounded: '{rounded.surface}'
    padding: 24px
  image:
    backgroundColor: '{colors.image-placeholder}'
    rounded: '{rounded.control}'
    width: 3.5rem
    height: 5.25rem
  notice-neutral:
    backgroundColor: '{colors.accent-soft}'
    textColor: '{colors.text}'
    typography: '{typography.body}'
    rounded: '{rounded.surface}'
    padding: 18px 20px
  notice-warning:
    backgroundColor: '{colors.warning-soft}'
    textColor: '{colors.warning}'
    typography: '{typography.body}'
    rounded: '{rounded.surface}'
    padding: 18px 20px
  notice-error:
    backgroundColor: '{colors.danger-soft}'
    textColor: '{colors.danger}'
    typography: '{typography.body}'
    rounded: '{rounded.surface}'
    padding: 18px 20px
  badge-info:
    backgroundColor: '{colors.info-soft}'
    textColor: '{colors.info}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 8px
  badge-success:
    backgroundColor: '{colors.success-soft}'
    textColor: '{colors.success}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 8px
  badge-warning:
    backgroundColor: '{colors.warning-soft}'
    textColor: '{colors.warning}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 8px
  badge-danger:
    backgroundColor: '{colors.danger-soft}'
    textColor: '{colors.danger}'
    typography: '{typography.badge}'
    rounded: '{rounded.control}'
    padding: 3px 8px
---

# Designsystem: Neutrale Anwendungsoberfläche

## Overview

Leitgedanke: Klarheit durch Zurückhaltung.

Die Oberfläche ist dunkel, sachlich und ruhig. Neutrale Flächen, eine kompakte Typografie und erkennbare Abstände unterstützen das wiederholte Prüfen und Bearbeiten von Informationen. Die Gestaltung wirkt luftig durch die Trennung von Arbeitsgruppen und präzise durch die Ausrichtung innerhalb eines Eintrags. Inhalte, Bestandswerte, Zeitangaben und Aktionen stehen im Vordergrund.

Die visuelle Identität entsteht aus Inter, drei Texthelligkeiten, vier Schriftgrössen, wenigen Gewichten und einer gemeinsamen Formensprache. Farbe kennzeichnet fachliche Zustände. Navigation, Buttons und Formulare verwenden Graustufen. Die Oberfläche verwendet weder dekorative Verläufe noch Schatten oder animierte Aufmerksamkeitseffekte.

### Geltung und Übertragbarkeit

Diese Spezifikation beschreibt das in NewTVShowsNG2 umgesetzte Design mit Stand 7. November 2026. Ihr allgemeiner Teil lässt sich auf andere datenorientierte Webanwendungen übertragen. Produktnamen, Datenquellen, fachliche Statusbedeutungen und konkrete Seitenabläufe werden im Zielprojekt separat festgelegt. Die hier gezeigten Komponenten benötigen kein bestimmtes Frontend-Framework.

Die YAML-Tokens am Dateianfang definieren die Werte. Die folgenden Abschnitte erklären ihre Anwendung. Die Abschnittstitel folgen dem [DESIGN.md-Format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md). Die Sprache der fachlichen Beschriftungen kann im Zielprojekt angepasst werden.

Die Datei ist als eigenständige Vorlage lesbar. Für die Umsetzung werden zusätzlich die Fontdatei und deren Lizenz benötigt. Die optionale Begleitdatei `.impeccable/design.json` enthält ausführbare HTML- und CSS-Beispiele für Designwerkzeuge. Sie ergänzt diese Spezifikation um Darstellungsmetadaten. Ihre abgeleiteten Tonwertreihen sind Vorschauhilfen und keine zusätzlichen freigegebenen Anwendungsfarben.

### Übernahme in ein anderes Projekt

1. Diese Datei als `DESIGN.md` in das Zielprojekt übernehmen und Geltungsbereich sowie Produktbeispiele anpassen.
2. Inter 4.1 und die unveränderte Lizenz lokal bereitstellen. Den Fontpfad in Preload und `@font-face` gemeinsam setzen.
3. Die CSS-Basis aus Typography übernehmen. Die Farb-, Typografie- und Radiusvariablen zentral halten.
4. Die benötigten Komponenten aus Components umsetzen. Die Begleitdatei kann als ausführbare Referenz mitkopiert werden.
5. Mit den Kriterien unter Do's and Don'ts prüfen, insbesondere lange Texte, Tastaturbedienung, Schriftvergrösserung und schmale Fenster.

Im bestehenden Projekt liegen die gemeinsamen Werte in [der Theme-Datei](src/newtvshowsng2/templates/_theme.html). Die Ansichten stehen in [index.html](src/newtvshowsng2/templates/index.html), [log.html](src/newtvshowsng2/templates/log.html), [series_selection.html](src/newtvshowsng2/templates/series_selection.html) und [error.html](src/newtvshowsng2/templates/error.html). Diese Links dienen als Herkunftsnachweis und können nach dem Kopieren in ein anderes Projekt ersetzt werden. Die projektbezogenen Abläufe sind in [docs/interface.md](docs/interface.md) beschrieben.

## Colors

### Neutrale Grundpalette

Die Palette basiert auf annähernd schwarzem Hintergrund und neutralen Graustufen. Helligkeit ordnet die Flächen, Konturen und Texte. Es gibt keine farbige Markenfläche für primäre Aktionen. Der neutrale Akzent dient Fokus und Interaktion.

| Rolle | Token / CSS-Variable | Anwendung |
| --- | --- | --- |
| Seitenhintergrund | `background` / `--background` | Grundfläche hinter allen Inhalten |
| Inhaltsfläche | `surface` / `--surface` | Tabellen, Panels, Filter, Auswahlmöglichkeiten und Navigation |
| Zeile unter dem Zeiger | `surface-hover` / `--surface-hover` | Hervorhebung eines Dateneintrags beim Überfahren |
| Flächenkontur | `border` / `--border` | Trennlinien und Umrisse übergeordneter Flächen |
| Primärtext | `text` / `--text` | Titel, Inhalte, Bestände, Datum und Uhrzeit |
| Sekundärtext | `text-secondary` / `--text-secondary` | Bedienung, ergänzende Angaben und Episodencodes |
| Gedämpfter Text | `muted` / `--muted` | Quellen, Hilfslabels, Dateiziele und Erzeugungsstand |
| Neutraler Akzent | `accent` / `--accent` | Zurückhaltende Hervorhebung innerhalb der Graupalette |
| Neutrale Hinweisfläche | `accent-soft` / `--accent-soft` | Laufhinweise und neutrale Logstufen |

Die exakten Farbwerte stehen im Frontmatter und in der CSS-Basis. Gleich aussehende Werte behalten getrennte Rollen, wenn sie unterschiedliche Zwecke erfüllen. Beispielsweise haben Sekundärtext, Fokus und der neutrale Akzent denselben aktuellen Hexwert. Eine spätere Anpassung einer Rolle soll die anderen Rollen nicht automatisch verändern.

### Fachliche Zustandsfarben

| Bedeutung | Text-Token | Flächen-Token | Beispiel aus dem Quellprojekt |
| --- | --- | --- | --- |
| Information | `info` | `info-soft` | Neu erkannte Veröffentlichung |
| Erfolg oder erreichter Zustand | `success` | `success-soft` | Übernommener Import oder erledigte Meldung |
| Warnung oder Handlungsbedarf | `warning` | `warning-soft` | Fehlende Folge oder ausstehende Prüfung |
| Fehler oder blockierter Vorgang | `danger` | `danger-soft` | Zielkonflikt oder fehlende Serienzuordnung |

Ein Status wird immer ausgeschrieben. Ein farbiger Punkt allein trägt keine fachliche Aussage. Blau kennzeichnet Information und wird nicht als allgemeine Linkfarbe verwendet. Grün bestätigt ausschliesslich den tatsächlich erreichten Zustand. Die konkrete Bedeutung eines Status wird im Zielprojekt mit dem jeweiligen Ablauf festgelegt.

### Interaktionszustände

Diese Tabelle gilt für neutrale Buttons, Eingaben, Auswahllisten und Aktionslinks. Die Token-Namen entsprechen den CSS-Variablen ohne führende Bindestriche.

| Zustand | Fläche | Kontur | Text |
| --- | --- | --- | --- |
| Normal | `control` | `control-border` | `control-text` |
| Hover | `control-hover` | `control-border-hover` | `control-text-hover` |
| Gedrückt | `control-pressed` | `control-border-pressed` | `control-text-hover` |
| Ausgewählt oder aufgeklappt | `control-selected` | `control-border-selected` | `control-text-hover` |
| Ausgewählt mit Hover | `control-selected-hover` | `control-border-hover` | `control-text-hover` |
| Deaktiviert | `control-disabled` | `control-border-disabled` | `control-text-disabled` |
| Tastaturfokus | Bisherige Zustandsfläche | `control-focus` | Bisherige Zustandsfarbe |

Geschlossene aufklappbare Beschriftungen beginnen mit transparenter Fläche und Kontur. Hover und Auswahl verwenden danach dieselben Zustandsfarben wie Buttons. Die Navigation verwendet die unter Navigation beschriebenen Flächen mit einer hellen Auswahl und einer dunklen Hover-Fläche. Fokus ist ein zusätzlicher Zustand und ersetzt die ausgewählte Fläche nicht.

### Links und Besuchsmarkierung

Normale Textlinks sind unterstrichen. Ihre Grundfarbe kommt aus `link`, besuchte Links verwenden `visited`. Der Abstand der Unterstreichung beträgt 3 px. Unbesuchte Eintragstitel verwenden die primäre Textfarbe. Textlinks erhalten dieselben Hover- und Druckfarben wie die übrige Bedienung.

Kompakte Quellen- beziehungsweise Release-Links sind umrandete Aktionslinks. Besuchte Links erhalten `control-visited` als Fläche und Kontur sowie `control-on-visited` als dunkle Schrift. Beim Überfahren wird die Fläche mit `control-visited-hover` heller. Beim Drücken bleibt die Besuchsmarkierung erhalten und die Kontur verwendet `control-border-pressed`.

Die Besuchsmarkierung basiert auf dem Browserverlauf. Sie bestätigt weder die Bearbeitung eines Eintrags noch den Erfolg einer Aktion. In einem anderen Projekt wird diese Darstellung nur für Links übernommen, bei denen der Linkbesuch eine nützliche Information ist.

### Browserdarstellung und ergänzende Farben

| Anwendung | Wert oder Zuordnung |
| --- | --- |
| Textauswahl | Fläche `selection`, Text `selection-text` |
| Schreibmarke und Formularakzent | `control-focus` |
| Scrollbar-Daumen | `control-border` |
| Scrollbar-Spur | `background` beziehungsweise `surface` im Tabellenbereich |
| Warnungskontur | `warning-border` |
| Fehlerkontur | `danger-border` |
| Kontur eines neutralen Laufhinweises | `notice-border` |
| Hervorgehobene aktuelle Tabelle | `current-border` |
| Bildplatzhalter | Fläche `image-placeholder`, SVG-Strich `image-placeholder-stroke` |

Warnungs- und Fehlerkonturen gehören zur jeweiligen semantischen Fläche. Es wird keine zusätzliche beliebige Farbe pro Meldung eingeführt. Die ergänzenden Farben sind im Quellcode teilweise lokale Werte. Das Frontmatter benennt sie für die Wiederverwendung, ohne daraus neue Gestaltungsvarianten abzuleiten.

## Typography

### Schriftfamilien und Auslieferung

Inter ist die einzige Schriftfamilie für die reguläre Bedienoberfläche. Sie trägt Überschriften, Eintragstitel, Inhalte, Formulare, Navigation, Zahlen und Status. Die Monospace-Ersatzschrift bleibt technischen Kennungen und tatsächlichem Code vorbehalten. Episodencodes, Datum und Uhrzeit verwenden Inter.

| Rolle | Font-Stack |
| --- | --- |
| Oberfläche | `"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` |
| Technische Kennungen | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` |

Verwendet wird die unveränderte normale variable Schrift aus [Inter 4.1](https://github.com/rsms/inter/tree/v4.1). Die [WOFF2-Datei](https://raw.githubusercontent.com/rsms/inter/v4.1/docs/font-files/InterVariable.woff2) und die [SIL Open Font License 1.1](https://github.com/rsms/inter/blob/v4.1/LICENSE.txt) werden zusammen mit der Anwendung ausgeliefert. Im Quellprojekt liegen sie unter [static/fonts](src/newtvshowsng2/static/fonts/LICENSE.txt). Für diese Oberfläche wird keine separate Kursivdatei geladen.

Der Browser lädt die Schrift vom eigenen Ursprung. Die folgende Einbindung setzt voraus, dass die Datei unter `/fonts/inter-4.1.woff2` erreichbar ist. Ein anderes Zielprojekt kann den Pfad gemeinsam in beiden Stellen anpassen.

```html
<link rel="preload" href="/fonts/inter-4.1.woff2"
      as="font" type="font/woff2" crossorigin>
```

```css
@font-face {
  font-family: "Inter";
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
  src: url("/fonts/inter-4.1.woff2") format("woff2");
}
```

Der Server liefert `font/woff2`. Eine versionierte URL erlaubt langfristige Zwischenspeicherung. Im Quellprojekt gilt `Cache-Control: public, max-age=31536000, immutable`. Die HTML-Sicherheitsrichtlinie enthält `font-src 'self'`. Bei einer anderen Dateiversion ändert sich auch die URL. Während des Ladens bleibt die Systemschrift sichtbar.

### Grössen, Gewichte und Rollen

Die Skala besteht aus vier Grössen. Pixelangaben beziehen sich auf eine Browserbasis von 16 px. Die Umsetzung verwendet `rem`, ohne die Basisschriftgrösse auf einen festen Pixelwert zu setzen. Die Skala ist auf Arbeitsoberflächen abgestimmt und enthält keine zusätzliche Display- oder Marketinggrösse.

| Rolle | Token | Grösse | Gewicht | Zeilenhöhe | Farbe |
| --- | --- | --- | --- | --- | --- |
| Seitenüberschrift | `heading` | 20 px / 1,25 rem | 600 | 1,4 | Primär |
| Abschnittsüberschrift | `section-heading` | 16 px / 1 rem | 600 | 1,4 | Primär |
| Eintragstitel | `title` | 16 px / 1 rem | 500 | 1,4 | Primär |
| Inhalt und Daten | `body` | 16 px / 1 rem | 400 | 1,6 | Primär |
| Bedienung | `label` | 14 px / 0,875 rem | 500 | 1,4 | Sekundär beziehungsweise Zustandsfarbe |
| Ergänzende Angabe | `secondary` | 14 px / 0,875 rem | 400 | 1,4 | Sekundär |
| Ergänzender Erklärungstext | `secondary-prose` | 14 px / 0,875 rem | 400 | 1,6 | Sekundär |
| Metadaten | `caption` | 13 px / 0,8125 rem | 400 | 1,4 | Gedämpft |
| Status | `badge` | 13 px / 0,8125 rem | 500 | 1,4 | Fachliche Statusfarbe |
| Technische Kennung | `code` | 13 px / 0,8125 rem | 400 | 1,4 | Gedämpft, Monospace |

Bestand, Datum und Uhrzeit verwenden dieselbe Datenrolle mit 16 px, Gewicht 400, Zeilenhöhe 1,6 und primärer Textfarbe. Wesentliche Daten werden nicht auf die Metadatenrolle verkleinert. Tabellenköpfe und Buttons verwenden die Bedienrolle. Formularlabels, Quellen, Dateiziele und der Erzeugungsstand verwenden die Metadatenrolle. Ein Episodencode ist eine ergänzende Angabe mit 14 px.

Es gibt genau drei reguläre Schriftgewichte. `strong` und `b` erhalten 500. Nur Überschriften verwenden 600. Die reguläre Oberfläche verwendet weder 700 noch 800. Eine neue Komponente übernimmt eine vorhandene Rolle.

### Inter-Funktionen

| Einstellung | Einsatz und Zweck |
| --- | --- |
| `font-optical-sizing: auto` | Passt die Zeichenformen an die verwendete Grösse an |
| `font-kerning: normal` | Erhält den regulären optischen Ausgleich zwischen Zeichen |
| `font-feature-settings: "ss04" 1` | Unterscheidet ähnliche Buchstaben wie grosses I und kleines l, ohne durchgestrichene Null |
| `font-variant-numeric: lining-nums tabular-nums` | Bestände, Datum, Uhrzeit und Episodencodes erhalten gleich breite Ziffern |
| `font-variant-numeric: slashed-zero` | Nur technische Kennungen erhalten die durchgestrichene Null, sofern ihre Monospace-Schrift diese Funktion unterstützt |

Die Bedeutung der Inter-Funktionen ist im [offiziellen Funktionsverzeichnis](https://rsms.me/inter/#features) beschrieben. Normale Texte behalten proportionale Ziffern. Technische Kennungen erhalten keine dekorative Sonderdarstellung darüber hinaus. Es werden keine manuellen Werte für die variable Gewichtsachse verwendet, die von 400, 500 oder 600 abweichen.

Formularelemente übernehmen Schrift und OpenType-Einstellungen. Bei CSS-Kurzformen für `font` ist auf unbeabsichtigte Rücksetzungen zu achten. Die regulären Bedienkomponenten setzen ihre Schrift deshalb über einzelne Eigenschaften.

### Laufweite, Umbruch und Sprache

Die Seitenüberschrift verwendet eine leichte Verdichtung von `-0.015em`. Alle anderen Textrollen verwenden die natürliche Laufweite. Es gibt keine gesperrten Labels und keine erzwungenen kleinen Grossbuchstaben. Technische Logstufen wie `WARNING` behalten ihre fachliche Schreibweise.

Überschriften verwenden `text-wrap: balance`, Absätze `text-wrap: pretty`. Diese Eigenschaften ergänzen den normalen Umbruch. Erklärende Absätze sind auf etwa 72 Zeichen pro Zeile begrenzt. Lange Pfade dürfen an beliebiger Stelle umbrechen, wenn sonst ein horizontaler Überlauf entsteht.

Texte verwenden Schweizer Rechtschreibung und einen nüchternen technischen Stil. Beschriftungen nennen die Aktion. Fehlertexte nennen Ursache und nächsten sinnvollen Schritt. Im Fliesstext werden keine Emojis, Semikolons, Gedankenstriche oder zusätzlichen Fett- und Kursivhervorhebungen verwendet. Die gestalterische Trennung von Angaben erfolgt ohne Mittelpunkte. Browser-Titel können einen Doppelpunkt verwenden. Eine vollständige Aktionsbeschriftung kann Serienname und Episodencode mit einem Komma verbinden.

### Kopierbare CSS-Basis

Der folgende Block übernimmt die gemeinsamen Werte des Quellprojekts. Die Alias-Beziehungen bleiben erhalten. Zusätzliche lokale Farben sind im Frontmatter benannt und werden in den betreffenden Komponenten beschrieben. Die Schriftdatei wird separat wie oben eingebunden.

```css
/* Gemeinsame Rollen halten Komponenten auch bei späteren Anpassungen konsistent. */
:root {
  color-scheme: dark;
  --font-interface: "Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-data: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --type-caption: .8125rem;
  --type-label: .875rem;
  --type-body: 1rem;
  --type-heading: 1.25rem;
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-heading: 600;
  --leading-compact: 1.4;
  --leading-body: 1.6;
  --tracking-heading: -.015em;
  --background: #121212;
  --surface: #191919;
  --surface-hover: #222222;
  --border: #333333;
  --text: #e0e0e0;
  --text-secondary: #c5c5c5;
  --muted: #a5a5a5;
  --accent: #c5c5c5;
  --accent-soft: #282828;
  --link: var(--control-text);
  --visited: #b0b0b0;
  --info: #98bee8;
  --info-soft: #1e2b3b;
  --success: #a0c8af;
  --success-soft: #202d26;
  --warning: #dfc18e;
  --warning-soft: #30291e;
  --danger: #e6aaa4;
  --danger-soft: #352522;
  --control: #262626;
  --control-hover: #333333;
  --control-pressed: #1f1f1f;
  --control-selected: #3b3b3b;
  --control-selected-hover: #484848;
  --control-disabled: #1d1d1d;
  --control-border: #6b6b6b;
  --control-border-hover: #909090;
  --control-border-pressed: #a5a5a5;
  --control-border-selected: #858585;
  --control-border-disabled: #3b3b3b;
  --control-text: var(--text-secondary);
  --control-text-hover: #f0f0f0;
  --control-text-disabled: #808080;
  --control-focus: #c5c5c5;
  --control-visited: #c5c5c5;
  --control-visited-hover: #dedede;
  --control-on-visited: #161616;
  --radius-detail: 3px;
  --radius-control: 6px;
  --radius-surface: 10px;
  --navigation-offset: 24px;
}

* { box-sizing: border-box; }
html {
  min-height: 100%;
  background: var(--background);
  scrollbar-color: var(--control-border) var(--background);
}
body {
  min-height: 100vh;
  margin: 0;
  background: var(--background);
  color: var(--text);
  font-family: var(--font-interface);
  font-size: var(--type-body);
  font-weight: var(--weight-regular);
  line-height: var(--leading-body);
  font-optical-sizing: auto;
  font-kerning: normal;
  font-feature-settings: "ss04" 1;
}
button, input, select, textarea {
  font: inherit;
  font-feature-settings: inherit;
  letter-spacing: inherit;
}
h1, h2 { text-wrap: balance; }
h1 {
  font-size: var(--type-heading);
  font-weight: var(--weight-heading);
  line-height: var(--leading-compact);
  letter-spacing: var(--tracking-heading);
}
h2 {
  font-size: var(--type-body);
  font-weight: var(--weight-heading);
  line-height: var(--leading-compact);
}
p { text-wrap: pretty; }
strong, b { font-weight: var(--weight-medium); }
small {
  font-size: var(--type-caption);
  line-height: var(--leading-compact);
}
a {
  color: var(--link);
  border-radius: var(--radius-control);
  text-underline-offset: 3px;
}
a:visited { color: var(--visited); }
:focus-visible {
  outline: 2px solid var(--control-focus);
  outline-offset: 3px;
}
::selection { background: #555555; color: #ffffff; }
```

Die Basis setzt noch keine Button-, Formular- oder Tabellengeometrie. Diese folgt den nachstehenden Komponentenvorgaben. Für ein anderes Produkt dürfen Komponentennamen geändert werden, die Bedeutung der Rollen bleibt erhalten.

## Layout

### Arbeitsfläche und Inhaltsbreiten

Das Layout zentriert eine begrenzte Arbeitsfläche. Tabellen nutzen deren Breite, erklärende Texte eine kleinere Lesebreite. Innenabstände gruppieren Informationen. Wiederkehrende Aktionen beginnen an derselben linken Inhaltskante.

| Bereich | Geometrie des Quellprojekts |
| --- | --- |
| Breite Arbeitsfläche | `min(1320px, calc(100% - 64px))` |
| Breite Arbeitsfläche bis 760 px | Basis `calc(100% - 32px)` |
| Tabellen und Log bis 760 px | `min(calc(100% - 24px), 680px)` |
| Fehleransicht bis 760 px | `calc(100% - 24px)` |
| Auswahl- beziehungsweise Prüfseite | `min(820px, calc(100% - 32px))` |
| Textabsätze in Prüf- und Fehleransichten | Höchstens `72ch` |
| Oberer Abstand der Arbeitsfläche | 24 px, bis 760 px 16 px |
| Unterer Abstand der Arbeitsfläche | 56 px |
| Eigenständige Auswahlseite | Aussenabstand oben 32 px, unten 64 px |

Diese Breiten sind übertragbare Ausgangswerte. Die Zahl der Spalten und die Fachinhalte eines anderen Projekts können andere Inhaltsbreiten benötigen. Die Maximalbreite wird nicht durch eine zusätzliche dekorative Seitenleiste ausgefüllt.

### Abstände und Rhythmus

Die Abstände sind aus den vorhandenen Komponenten erfasst. Das Quellprojekt hat dafür noch keine zentrale CSS-Abstandsskala. Das Frontmatter gibt ihnen gemeinsame Namen für die Übernahme. Die Oberfläche folgt keinem nachträglich behaupteten strikten 8-Pixel-Raster.

| Token | Wert | Wiederkehrender Zweck |
| --- | --- | --- |
| `micro` | 2 px | Kleine Korrekturen in der kompakten Navigation |
| `related` | 4 px | Eng zusammengehörige Angaben und kleinere Abstände |
| `inline` | 6 px | Gruppen von Qualitätslinks, Badges und Formularlabels |
| `control-block` | 8 px | Vertikaler Button-Innenabstand und Statusaktionen |
| `compact` | 10 px | Kompakte horizontale Innenabstände und mobile Datenzeilen |
| `group` | 12 px | Benachbarte Buttons, Formularfelder und Aktionsgruppen |
| `item` | 14 px | Abstand zwischen Bild und Text, horizontaler Button-Innenabstand |
| `panel` | 16 px | Innenabstand einfacher Form- und Fehlerflächen |
| `row` | 18 px | Vertikaler Abstand in Desktop-Datenzeilen |
| `cell` | 20 px | Horizontaler Abstand in Datenzeilen und breiteren Meldungen |
| `section` | 24 px | Trennung zwischen Aktionen und Inhalten, Auswahlkarten |
| `page` | 32 px | Desktop-Aussenabstand und Beginn eigenständiger Auswahlseiten |
| `page-bottom` | 56 px | Abschluss der normalen Arbeitsfläche |
| `selection-bottom` | 64 px | Abschluss eigenständiger Auswahlseiten |

Eine Aktionsgruppe ist von der nachfolgenden Tabelle oder Filterfläche 24 px entfernt. Verwandte Aktionen stehen mit 12 px Abstand nebeneinander und dürfen umbrechen. Zwischen Inhalt und Erzeugungsstand liegen im Quellprojekt 30 px. Grössere Gruppen erhalten mehr Abstand als die Angaben innerhalb derselben Gruppe.

### Responsive Verhalten

| Grenze | Änderung |
| --- | --- |
| Bis 800 px | Logeinträge wechseln von drei Spalten zu einer zweizeiligen Anordnung |
| Bis 760 px | Datentabellen werden zu Eintragskarten, Aussenabstände werden kleiner, Kopfabstand wird 16 px |
| Bis 470 px | Navigation reduziert Abstand auf 2 px, Innenabstand auf 4 px und Link-Innenabstand seitlich auf 6 px |

Die Schriftrollen behalten ihre Grössen. Platz wird durch Anordnung, Umbruch und kleinere Aussenabstände gewonnen. Flex- und Grid-Kinder mit langen Inhalten erhalten `min-width: 0`. Einspaltige mobile Grids verwenden `minmax(0, 1fr)`, damit lange Titel keine Karten verbreitern.

Der dreizeilige Eintrag behält seine Ausrichtung zum Bild auch in schmalen Fenstern. Qualitätslinks bleiben in einer Zeile und sind bei Bedarf horizontal scrollbar. Lange Titel werden gekürzt und bleiben vollständig zugänglich. Andere Inhalte wie Pfade und Meldungen dürfen umbrechen.

## Elevation & Depth

### Flächen und Konturen

Die Oberfläche ist flach. Tiefe entsteht durch die abgestuften Flächen `background`, `surface` und die Interaktionsflächen. Panels erhalten eine Kontur von 1 px. Hover, Auswahl und Fokus ändern Helligkeit und Kontur. Es gibt keine Schattenwerte, keine Leuchteffekte und keine weichgezeichneten Hintergrundflächen im bestehenden System.

Eine Fläche wird durch ihre Kontur und ihren Ton erkennbar. Kleine Bedienelemente erhalten stärkere Konturen als grosse Inhaltsflächen. Die stärkere aktuelle Tabelle verwendet `current-border`. Es wird nicht zusätzlich ein Schatten eingeführt, um dieselbe Abgrenzung nochmals zu zeichnen.

### Feste Kopfzeile

Die Kopfzeile bleibt beim Scrollen mit `position: sticky` und `z-index: 5` im Inhaltskontext. Ihr Abstand zum oberen Fensterrand entspricht `--navigation-offset`. Ihre deckende Hintergrundfläche und eine nach oben erweiterte Abdeckung verhindern, dass Text zwischen Fensterrand und Navigation durchscheint. Unter der Kopfzeile liegen 12 px Innenabstand und 24 px Aussenabstand. Bis 760 px beträgt der Aussenabstand 20 px.

Die Zahl 5 ist eine lokale Ebenenentscheidung. Das Quellprojekt definiert keine Ebenenhierarchie für Dialoge, Popovers oder modale Overlays. Diese Komponenten erhalten im Zielprojekt eine eigene, explizite Entscheidung.

### Bewegung und Rückmeldung

Das bestehende Design verwendet keine CSS-Animationen und keine Übergangszeiten. Zustandsfarben ändern sich unmittelbar. Laufende Verarbeitung wird durch verständlichen Text und die Verfügbarkeit der Aktionen sichtbar. Die Oberfläche beginnt bereits sichtbar und ist nicht von einer Eintrittsanimation abhängig.

Für später ergänzte Bewegung sind Zweck, Dauer, Kurve und Verhalten bei reduzierter Bewegung gesondert festzulegen. Diese Spezifikation führt keine unbestätigten Motion-Tokens ein.

## Shapes

### Eckenradien

| Rolle | Token / CSS-Variable | Wert | Verwendung |
| --- | --- | --- | --- |
| Kleines Detail | `detail` / `--radius-detail` | 3 px | Checkboxen |
| Gemeinsames Bedienelement | `control` / `--radius-control` | 6 px | Buttons, Aktionslinks, Badges, Logstufen, Eingaben, Auswahllisten, Bilder sowie Auswahl und Hover-Fläche der Navigation |
| Übergeordnete Fläche | `surface` / `--radius-surface` | 10 px | Panels, mobile Karten, Meldungen, Filter, Auswahlkarten und Navigationsleiste |

Buttons, Badges, Release-Links und Bilder verwenden denselben Radius. Der Bildradius wird am Bildelement gesetzt und bleibt auch bei anderen Bildquellen wirksam. Eine zusätzliche eigene Bild- oder Badge-Radiusstufe entfällt. Die Navigationsleiste verwendet den Flächenradius von 10 px. Ihre Auswahl und Hover-Fläche verwenden wie die übrigen Bedienelemente 6 px Radius.

### Linien und Bilder

Reguläre Komponenten- und Flächenkonturen sind 1 px stark. Die Fokusmarkierung ist 2 px stark und hat 3 px Abstand. Der Checkbox-Haken verwendet eine Strichstärke von 2 px. Symbole für die Eintragsart sind 14 × 14 px gross und bestehen aus konsistenten SVG-Strichen.

Portraitbilder behalten das Seitenverhältnis 2:3. Ihre Standardgrösse beträgt 3,5 rem × 5,25 rem, bei normaler Browserbasis 56 × 84 px. `object-fit: cover` füllt den Ausschnitt. Breite und Höhe skalieren gemeinsam mit der Basisschrift. Platzhalter verwenden dieselbe Grösse und denselben Radius. Dekorative Bilder neben einem vollständigen Textlabel erhalten einen leeren Alternativtext. Ein Bild, das selbst Information trägt, benötigt einen passenden Alternativtext.

## Components

### Gemeinsame Regeln

Die folgenden Bausteine beschreiben vorhandene Komponenten. Die Beispiele in der Begleitdatei verwenden den Präfix `ds-`, damit sie in einem anderen Projekt isoliert eingesetzt werden können. Variablen behalten ihre Bedeutung, auch wenn eine Komponentenbibliothek andere Klassennamen verwendet.

Bedienung wird mit nativen HTML-Elementen umgesetzt. Navigation verwendet Links, Aktionen verwenden Buttons und Formulareingaben behalten ihre Labels. Ein visuelles Status-Badge wird nicht als Button ausgegeben. Eine farbige Auswahl erhält zusätzlich einen semantischen Zustand wie `aria-current="page"` oder ein tatsächlich ausgewähltes Formularelement.

### Buttons und Aktionslinks

Buttons sind ruhig umrandet und in der neutralen Palette gehalten. Primäre und sekundäre Aktionen unterscheiden sich im bestehenden System durch Platzierung und Beschriftung. Eine zusätzliche gefüllte Markenfarbe oder eine neue Button-Farbpalette ist nicht definiert.

| Variante | Schrift | Geometrie |
| --- | --- | --- |
| Standard | 14 px / 500 / 1,4 | Mindesthöhe 38 px, Innenabstand 8 px vertikal und 14 px horizontal |
| Kompakt | 14 px / 500 / 1,4 | Mindesthöhe 32 px, Innenabstand 5 px vertikal und 10 px horizontal |
| Aktualisieren eines Laufhinweises | 14 px / 500 / 1,4 | Mindesthöhe 34 px, reguläre Button-Innenabstände |

Alle Varianten verwenden 6 px Radius, 1 px Kontur und die Zustandswerte aus Colors. Links mit Aktionsdarstellung verwenden dieselbe Geometrie. Kompakte Beschriftungen bleiben einzeilig. Mindesthöhen sind Untergrenzen, keine festen Höhen. Wenn Schrift und Innenabstand mehr Platz benötigen, wächst das Element.

Ein deaktiviertes Element reagiert visuell nicht auf Hover oder Druck. Das Quellprojekt zeigt bei deaktivierten Buttons derzeit den Cursor `wait`. Bei anderen Projekten sind gesperrte Bedienung und tatsächlich laufende Verarbeitung fachlich zu unterscheiden. Ein deaktivierter Button allein bestätigt keinen laufenden Vorgang.

### Formulare und Filter

Formulargruppen liegen auf `surface`, mit 1 px Kontur, 10 px Radius und 16 px Innenabstand. Die Felder stehen mit 12 px Abstand zusammen und dürfen umbrechen. Labels verwenden 13 px und gedämpfte Schrift, darunter folgen 6 px Abstand bis zum Feld. Platzhalter ersetzen kein sichtbares Label.

Eingaben und Auswahllisten verwenden 14 px, Gewicht 400, Zeilenhöhe 1,4 und 6 px Radius. Im Logfilter beträgt die Mindesthöhe 39 px, der Innenabstand 8 px vertikal und 10 px horizontal. Suchfelder dürfen den verbleibenden Platz einnehmen. Die Schreibmarke und der Formularakzent verwenden `control-focus`. Platzhalter haben volle Deckkraft in der gedämpften Textfarbe.

Die Filteraktionen stehen auf derselben unteren Linie wie die Felder. Fehler, Hilfstexte und Labels bleiben als Text verfügbar. Für zusätzliche Feldtypen, Validierung während der Eingabe oder komplexe Formulare sind die konkreten Verhaltensregeln im Zielprojekt festzulegen.

### Navigation

Die Navigationsleiste ist eine kompakte Fläche mit 10 px Radius, 1 px Kontur und 5 px Innenabstand. Zwischen den Einträgen liegen 4 px. Jeder Link verwendet 14 px, Gewicht 500, Mindesthöhe 44 px, Innenabstand 9 px vertikal und 17 px horizontal sowie den Bedienelementradius von 6 px.

Die aktive Ansicht erhält eine gefüllte hellgraue Fläche aus `accent` mit dunkler Schrift aus `background` und transparenter Kontur. Beim Überfahren wird ihre Fläche mit `text` etwas heller. Nicht aktive Einträge beginnen transparent. Eine separate dunkle Fläche aus `background` gleitet beim Überfahren zwischen ihnen und passt ihre Breite dem angesteuerten Link an. Die aktive Auswahl bleibt dabei an ihrem Ort und sichtbar. Hover und Auswahl verwenden keine eigene sichtbare Kontur.

Die Hover-Fläche bewegt sich über 220 ms mit `cubic-bezier(.16, 1, .3, 1)` und blendet über 120 ms aus. Schnelle Mauswechsel dürfen die Bewegung unmittelbar umlenken. Beim Eintritt erscheint sie am angesteuerten Link. Beim Verlassen der Navigation und auf der aktiven Seite verschwindet sie. Touch löst keine Hover-Bewegung aus. Bei `prefers-reduced-motion: reduce` erfolgen alle Wechsel ohne Animation. Tastaturfokus bleibt unabhängig von der Hover-Fläche sichtbar.

Die aktive Seite wird zusätzlich über `aria-current="page"` gekennzeichnet. Im Quellprojekt ergänzen URL-Fragmente die Auswahl der Hauptansichten. Das gemeinsame UI-Skript aktualisiert den semantischen Zustand bei Fragmentwechseln und der Browsernavigation. Ohne Skript erhalten aktive und überfahrene Links dieselben Farben über CSS. Diese technische Zuordnung wird beim Übertragen durch das Routing des Zielprojekts ersetzt.

Die Navigation bleibt in schmalen Fenstern eine Zeile. Bis 470 px gelten die unter Layout beschriebenen kleineren Abstände. Die vier Beschriftungen des Quellprojekts wurden bis 320 px geprüft. Eine andere Anzahl oder längere Beschriftungen benötigen eine eigene Platzprüfung.

### Status-Badges und Logstufen

Status-Badges haben 6 px Radius, mindestens 26 px Höhe und 3 px vertikalen sowie 8 px horizontalen Innenabstand. Die Kontur ist 1 px transparent. Die Schrift verwendet 13 px, Gewicht 500 und Zeilenhöhe 1,4. Die Breite folgt dem Inhalt und überschreitet den verfügbaren Raum nicht. Ein Badge wird nicht über die ganze Zellenbreite gestreckt.

Information, Erfolg, Warnung und Fehler verwenden jeweils das passende Text- und Flächenpaar aus Colors. Neutrale Logstufen verwenden die neutrale Hinweisfläche und Sekundärtext. Fehler- und Warnstufen verwenden ihre semantischen Farben. Logstufen verwenden Inter und keine Monospace-Sonderschrift.

Badges innerhalb einer Zeile haben 6 px Abstand. Eine anschliessende Aktion ist 8 px davon entfernt. Mehrere lange Statuswerte dürfen umbrechen beziehungsweise in einem begrenzten Inhaltsbereich scrollbar bleiben. Farbe und Label geben dieselbe Bedeutung wieder.

### Kompakte Quellen- und Release-Links

Ein Quellenlink ist ein wirklicher Link mit 6 px Radius, 1 px Kontur sowie 3 px vertikalem und 9 px horizontalem Innenabstand. Die Schrift verwendet 13 px, Gewicht 500 und Zeilenhöhe 1,4. Die Links stehen mit 6 px Abstand nebeneinander.

Die Standarddarstellung entspricht der neutralen Bedienung. Für besuchte Links gilt die Besuchsmarkierung aus Colors. In einem dreizeiligen Eintrag bleiben die Links einzeilig und werden bei Platzmangel horizontal scrollbar. Einzelne Links schrumpfen nicht zusammen. Ein Tooltip kann den vollständigen Quelltitel ergänzen.

Bei mehreren Quellen derselben Qualität folgt die Quellenkennung mit einem Leerzeichen, beispielsweise `1080p WAYNE`. Ein zusätzlicher Mittelpunkt wird nicht eingefügt. Der Zieltext bleibt ausreichend aussagekräftig, um mehrere Links voneinander zu unterscheiden.

### Dreizeiliger Bildeintrag

Dieser Baustein ist die wiederkehrende Kombination aus Bild, Titel, ergänzendem Code und Aktionen. Im Quellprojekt enthält er Serie, Episodencode und Release-Links. Ein anderes Projekt kann dieselben Rollen beispielsweise für ein Dokument, eine Kennung und dessen Quellen verwenden.

| Teil | Festlegung |
| --- | --- |
| Bild | 3,5 rem breit, 5,25 rem hoch, Radius 6 px, `object-fit: cover` |
| Abstand zwischen Bild und Text | 14 px |
| Textbereich | 5,25 rem hoch, flexibel breit, `min-width: 0` |
| Erste Zeile | Eintragstitel, sichtbare Versalhöhe oben bündig mit dem Bild |
| Zweite Zeile | Ergänzender Code in Inter, 14 px / 400, normale Null, gleich breite Ziffern |
| Dritte Zeile | Aktionslinks beziehungsweise Eintragsart, unten bündig mit dem Bild |
| Zwischenraum | Der freie Platz wird mit `justify-content: space-between` verteilt |

Die obere Ausrichtung berücksichtigt den Innenraum der Schriftzeile. Ein aus Versalhöhe und Zeilenhöhe berechneter Aussenabstand mit `calc((1cap - 1lh) / 2)` richtet die sichtbare Schrift an der Bildkante aus. Der Aktionsbereich endet am unteren Bildrand. Es werden keine festen Pixelkorrekturen pro Wort verwendet. In mobilen Eintragskarten beginnen auch die Werte für Bestand, Status und Datum an der Textkante neben dem Bild. Bildbreite und Bildabstand bestimmen dafür dieselben beiden Spalten wie im Bildeintrag.

Ein Titel bleibt einzeilig. Bei Platzmangel erscheint ein Auslassungszeichen. Der vollständige Titel steht als Tooltip bereit und bleibt als vollständiger Text im Dokument. Der Titelbereich oder sein Link ist per Tastatur erreichbar und lässt sich bei Fokus horizontal scrollen. Der Tooltip ist damit eine Ergänzung zur zugänglichen Darstellung. Auf Geräten ohne Hover muss der volle Titel weiterhin über den fokussierbaren Text oder das zugehörige Linkziel erreichbar bleiben.

```html
<article class="ds-item">
  <img class="ds-item-image" src="/images/example.webp"
       width="56" height="84" alt="">
  <div class="ds-item-content">
    <span class="ds-item-title" title="Beispieltitel" tabindex="0">Beispieltitel</span>
    <span class="ds-item-code">S03E07</span>
    <div class="ds-item-links">
      <a class="ds-source-link" href="/sources/example">1080p</a>
    </div>
  </div>
</article>
```

```css
.ds-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
  height: 5.25rem;
}
.ds-item-image {
  flex: 0 0 3.5rem;
  width: 3.5rem;
  height: 5.25rem;
  border-radius: var(--radius-control);
  object-fit: cover;
}
.ds-item-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  height: 5.25rem;
}
.ds-item-title {
  flex: 0 0 auto;
  margin-block-start: calc((1cap - 1lh) / 2);
  max-width: 100%;
  overflow: hidden;
  font-size: var(--type-body);
  font-weight: var(--weight-medium);
  line-height: var(--leading-compact);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ds-item-title:focus-within {
  overflow-x: auto;
  text-overflow: clip;
  scrollbar-width: none;
}
.ds-item-code {
  color: var(--text-secondary);
  font-size: var(--type-label);
  font-weight: var(--weight-regular);
  line-height: var(--leading-compact);
  font-variant-numeric: lining-nums tabular-nums;
  white-space: nowrap;
}
.ds-item-links {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
}
.ds-source-link {
  flex: 0 0 auto;
  padding: 3px 9px;
  border: 1px solid var(--control-border);
  border-radius: var(--radius-control);
  background: var(--control);
  color: var(--control-text);
  font-size: var(--type-caption);
  font-weight: var(--weight-medium);
  line-height: var(--leading-compact);
  text-decoration: none;
}
.ds-source-link:hover {
  border-color: var(--control-border-hover);
  background: var(--control-hover);
  color: var(--control-text-hover);
}
.ds-source-link:active {
  border-color: var(--control-border-pressed);
  background: var(--control-pressed);
  color: var(--control-text-hover);
}
.ds-source-link:visited {
  border-color: var(--control-visited);
  background: var(--control-visited);
  color: var(--control-on-visited);
}
.ds-source-link:visited:hover {
  border-color: var(--control-visited-hover);
  background: var(--control-visited-hover);
}
.ds-source-link:visited:active {
  border-color: var(--control-border-pressed);
  background: var(--control-visited);
}
.ds-source-link:focus-visible { border-color: var(--control-focus); }
```

Das Beispiel setzt die gemeinsame CSS-Basis und die Inter-Einbindung voraus. Der Beispielbildpfad und das Linkziel werden im Zielprojekt durch tatsächliche Ressourcen ersetzt. Ein Platzhalter verwendet dieselben Masse. Für Status statt Aktionen kann in der dritten Zeile ein vorhandenes Badge eingesetzt werden.

### Tabellen und mobile Eintragskarten

Desktop-Tabellen verwenden feste Spaltenanteile und verbinden die Zeilen durch feine Konturen. Die Oberfläche verwendet keine wechselnden Zebraflächen. Eine Zeile wird beim Überfahren auf `surface-hover` gesetzt. Zellen richten sich oben und links aus. Der Innenabstand beträgt 18 px vertikal und 20 px horizontal.

| Tabelle im Quellprojekt | Titel / Quelle | Bestand / Ziel | Status | Datum / Details |
| --- | --- | --- | --- | --- |
| Aktuelle Einträge | 46 % | 20 % | 14 % | 20 % |
| Historie | 46 % | 24 % | 14 % | 16 % |

Die Prozentanteile sind Anwendungsdetails und keine Pflicht für andere Datenmodelle. Kopfzellen verwenden grundsätzlich 14 px und mittleres Gewicht. Eine bestehende CSS-Ausnahme ist die Datumsüberschrift mit 14 px, Gewicht 400 und Zeilenhöhe 1,6. Für neue Tabellen ist die gemeinsame Kopfrolle mit 500 und 1,4 der Ausgangspunkt.

Ein Datenbereich ist am Desktop 5,25 rem hoch. Gleich hohe Zeilen halten die Tabelle ruhig. Längere Inhalte bleiben innerhalb der vorhandenen Scrollbereiche erreichbar. Importziele werden auf höchstens zwei Zeilen gekürzt und zeigen letzten Ordner und Dateinamen. Der vollständige Zielpfad bleibt als Tooltip erhalten. Daten selbst werden durch die Kürzung nicht verändert.

Bis 760 px wird jede Tabellenzeile zu einer eigenen Karte mit 10 px Radius und 10 px Innenabstand für die Eintragsliste. Einzelne Werte stehen neben ihrem sichtbaren Feldlabel. Das Label verwendet 13 px und Gewicht 500 in normaler Gross- und Kleinschreibung. Die Labelspalte ist 105 px breit, bis 470 px 88 px. Dazwischen liegen 10 px. Tabellenüberschriften bleiben für assistive Technik verfügbar.

Die mobilen Bestandsbereiche haben im Quellprojekt 4,75 rem Höhe, Statusbereiche 2,125 rem und Datumsbereiche 1,75 rem. Diese Masse sind auf die gezeigten Daten abgestimmt. Ein anderes Datenmodell übernimmt sie nur nach einer Prüfung mit seinen tatsächlichen Inhalten.

### Panels, Auswahlkarten und leere Ansichten

Panels verwenden `surface`, 1 px Kontur und 10 px Radius. Ein einfacher Inhaltsbereich kann 16 px Innenabstand erhalten. Auswahlkarten verwenden 24 px Innenabstand und 20 px vertikalen Aussenabstand. Ihre Überschrift verwendet die Abschnittsrolle, erläuternder Text die reguläre Inhaltsrolle mit sekundärer Farbe.

Eine leere Ansicht zeigt eine kurze Erklärung und bei Bedarf den nächsten sinnvollen Schritt. Im Tabellenbereich sind dafür 48 px vertikaler und 20 px horizontaler Innenabstand vorgesehen. Der Titel verwendet 16 px und Gewicht 500, der Zusatztext 14 px in gedämpfter Farbe. Das Diagnoselog verwendet 38 px vertikal und 16 px horizontal. Diese Varianten gehören zu ihrer jeweiligen Fläche und sind keine zusätzlichen Schriftrollen.

### Hinweise, Warnungen und Fehler

Meldungen verwenden 10 px Radius, eine 1 px starke semantische Kontur und die zum Zustand gehörende Fläche. In breiten Arbeitsansichten beträgt der Innenabstand 18 px vertikal und 20 px horizontal. Die Fehlerbegründung auf einer eigenen Fehlerseite verwendet 16 px.

Der Meldungstitel hat Gewicht 500 und steht mit 4 px Abstand vor dem Inhalt. Ein neutraler Laufhinweis verwendet Primärtext auf der neutralen Hinweisfläche. Warnungen und Fehler verwenden ihre semantische Schriftfarbe. Eine Fehlerseite behält die Navigation und einen verständlichen Rückweg. Die Darstellung behauptet keinen Erfolg und führt keine versteckte Wiederholung einer Aktion aus.

Für Statusmeldungen wird ein geeigneter Statusbereich, für unmittelbar relevante Fehler ein geeigneter Alarmbereich verwendet. Eine neue Meldung verschiebt nicht unnötig den Tastaturfokus. Die konkrete Ankündigung durch assistive Technik wird mit dem tatsächlichen Ablauf geprüft.

### Aufklappbare Bereiche und Checkboxfilter

Aufklappbare Beschriftungen verwenden 14 px, Gewicht 500, mindestens 28 px Höhe, 3 px vertikalen und 5 px horizontalen Innenabstand sowie 6 px Radius. Sie beginnen transparent und erhalten im geöffneten Zustand die ausgewählte Bedienfläche. Der native Öffnungsmarker bleibt erhalten.

Die Checkboxfilter der Historie verwenden 17 × 17 px grosse Checkboxen innerhalb regulärer Buttonlabels. Zwischen Checkbox und Beschriftung liegen 8 px, zwischen zwei Filterlabels 12 px. Checkboxen behalten ihren eigenen Radius von 3 px. Der gezeichnete Haken ist 9 × 5 px gross und hat 2 px Strichstärke. Der ausgewählte Zustand wird durch das tatsächliche Formularelement getragen.

Im erzwungenen Kontrastmodus übernimmt der Browser die Checkboxdarstellung. Das selbst gezeichnete Häkchen entfällt dort. Die Filtergruppe behält eine zugängliche Gruppenbeschriftung.

### Strukturierte Logeinträge

Logeinträge folgen denselben Schrift- und Flächenrollen wie andere Daten. Zeit und Nachricht verwenden beide 16 px, Gewicht 400 und Primärtext. Die Quelle steht mit 6 px Abstand unter der Nachricht in der Metadatenrolle. Die Logstufe ist ein Status-Badge.

Am Desktop werden Zeit, Logstufe und Nachricht in drei Spalten angeordnet: `15rem 5.125rem minmax(0, 1fr)`. Zwischen den Spalten liegen 12 px, innerhalb der Zeile 18 px vertikaler und 20 px horizontaler Innenabstand. Bis 800 px stehen Zeit und Logstufe oben, die Nachricht darunter über die gesamte Breite. Die kleinere Anordnung verwendet 5 px vertikalen und 10 px horizontalen Abstand.

Meldungen bewahren vorhandene Zeilenumbrüche mit `white-space: pre-wrap` und brechen lange Zeichenfolgen um. Die strukturierte Ansicht wird nicht allein wegen ihres technischen Inhalts in Monospace gesetzt. Eine tatsächliche Rohtext- oder Codeansicht kann die technische Schriftrolle verwenden.

### Symbole und Produktressourcen

Symbole werden als konsistente SVG-Geometrie eingebunden. Sie ersetzen keine vollständige Statusbeschriftung und keine wesentliche Handlungsanweisung. Die vorhandenen Symbole für Feed und Import sind 14 px gross und verwenden `currentColor`. Reine Dekoration ist für assistive Technik ausgeblendet.

Das Favicon und der Serienplatzhalter des Quellprojekts sind Produktressourcen. Beim Übertragen wird ein neues Produktsymbol festgelegt. Ihre Buchstabenform oder ihr Serienmotiv werden nicht automatisch zur Markenidentität des Zielprojekts. Die Platzhalterfläche und die Bildgeometrie können übernommen werden.

## Do's and Don'ts

### Verbindliche Gestaltungsregeln

| Anwenden | Vermeiden |
| --- | --- |
| Neue Elemente einer vorhandenen Textrolle zuordnen | Zusätzliche lokale Schriftgrössen und Gewichte einführen |
| Bestand, Datum und Uhrzeit gleichwertig mit 16 px darstellen | Wesentliche Daten als kleine Metadaten behandeln |
| Buttons, Badges, Quellenlinks und Bilder mit 6 px abrunden | Für ähnliche kleine Elemente eigene Radiusstufen verwenden |
| Zustände mit Text und semantischer Farbe kennzeichnen | Fachliche Bedeutung allein durch Farbe oder einen Punkt vermitteln |
| Angaben durch Abstand und Position trennen | Mittelpunkte als dekorative Trenner einsetzen |
| Inter lokal ausliefern und die Lizenz mitführen | Eine neue externe Font-Abhängigkeit einführen |
| Lange Titel vollständig zugänglich halten | Den Datenwert beim visuellen Kürzen verändern oder entfernen |
| Schriftvergrösserung durch relative Masse unterstützen | Schrift in schmalen Fenstern verkleinern, um Platz zu erzwingen |
| Native HTML-Bedienung und erkennbare Fokuszustände verwenden | Interaktive `div`-Elemente ohne gleichwertige Semantik einsetzen |
| Flächen durch Ton und Kontur abgrenzen | Zusätzliche Schatten, Verläufe oder Leuchteffekte als Standard hinzufügen |

### Zugänglichkeit und robuste Zustände

Text muss gegen seine tatsächliche Fläche ausreichend kontrastieren. Für normalen Text gilt ein Ziel von mindestens 4,5 zu 1. Die Freigabe eines Textfarbwerts gilt nicht automatisch für jede andere Fläche. Gedämpfte Schrift wird deshalb nicht beliebig auf helle ausgewählte Bedienflächen gelegt. Hover, Auswahl und Fokus verwenden die jeweils definierten Zustandsfarben.

Die Fokusmarkierung bleibt sichtbar und wird nicht global entfernt. Scrollbare Textbereiche sind mit der Tastatur erreichbar. Versteckte Seitenüberschriften bleiben semantisch vorhanden. Die primäre Navigation benennt ihre Aufgabe und den aktuellen Eintrag. Dekorative Bilder erhalten keinen redundanten vorgelesenen Titel.

Die dokumentierten Kompaktgrössen sind auf die bestätigte Desktop-Bedienung abgestimmt. Ein Zielprojekt mit überwiegender Touch-Bedienung legt seine benötigten Trefferflächen ausdrücklich fest. Visuell kompakte Badges werden dadurch nicht automatisch zu kleinen Touch-Buttons.

### Prüfkriterien vor der Übernahme

| Prüfung | Erwartetes Ergebnis |
| --- | --- |
| Fontladung | Inter wird lokal geladen, die Ersatzschrift bleibt während des Ladens lesbar |
| Schriftrollen | Reguläre sichtbare Texte verwenden nur 13, 14, 16 oder 20 px bei normaler Browserbasis |
| Gewichte | Reguläre Oberfläche verwendet 400, 500 oder 600 |
| Datenvergleich | Bestand, Datum und Uhrzeit haben dieselbe Grösse, Gewichtung, Zeilenhöhe und Farbe |
| Dreizeiliger Eintrag | Titelbox beginnt am oberen Bildrand, Aktionsbereich endet am unteren Bildrand |
| Radien | Buttons, Badges, Quellenlinks und Bilder haben denselben Radius |
| Lange Inhalte | Vollständige Werte bleiben über Text, Fokus, Scrollbereich oder ergänzendes Ziel zugänglich |
| Tastatur | Reihenfolge, Fokusmarkierung und alle Aktionen sind bedienbar |
| Schmale Fenster | Kein unbeabsichtigter horizontaler Überlauf der ganzen Seite |
| Textvergrösserung | Bei 200 Prozent wachsen Schrift, Bild und Textbereiche sinnvoll mit |
| Status und Fehler | Labels passen zu Farben und tatsächlich erreichtem Zustand |
| Fehlende Inhalte | Leere Ansichten, fehlende Bilder und fehlende Fonts bleiben verständlich |

Die bisherige Browserprüfung des Quellprojekts umfasste 1920, 1280, 760, 390 und 320 px sowie 200 Prozent Textgrösse am Desktop. Diese Angaben beschreiben die bisherigen Prüffälle und sind keine pauschale Zugänglichkeitszertifizierung für ein neues Produkt. Andere Beschriftungen, Datenmengen und Bedienabläufe werden erneut geprüft.

### Grenzen des bestehenden Systems

Eine helle Variante, zusätzliche Markenpaletten, Diagrammfarben, Dialoge, Toasts, komplexe Dropdowns und mehrstufige Seitennavigation sind nicht als fertige Varianten definiert. Sie werden bei Bedarf aus den vorhandenen Rollen entwickelt und vor ihrer Verwendung dokumentiert.

Bei einer Erweiterung werden zuerst Zweck und Informationsrolle beschrieben. Danach werden vorhandene Tokens und Komponenten geprüft. Ein zusätzlicher Wert wird erst eingeführt, wenn eine bestehende Rolle den Zweck nicht erfüllt. Werte und Beschreibungen in dieser Datei, die CSS-Umsetzung und gegebenenfalls die Werkzeug-Begleitdatei werden gemeinsam aktualisiert.
