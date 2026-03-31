#!/usr/bin/env python3
"""
KCC Notification Checker
Runs every 30 minutes via GitHub Actions.
Reads kcc-data.json, finds posts coming up in the next 30-65 minutes,
and sends a ntfy notification for each one.

TIMEZONE: Set the TIMEZONE secret in your GitHub repo to your local timezone.
Examples: America/Chicago, America/New_York, America/Los_Angeles, America/Denver
Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
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
USER_TZ_NAME = os.environ.get('TIMEZONE', 'America/Chicago').strip()

NOTIFY_MIN = 25
NOTIFY_MAX = 65

PLAT_LABELS = { 'tt': 'TikTok', 'ig': 'Instagram', 'yt': 'YouTube' }
PLAT_TAGS   = { 'tt': 'musical_note', 'ig': 'camera', 'yt': 'movie_camera' }


# ── TIMEZONE ─────────────────────────────────────────────────────────────
def get_utc_offset(tz_name):
    try:
        from zoneinfo import ZoneInfo
        local_now = datetime.now(ZoneInfo(tz_name))
        offset = local_now.utcoffset()
        hours = int(offset.total_seconds() // 3600)
        print(f"  Timezone: {tz_name} (UTC{hours:+d})")
        return offset
    except Exception as e:
        print(f"  Warning: Could not load timezone '{tz_name}': {e}")
        print(f"  Falling back to auto-detecting US Central time")
        now_utc = datetime.now(timezone.utc)
        year = now_utc.year
        march_1 = datetime(year, 3, 1)
        days_to_sun = (6 - march_1.weekday()) % 7
        dst_start = datetime(year, 3, 1 + days_to_sun + 7, 2, tzinfo=timezone.utc)
        nov_1 = datetime(year, 11, 1)
        days_to_sun = (6 - nov_1.weekday()) % 7
        dst_end = datetime(year, 11, 1 + days_to_sun, 2, tzinfo=timezone.utc)
        if dst_start <= now_utc < dst_end:
            print(f"  Detected CDT (UTC-5)")
            return timedelta(hours=-5)
        else:
            print(f"  Detected CST (UTC-6)")
            return timedelta(hours=-6)


# ── HELPERS ───────────────────────────────────────────────────────────────
def fmt_time(time_str):
    h, m = map(int, time_str.split(':'))
    ap = 'AM' if h < 12 else 'PM'
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ap}"


def send_ntfy(channel, title, body, tags='bell', priority='high'):
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

    utc_offset = get_utc_offset(USER_TZ_NAME)
    user_tz    = timezone(utc_offset)
    now_utc    = datetime.now(timezone.utc)
    now_local  = datetime.now(user_tz)

    print(f"  UTC time:   {now_utc.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Local time: {now_local.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Window:     {NOTIFY_MIN}–{NOTIFY_MAX} min before post")
    print()

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    posts    = data.get('posts', [])
    notified = 0

    print(f"Checking {len(posts)} posts...")
    print()

    for post in posts:
        if post.get('posted'):
            continue

        date_str  = post.get('date', '')
        time_str  = post.get('time', '')
        platform  = post.get('platform', '')
        clip_name = post.get('clipName', 'Unknown clip')

        if not date_str or not time_str:
            continue

        try:
            # Parse as LOCAL time, convert to UTC for comparison
            post_dt_local = datetime.strptime(
                f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=user_tz)
            post_dt_utc = post_dt_local.astimezone(timezone.utc)
        except ValueError:
            continue

        minutes_until = (post_dt_utc - now_utc).total_seconds() / 60

        print(f"  [{platform.upper()}] {clip_name} — {fmt_time(time_str)} local — {minutes_until:.0f} min away")

        if NOTIFY_MIN <= minutes_until <= NOTIFY_MAX:
            plat_label = PLAT_LABELS.get(platform, platform.upper())
            plat_tag   = PLAT_TAGS.get(platform, 'bell')

            title = f"Post to {plat_label} in ~30 min"
            body  = f'"{clip_name}"\n{plat_label} · {fmt_time(time_str)}\n\nTime to get it ready!'

            print(f"         → Sending: {title}")
            ok = send_ntfy(NTFY_CHANNEL, title, body, tags=plat_tag, priority='high')
            print(f"         → {'✓ Sent' if ok else '✗ Failed'}")
            notified += 1

    print()
    print(f"Done. {notified} notification(s) sent.")


if __name__ == '__main__':
    main()
