#!/usr/bin/env python3
"""
KCC Notification Checker
Runs every 30 minutes via GitHub Actions.
Reads kcc-data.json, finds posts coming up in the next 30-65 minutes,
and sends a ntfy notification for each one.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_FILE    = 'kcc-data.json'
NTFY_CHANNEL = os.environ.get('NTFY_CHANNEL', '').strip()
NTFY_BASE    = 'https://ntfy.sh'

# Window: notify if post is between 25 and 65 minutes away
# This gives a comfortable window so no post is missed between runs
NOTIFY_MIN = 25
NOTIFY_MAX = 65

PLAT_LABELS = { 'tt': 'TikTok', 'ig': 'Instagram', 'yt': 'YouTube' }
PLAT_TAGS   = { 'tt': 'musical_note', 'ig': 'camera', 'yt': 'movie_camera' }

# ── HELPERS ───────────────────────────────────────────────────────────────
def fmt_time(time_str):
    """Convert 24hr HH:MM to 12hr h:MM AM/PM"""
    h, m = map(int, time_str.split(':'))
    ap = 'AM' if h < 12 else 'PM'
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ap}"

def send_ntfy(channel, title, body, tags='bell', priority='high'):
    """Send a notification via ntfy.sh"""
    url = f"{NTFY_BASE}/{channel}"
    data = body.encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Title', title)
    req.add_header('Tags', tags)
    req.add_header('Priority', priority)
    req.add_header('Content-Type', 'text/plain')
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except urllib.error.URLError as e:
        print(f"  ntfy error: {e}")
        return False

# ── MAIN ──────────────────────────────────────────────────────────────────
def main():
    if not NTFY_CHANNEL:
        print("No NTFY_CHANNEL set — skipping notifications.")
        return

    if not os.path.exists(DATA_FILE):
        print(f"{DATA_FILE} not found — nothing to check.")
        return

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    posts = data.get('posts', [])
    now   = datetime.now(timezone.utc)

    print(f"Checking {len(posts)} posts at {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Notify window: {NOTIFY_MIN}–{NOTIFY_MAX} minutes before post time")
    print(f"ntfy channel: {NTFY_CHANNEL}")
    print()

    notified = 0

    for post in posts:
        # Skip already posted
        if post.get('posted'):
            continue

        date_str = post.get('date', '')
        time_str = post.get('time', '')
        platform = post.get('platform', '')
        clip_name = post.get('clipName', 'Unknown clip')

        if not date_str or not time_str:
            continue

        # Parse post datetime — treat as local time stored without timezone
        # GitHub Actions runs in UTC, so we compare against UTC
        try:
            post_dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            # Assume the user's times are in UTC for comparison
            # (GitHub Actions runs in UTC)
            post_dt = post_dt_naive.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        minutes_until = (post_dt - now).total_seconds() / 60

        print(f"  [{platform.upper()}] {clip_name} — {date_str} {time_str} — {minutes_until:.0f} min away")

        if NOTIFY_MIN <= minutes_until <= NOTIFY_MAX:
            plat_label = PLAT_LABELS.get(platform, platform.upper())
            plat_tag   = PLAT_TAGS.get(platform, 'bell')
            time_fmt   = fmt_time(time_str)

            title = f"Post to {plat_label} in ~30 min"
            body  = f'"{clip_name}"\n{plat_label} · {time_fmt} slot\n\nTime to get it ready!'

            print(f"  → Sending notification: {title}")
            ok = send_ntfy(NTFY_CHANNEL, title, body, tags=plat_tag, priority='high')
            print(f"  → {'✓ Sent' if ok else '✗ Failed'}")
            notified += 1

    print()
    print(f"Done. {notified} notification(s) sent.")

if __name__ == '__main__':
    main()
