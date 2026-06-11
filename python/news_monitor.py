#!/usr/bin/env python3
"""
Financial News Monitor - Fetches RSS feeds for market news.

Integration with ksf_stockmarket:
- Saves news to MariaDB news_feeds table
- Can filter by symbol or category (crypto, stocks, all)

Sources: Yahoo Finance, MarketWatch, CNBC (stocks), CoinDesk, CoinTelegraph (crypto)
"""

import os
import json
import pymysql
from datetime import datetime, timezone

# Try feedparser, fallback to manual RSS if not available
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

RSS_FEEDS = {
    "crypto": [
        {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "name": "CoinDesk"},
        {"url": "https://cointelegraph.com/rss", "name": "CoinTelegraph"},
    ],
    "stocks": [
        {"url": "https://finance.yahoo.com/news/rssindex", "name": "Yahoo Finance"},
        {"url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "name": "MarketWatch Top Stories"},
        {"url": "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines", "name": "MarketWatch Real-Time"},
        {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "name": "CNBC Top News"},
    ],
    "all": [
        {"url": "https://finance.yahoo.com/news/rssindex", "name": "Yahoo Finance"},
        {"url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "name": "MarketWatch Top Stories"},
        {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "name": "CNBC Top News"},
        {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "name": "CoinDesk"},
        {"url": "https://cointelegraph.com/rss", "name": "CoinTelegraph"},
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; ksf_stockmarket-news/1.0; +https://ksfraser.ca)"


def fetch_news(symbol=None, category="stocks", limit=10):
    """Fetch financial news from RSS feeds."""
    if not FEEDPARSER_AVAILABLE:
        print("feedparser not installed. Run: pip install feedparser")
        return []
    
    feeds = RSS_FEEDS.get(category, RSS_FEEDS["stocks"])
    results = []
    
    for feed_info in feeds:
        if len(results) >= limit:
            break
        try:
            feed = feedparser.parse(feed_info["url"], agent=USER_AGENT)
            source_name = feed.feed.get("title", feed_info["name"])
            
            for entry in feed.entries:
                if len(results) >= limit:
                    break
                
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                
                if symbol:
                    combined = f"{title} {summary}".upper()
                    if symbol.upper() not in combined:
                        continue
                
                published = entry.get("published", entry.get("updated", ""))
                
                results.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "published": published,
                    "summary": clean_html(summary)[:300],
                    "source": source_name,
                    "symbol_filter": symbol,
                })
        except Exception as e:
            print(f"Error fetching {feed_info['name']}: {e}")
            continue
    
    return results[:limit]


def clean_html(text):
    """Strip basic HTML tags from text."""
    import re
    text = re.sub(r"<[^>]+>", "", text)
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")]:
        text = text.replace(entity, char)
    return text.strip()


def save_news_to_db(news_items, category="stocks", conn=None):
    """Save news items to MariaDB news_feeds table."""
    need_close = False
    if not conn:
        need_close = True
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'ksfraser_stockmarket'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'ksfraser_stock_market'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_feeds (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                source VARCHAR(100),
                title VARCHAR(500),
                url TEXT,
                summary TEXT,
                published DATETIME,
                category VARCHAR(20),
                symbol_filter VARCHAR(20),
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_published (published),
                INDEX idx_symbol (symbol_filter)
            )
        """)
        
        for item in news_items:
            cur.execute("""
                INSERT INTO news_feeds (source, title, url, summary, published, category, symbol_filter)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                item['source'],
                item['title'],
                item['url'],
                item['summary'],
                item['published'],
                category,
                item.get('symbol_filter')
            ))
    
    if need_close:
        conn.close()
    
    return len(news_items)


def main():
    """Run news fetch and save for all categories."""
    mysql_pass = os.environ.get('DB_PASSWORD', 'Zaqwsx9sm1@')
    conn = pymysql.connect(
        host='ksfraser.ca',
        user='ksfraser_stockmarket',
        password=mysql_pass,
        database='ksfraser_stock_market',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    
    try:
        # Clear old news (keep last 7 days)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM news_feeds WHERE run_at < DATE_SUB(NOW(), INTERVAL 7 DAY)")
        
        total_saved = 0
        for category in ["crypto", "stocks"]:
            print(f"\nFetching {category} news...")
            news = fetch_news(category=category, limit=20)
            if news:
                saved = save_news_to_db(news, category, conn)
                total_saved += saved
                print(f"  Saved {saved} items")
                for n in news[:3]:
                    print(f"    - {n['title'][:60]}...")
            else:
                print("  No items")
        
        print(f"\nTotal news items saved: {total_saved}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()