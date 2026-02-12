import requests
from bs4 import BeautifulSoup
import os

# Scrape.do API key (stored in GitHub Actions secrets)
SCRAPE_API_KEY = os.getenv("SCRAPE_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Your Make.com webhook URL
WEBHOOK_URL = "https://hook.eu1.make.com/your-webhook-id"

# List of usernames to monitor
USERNAMES = [
    "visegrad24",
    "MarioNawfal",
    "illuminatibot",
    "redpillb0t",
]

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


def fetch_latest_tweet(username):
    """Fetch only the latest tweet using Scrape.do API."""
    target_url = f"https://twitter.com/{username}"
    api_url = f"https://api.scrape.do?token={SCRAPE_API_KEY}&url={target_url}"

    try:
        response = requests.get(api_url, timeout=20)
        if response.status_code != 200:
            print(f"❌ Failed to fetch @{username}, status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Grab the first <article> (latest tweet)
        article = soup.select_one("article")
        if not article:
            print(f"⚠️ No tweets found for @{username}")
            return None

        text_block = article.select_one("div[lang]")
        text = text_block.get_text() if text_block else None

        # Extract media (images/videos)
        media_urls = []
        for img in article.select("img"):
            if "profile" not in img["src"]:  # skip profile pics
                media_urls.append(img["src"])
        for video in article.select("video"):
            if video.has_attr("src"):
                media_urls.append(video["src"])

        # Extract link (unique identifier)
        link_tag = article.find("a", href=True)
        link = f"https://twitter.com{link_tag['href']}" if link_tag else None

        if text and link:
            return {
                "username": username,
                "text": text,
                "media": media_urls,
                "link": link
            }

        return None

    except Exception as e:
        print(f"❌ Error fetching @{username}: {e}")
        return None


def send_to_webhook(tweet):
    """Send tweet data to Make.com webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=tweet)
        print(f"Sent latest tweet from @{tweet['username']}, status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending webhook for @{tweet['username']}: {e}")


def main():
    seen = load_seen()
    updated_seen = set(seen)

    for username in USERNAMES:
        print(f"Fetching latest tweet for @{username}...")
        tweet = fetch_latest_tweet(username)
        if tweet:
            if tweet["link"] not in seen:
                print(f"➡️ New tweet: {tweet['text'][:50]}...")
                send_to_webhook(tweet)
                updated_seen.add(tweet["link"])
            else:
                print(f"Already processed latest tweet: {tweet['link']}")

    save_seen(updated_seen)


if __name__ == "__main__":
    main()
