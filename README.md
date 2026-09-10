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
      RSS_URLS: ${RSS_URLS:?RSS_URLS muss gesetzt sein}
      CHECK_INTERVAL_HOURS: ${CHECK_INTERVAL_HOURS:-1}
      MAX_HISTORY: ${MAX_HISTORY:-300}
      TZ: ${TZ:-Europe/Zurich}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      PUID: ${PUID:-1000}
      PGID: ${PGID:-1000}
    volumes:
      - ./data:/data
      - ./out:/out
```

## `.env`

```dotenv
JELLYFIN_URL=http://192.168.0.2:8096
JELLYFIN_API_KEY=dein-api-key
RSS_URLS=https://example.org/serien/feed
CHECK_INTERVAL_HOURS=1
MAX_HISTORY=300
TZ=Europe/Zurich
LOG_LEVEL=INFO
PUID=1000
PGID=1000
```
