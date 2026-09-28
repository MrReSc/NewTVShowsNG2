# NewTVShowsNG2

## `compose.yaml`

```yaml
services:
  newtvshowsng2:
    image: ghcr.io/mrresc/newtvshowsng2:latest
    platform: linux/amd64
    pull_policy: always
    container_name: NewTVShowsNG2
    restart: unless-stopped
    ports:
      - "28800:8080"
    environment:
      JELLYFIN_URL: ${JELLYFIN_URL:?JELLYFIN_URL muss gesetzt sein}
      JELLYFIN_API_KEY: ${JELLYFIN_API_KEY:?JELLYFIN_API_KEY muss gesetzt sein}
      JELLYFIN_USERNAME: ${JELLYFIN_USERNAME:?JELLYFIN_USERNAME muss gesetzt sein}
      RSS_URLS: ${RSS_URLS:?RSS_URLS muss gesetzt sein}
      CHECK_INTERVAL_HOURS: ${CHECK_INTERVAL_HOURS:-1}
      MAX_HISTORY: ${MAX_HISTORY:-300}
      TZ: ${TZ:-Europe/Zurich}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      MEDIA_IMPORT_ENABLED: ${MEDIA_IMPORT_ENABLED:-true}
      INCOME_DIR: /income
      SHOWS_DIR: /shows
      JELLYFIN_SHOWS_PATH: ${JELLYFIN_SHOWS_PATH:-/data/tvshows}
      IMPORT_STABLE_HOURS: ${IMPORT_STABLE_HOURS:-1}
      PUID: ${PUID:-1000}
      PGID: ${PGID:-1000}
    volumes:
      - ./data:/data
      - ./out:/out
      - type: bind
        source: ${INCOME_HOST_PATH:?INCOME_HOST_PATH muss gesetzt sein}
        target: /income
        bind:
          create_host_path: false
      - type: bind
        source: ${SHOWS_HOST_PATH:?SHOWS_HOST_PATH muss gesetzt sein}
        target: /shows
        bind:
          create_host_path: false
```

## `.env`

```dotenv
JELLYFIN_URL=http://192.168.0.2:8096
JELLYFIN_API_KEY=dein-api-key
JELLYFIN_USERNAME=Hans
RSS_URLS=https://example.org/serien/feed
CHECK_INTERVAL_HOURS=1
MAX_HISTORY=300
TZ=Europe/Zurich
LOG_LEVEL=INFO
MEDIA_IMPORT_ENABLED=true
INCOME_HOST_PATH=/volume1/Media/Serien/Income
SHOWS_HOST_PATH=/volume1/Media/Serien/Watched
JELLYFIN_SHOWS_PATH=/data/tvshows
IMPORT_STABLE_HOURS=1
PUID=1000
PGID=1000
```

`JELLYFIN_SHOWS_PATH` ist der Pfad desselben `Watched`-Ordners aus Sicht des
Jellyfin-Containers. Die Anwendung vergleicht ihn vor jedem Import mit den von
Jellyfin gemeldeten TV-Bibliothekspfaden. Dateien werden erst übernommen, wenn
sie eine Stunde unverändert in `Income` lagen. Nicht eindeutige Zuordnungen und
bereits vorhandene Episoden bleiben in `Income` und werden in der Weboberfläche
angezeigt.
