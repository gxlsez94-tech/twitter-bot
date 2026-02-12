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

        # Try multiple selectors for tweet containers
        article = soup.select_one("article") or soup.select_one('div[data-testid="tweet"]')
        if not article:
            print(f"⚠️ No tweets found for @{username}")
            return None

        # Extract text
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
