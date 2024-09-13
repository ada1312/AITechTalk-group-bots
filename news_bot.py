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
from telebot.async_telebot import AsyncTeleBot
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Load environment variables
load_dotenv()

# Get API keys from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Specify the news sources and keywords we want
ALLOWED_SOURCES = ['Forbes', 'TechCrunch', 'Wired', 'MIT Technology Review', 'VentureBeat']
KEYWORDS = ['AI', 'artificial intelligence', 'machine learning', 'deep learning', 'neural networks', 'NLP', 'computer vision']

bot = AsyncTeleBot(TELEGRAM_BOT_TOKEN)

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

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    welcome_text = (
        "Welcome to the AI News Bot! 🤖📰\n\n"
        "I'm here to keep you updated with the latest AI news. Here are the commands you can use:\n\n"
        "/news - Get the latest AI news\n"
        "/sources - See the list of news sources\n"
        "/keywords - View the AI-related keywords I'm tracking\n\n"
        "Feel free to ask for news anytime!"
    )
    await bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['news'])
async def send_news(message):
    await bot.reply_to(message, "Fetching the latest AI news... Please wait.")
    news_message = await get_ai_news()
    try:
        await bot.send_message(message.chat.id, news_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        await bot.reply_to(message, "Sorry, I encountered an error while sending the news. Please try again later.")

@bot.message_handler(commands=['sources'])
async def send_sources(message):
    sources_text = "I'm currently fetching news from these sources:\n\n" + "\n".join(ALLOWED_SOURCES)
    await bot.reply_to(message, sources_text)

@bot.message_handler(commands=['keywords'])
async def send_keywords(message):
    keywords_text = "I'm tracking news related to these AI keywords:\n\n" + "\n".join(KEYWORDS)
    await bot.reply_to(message, keywords_text)

async def main():
    if not NEWS_API_KEY or not TELEGRAM_BOT_TOKEN:
        logger.error("Error: NEWS_API_KEY or TELEGRAM_BOT_TOKEN is not set in the environment variables.")
        return

    try:
        logger.info("Starting bot polling...")
        await bot.polling(non_stop=True, timeout=60)
    except Exception as e:
        logger.error(f"Error in bot polling: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())