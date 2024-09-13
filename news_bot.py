import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
import nltk
import math
import random
import telebot
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Load environment variables
load_dotenv()

# Get API keys and chat ID from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

# Specify the news sources and keywords we want
ALLOWED_SOURCES = ['Forbes', 'TechCrunch', 'Wired', 'MIT Technology Review', 'VentureBeat']
KEYWORDS = ['AI', 'artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 'NLP', 'computer vision']

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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
                    logger.error(f"Unexpected API response structure: {data}")
                    return None
            else:
                logger.error(f"Error fetching news: {response.status}")
                logger.error(f"Response content: {await response.text()}")
                return None

def summarize_text(text, num_sentences=2):
    sentences = sent_tokenize(text)
    words = [word.lower() for sentence in sentences for word in sentence.split() if word.lower() not in stopwords.words('english')]
    freq_dist = FreqDist(words)
    sentence_scores = {sentence: sum(freq_dist[word.lower()] for word in sentence.split() if word.lower() not in stopwords.words('english')) for sentence in sentences}
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

def get_random_emoji():
    ai_emojis = ["🤖", "🧠", "💡", "🔬", "🚀", "💻", "🔮", "🎛️", "🌐", "📊"]
    return random.choice(ai_emojis)

def format_news_message(articles):
    if not articles:
        return "No relevant AI news found at the moment."

    message = f"{get_random_emoji()} AI News Roundup {get_random_emoji()}\n\n"
    message += "Today's top AI stories:\n\n"

    for index, article in enumerate(articles[:5], start=1):
        summary = summarize_text(article['content'])
        reading_time = calculate_reading_time(article['content'])
        
        message += f"{index}. {article['title']}\n"
        message += f"Source: {article['source']['name']}\n"
        message += f"Summary: {summary[:200]}...\n"
        message += f"Reading time: {reading_time}\n"
        message += f"Link: {article['url']}\n\n"

    return message

async def get_ai_news():
    news_articles = await fetch_ai_news()
    if news_articles:
        return format_news_message(news_articles)
    else:
        return "Sorry, I couldn't fetch any news at the moment. Please try again later."

def check_bot_membership():
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_CHAT_ID, bot.get_me().id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiException as e:
        logger.error(f"Error checking bot membership: {e}")
        return False

async def send_news_update():
    logger.info("Checking bot membership in the group")
    if not check_bot_membership():
        logger.error("Bot is not a member of the group. Please add the bot to the group and grant necessary permissions.")
        return

    logger.info("Sending news update to the group")
    news_message = await get_ai_news()
    try:
        bot.send_message(TELEGRAM_GROUP_CHAT_ID, news_message, parse_mode='HTML')
        logger.info("News update sent successfully")
    except telebot.apihelper.ApiException as e:
        logger.error(f"Telegram API error: {e}")
        if "bot was kicked" in str(e).lower():
            logger.error("The bot was kicked from the group. Please add it back and grant necessary permissions.")
        elif "chat not found" in str(e).lower():
            logger.error("The specified group chat was not found. Please check the TELEGRAM_GROUP_CHAT_ID.")
        elif "not enough rights" in str(e).lower():
            logger.error("The bot doesn't have enough rights to send messages. Please check its permissions in the group.")
    except Exception as e:
        logger.error(f"Unexpected error sending news update: {str(e)}")

async def main():
    if not NEWS_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_GROUP_CHAT_ID:
        logger.error("Error: NEWS_API_KEY, TELEGRAM_BOT_TOKEN, or TELEGRAM_GROUP_CHAT_ID is not set in the environment variables.")
        return

    await send_news_update()

if __name__ == "__main__":
    asyncio.run(main())