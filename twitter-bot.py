import feedparser
import requests
import os

# List of Nitter instances to try in order
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
    "https://nitter.catsarch.com",
    "https://nitter.pek.li",
    "https://nitter.aishiteiru.moe",
    "https://nitter.aosus.link",
    "https://nitter.10qt.net",
    "https://nitter.anoxinon.de",
    "https://nitter.alt.biovictor.com",
    "https://nitter.batsense.net",
    "https://nitter.bird.froth.zone",
]

# Track instance health (fail counts)
INSTANCE_FAILS = {instance: 0 for instance in NITTER_INSTANCES}
FAIL_THRESHOLD = 3  # remove instance after 3 failures

# List of usernames to monitor
USERNAMES = [
    "visegrad24",
    "MarioNawfal",
    "illuminatibot",
    "redpillb0t",
]

# Your Make.com webhook URL
WEBHOOK_URL = "https://hook.eu1.make.com/ze6g6ouqsvjigxeocgega4ufrh7km9hl"

# File to track already processed tweets
SEEN_FILE = "seen_tweets.txt"


def load_seen():
    """Load already processed tweet links from file."""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()


def save_seen(seen):
    """Save updated set of seen tweet links."""
    with open(SEEN_FILE, "w") as f:
        for link in seen:
            f.write(link + "\n")


def fetch_feed(username):
    """Try multiple Nitter instances until one returns entries, with HTTP logging and fail tracking."""
    global NITTER_INSTANCES

    for instance in list(NITTER_INSTANCES):  # copy to avoid modifying while iterating
        url = f"{instance}/{username}/rss"
        try:
            response = requests.get(url, timeout=10)
            print(f"🔎 Checking {url} → Status {response.status_code}")

            if response.status_code != 200:
                print(f"❌ {instance} returned {response.status_code} for @{username}")
                INSTANCE_FAILS[instance] += 1
                if INSTANCE_FAILS[instance] >= FAIL_THRESHOLD:
                    print(f"🚫 Removing {instance} from list (too many failures)")
                    NITTER_INSTANCES.remove(instance)
                continue

            feed = feedparser.parse(response.text)
            if feed.entries:
                print(f"✅ Found {len(feed.entries)} tweets for @{username} using {instance}")
                return feed.entries
            else:
                print(f"⚠️ No tweets found for @{username} on {instance}")
        except Exception as e:
            print(f"❌ Error fetching @{username} from {instance}: {e}")
            INSTANCE_FAILS[instance] += 1
            if INSTANCE_FAILS[instance] >= FAIL_THRESHOLD:
                print(f"🚫 Removing {instance} from list (too many failures)")
                NITTER_INSTANCES.remove(instance)
    return []


def send_to_webhook(username, entry):
    """Send tweet data to Make.com webhook."""
    data = {
        "username": username,
        "title": entry.title,
        "link": entry.link,
        "published": entry.published,
    }
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        print(f"Sent tweet from @{username}, status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending webhook for @{username}: {e}")


def main():
    seen = load_seen()
    updated_seen = set(seen)

    for username in USERNAMES:
        print(f"Fetching feed for @{username}...")
        entries = fetch_feed(username)
        for entry in entries:
            if entry.link not in seen:
                print(f"➡️ New tweet found for @{username}: {entry.title}")
                send_to_webhook(username, entry)
                updated_seen.add(entry.link)
            else:
                print(f"Already processed tweet for @{username}: {entry.link}")

    save_seen(updated_seen)


if __name__ == "__main__":
    main()
