import feedparser
import requests
import time

accounts = ["visegrad24", "MarioNawfal", "illuminatibot", "redpillb0t"]
webhook_url = "https://hook.eu1.make.com/ze6g6ouqsvjigxeocgega4ufrh7km9hl"

for account in accounts:
    print(f"Fetching feed for @{account}...")
    feed = feedparser.parse(f"https://nitter.net/{account}/rss")
    
    if feed.entries:
        latest = feed.entries[0]
        images = [e.href for e in getattr(latest, "enclosures", [])]  # ✅ capture media if available
        
        data = {
            "account": account,
            "content": latest.title,
            "url": latest.link,
            "date": latest.published,
            "media": images
        }
        
        response = requests.post(webhook_url, json=data)
        print(f"Sent tweet from @{account}, status: {response.status_code}, images: {images}")
    else:
        print(f"No tweets found for @{account}")
    
    time.sleep(5)   # 💤 wait 5 seconds before next account

