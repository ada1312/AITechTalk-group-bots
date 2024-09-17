import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
import spacy
import math
import random
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load the small English NLP model from spaCy
nlp = spacy.load('en_core_web_sm')

# Load environment variables
load_dotenv()

# Get API keys from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL')

# Specify the news sources and keywords we want
ALLOWED_SOURCES = ['Forbes', 'TechCrunch', 'Wired', 'MIT Technology Review', 'VentureBeat']
KEYWORDS = ['AI', 'artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 'prompt engineering']

async def fetch_ai_news():
    seven_days_ago = (datetime.now() - timedelta(7)).strftime('%Y-%m-%d')
    
    url = f'https://newsapi.org/v2/everything?q=({" OR ".join(KEYWORDS)})&language=en&from={seven_days_ago}&sortBy=relevancy&apiKey={NEWS_API_KEY}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if 'articles' in data:
                    filtered_articles = [
                        article for article in data['articles']
                        if article['source']['name'] in ALLOWED_SOURCES and
                        any(keyword.lower() in article['title'].lower() for keyword in KEYWORDS)
                    ]
                    return filtered_articles
                else:
                    logging.error(f"Unexpected API response structure: {data}")
                    return None
            else:
                logging.error(f"Error fetching news: {response.status}")
                logging.error(f"Response content: {await response.text()}")
                return None

def summarize_text(text, num_sentences=2):
    # Use spaCy to tokenize the text into sentences
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    
    # Frequency-based sentence scoring
    words = [token.text.lower() for token in doc if not token.is_stop and not token.is_punct]
    word_freq = {word: words.count(word) for word in set(words)}
    
    sentence_scores = {sentence: sum(word_freq.get(token.text.lower(), 0) for token in nlp(sentence)) for sentence in sentences}
    summary_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    summary = ' '.join(summary_sentences)
    return summary

def calculate_reading_time(content):
    clean_content = ''.join(char for char in content if char not in '<>')
    word_count = len(clean_content.split())
    reading_time_minutes = math.ceil(word_count / 200)
    
    if reading_time_minutes < 1:
        return "< 1 min"
    elif reading_time_minutes == 1:
        return "1 min"
    else:
        return f"{reading_time_minutes} mins"

def get_news_emoji(title):
    keywords = {
        "research": "🔬", "breakthrough": "💡", "robot": "🤖", "language": "🗣️",
        "vision": "👁️", "ethics": "🤔", "business": "💼", "health": "🏥",
        "data": "📊", "cloud": "☁️", "security": "🔒", "innovation": "🚀",
        "startup": "🌱", "investment": "💰", "education": "🎓", "future": "🔮"
    }
    for keyword, emoji in keywords.items():
        if keyword in title.lower():
            return emoji
    return "🧠"  # Default AI-related emoji

def format_news_message(articles):
    if not articles:
        return "No relevant AI news found at the moment."

    header_emoji = random.choice(["🤖", "🧠", "💡", "🚀", "🔬", "💻", "🌐", "📊"])
    message = f"{header_emoji} <b>AI News Roundup</b> {header_emoji}\n\n"
    message += f"📅 <i>{datetime.now().strftime('%B %d, %Y')}</i>\n\n"
    message += "🔥 <b>Top AI Stories:</b>\n\n"

    for index, article in enumerate(articles[:5], start=1):
        news_emoji = get_news_emoji(article['title'])
        summary = summarize_text(article['content'])
        reading_time = calculate_reading_time(article['content'])
        
        message += f"{index}. {news_emoji} <b>{article['title']}</b>\n\n"
        message += f"   📰 <i>{article['source']['name']}</i> | ⏱️ <i>{reading_time}</i>\n\n"
        message += f"   {summary[:150]}...\n\n"
        message += f"   🔗 <a href='{article['url']}'>Read full article</a>\n\n"
        
        if index < len(articles[:5]):
            message += "   ──────────────────────\n\n"

    hashtags = "#AINews #ArtificialIntelligence #MachineLearning #TechInnovation"
    message += f"\n{hashtags}\n\n"
    message += "💬 <i>Want to discuss these stories? Join our AI community chat!</i>\n"
    message += "🔔 <i>Stay tuned for more AI updates!</i>"

    return message

async def get_ai_news():
    news_articles = await fetch_ai_news()
    if news_articles:
        return format_news_message(news_articles)
    else:
        return "Sorry, I couldn't fetch any news at the moment. Please try again later."

async def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHANNEL,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    logging.info(f"Attempting to send message to channel: {TELEGRAM_CHANNEL}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logging.info("Message sent successfully")
                    response_json = await response.json()
                    logging.info(f"Response: {response_json}")
                else:
                    logging.error(f"Failed to send message: {response.status}")
                    response_text = await response.text()
                    logging.error(f"Response: {response_text}")
        except Exception as e:
            logging.error(f"Error while sending message: {e}")

async def main():
    logging.info("Starting main function with TELEGRAM_CHANNEL: ***")
    
    news_message = await get_ai_news()
    await send_telegram_message(news_message)

if __name__ == '__main__':
    asyncio.run(main())
