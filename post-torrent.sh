#!/bin/bash

LOGFILE="/var/log/transmission-move.log"

{
    echo "=== $(date): Move script started ==="

    shopt -s nullglob

    echo "Moving TV files..."
    rsync -av --remove-source-files /var/lib/transmission-daemon/downloads/tv/ /mnt/external/TV\ Shows/

    echo "Moving Film files..."
    rsync -av --remove-source-files /var/lib/transmission-daemon/downloads/film/ /mnt/external/Movies/

    echo "Cleaning up empty directories..."
    find /var/lib/transmission-daemon/downloads/tv/ -type d -empty -delete
    find /var/lib/transmission-daemon/downloads/film/ -type d -empty -delete

    echo "=== $(date): Move script finished ==="
    echo ""
} >> "$LOGFILE" 2>&1

