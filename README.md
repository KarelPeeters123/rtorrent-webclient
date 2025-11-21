# rtorrent-webclient API

A production-ready Flask REST API for managing Transmission torrents with support for TV/film categorization and automatic magnet link addition.

## Features

- **POST /add** — Add a magnet link to Transmission (auto-categorized to TV or Film)
- **GET /list** — List all torrents with status, progress, and ETA
- **GET /ping** — Health check endpoint
- **Dockerized** — Includes Transmission RPC server and Flask API
- **Environment-driven** — Configure via env vars (TRANSMISSION_HOST, TRANSMISSION_PORT, etc.)

## Quick Start (Docker)

### Build
```bash
docker build -t rtorrent-api .
```

### Run
```bash
docker run -d \
  --name rtorrent-api \
  -p 5000:5000 \
  -p 9091:9091 \
  -v transmission-data:/var/lib/transmission-daemon \
  rtorrent-api
```

### Test
```bash
curl http://localhost:5000/ping
```

## API Endpoints

### POST /add — Add a torrent

Request:
```json
{
  "magnet": "magnet:?xt=urn:btih:0624b3a5...",
  "media_type": "tv"  // or "film"
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "method": "rpc",
    "result": "Torrent(id=1, ...)"
  }
}
```

Example:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"magnet":"magnet:?xt=urn:btih:...", "media_type":"tv"}' \
  http://localhost:5000/add
```

### GET /list — List torrents

Response:
```json
{
  "ok": true,
  "result": {
    "torrents": [
      {
        "id": "1*",
        "done": "100%",
        "have": "1.05 GB",
        "eta": "Done",
        "up": "0.0",
        "down": "0.0",
        "ratio": "0.00",
        "status": "Idle",
        "name": "Example Show S01E01"
      }
    ]
  }
}
```

Example:
```bash
curl http://localhost:5000/list | jq
```

### GET /ping — Health check

Response:
```json
{
  "ok": true,
  "msg": "rtorrent-webclient API running"
}
```

## Local Development

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run with Flask dev server (not for production)
```bash
python3 api.py
```

### Run with gunicorn (production-like)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

## Configuration

### Environment Variables

- `TRANSMISSION_HOST` (default: `127.0.0.1`)
- `TRANSMISSION_PORT` (default: `9091`)
- `TRANSMISSION_USER` (optional)
- `TRANSMISSION_PASS` (optional)
- `TRANSMISSION_DOWNLOAD_DIR` (default: `/var/lib/transmission-daemon/downloads`)
- `ENABLE_CORS` (default: `false`) — set to `true` to enable CORS headers

Example:
```bash
docker run -e ENABLE_CORS=true -e TRANSMISSION_HOST=remote.server.com ...
```

### Transmission Settings

The Docker container uses `transmission-settings.json` (a Transmission configuration file) which is copied into the container at build time. Key settings include:

- **RPC enabled**: port 9091, no authentication required (configure in production)
- **Download directory**: `/var/lib/transmission-daemon/downloads`
- **Subdirectories**: `tv/` and `film/` (auto-created by Dockerfile)
- **Default peer limit**: 60 per torrent, 240 global
- **DHT/PEX enabled**: for better peer discovery

#### Customizing Transmission Settings

To modify settings:

1. Edit `transmission-settings.json` in the repo
2. Rebuild the image: `docker build -t rtorrent-api .`
3. Run the container

Alternatively, mount a custom settings file at runtime:
```bash
docker run -v /path/to/custom-settings.json:/var/lib/transmission-daemon/settings.json ...
```

For a full list of Transmission settings, see the [Transmission Wiki](https://github.com/transmission/transmission/wiki/Editing-Configuration-Files).

## Directory Structure

```
rtorrent-webclient/
├── api.py                       # Flask application
├── rtorrent.py                  # Transmission helper (RPC + CLI fallback)
├── entrypoint.sh                # Container startup script (starts transmission-daemon + Flask API)
├── Dockerfile                   # Container image definition
├── transmission-settings.json   # Transmission daemon configuration
├── requirements.txt             # Python dependencies
├── .dockerignore                # Docker build exclusions
└── README.md                    # This file
```

## Production Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3'
services:
  rtorrent-api:
    build: .
    ports:
      - "5000:5000"
      - "9091:9091"
    volumes:
      - transmission-data:/var/lib/transmission-daemon
      - downloads:/var/lib/transmission-daemon/downloads
    environment:
      - ENABLE_CORS=false
    restart: always

volumes:
  transmission-data:
  downloads:
```

Run:
```bash
docker-compose up -d
```

### Systemd Service

Create `/etc/systemd/system/rtorrent-api.service`:

```ini
[Unit]
Description=rtorrent-webclient API
After=network.target transmission-daemon.service

[Service]
Type=simple
ExecStart=/usr/bin/gunicorn -w 4 -b 127.0.0.1:5000 api:app
WorkingDirectory=/opt/rtorrent-webclient
Restart=always
RestartSec=10
User=transmission

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rtorrent-api
sudo systemctl start rtorrent-api
```

### Reverse Proxy (Nginx)

```nginx
upstream rtorrent_api {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://rtorrent_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

## Troubleshooting

### 502 Bad Gateway (RPC unreachable)

Check Transmission is running:
```bash
curl http://localhost:9091/transmission/rpc/
# Should return 409 Conflict (expected without X-Transmission-Session-Id header)
```

### Import errors in Docker

Ensure the Dockerfile copies `rtorrent.py` alongside `api.py`. Check:
```bash
docker exec rtorrent-api ls -la /app/
```

### Permission denied on downloads

Fix ownership:
```bash
docker exec rtorrent-api chown -R debian-transmission:debian-transmission /var/lib/transmission-daemon/downloads
```

## License

MIT
