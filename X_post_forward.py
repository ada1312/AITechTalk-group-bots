import tweepy
import telegram
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# X API credentials
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')

# Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHANNEL')

# X account to monitor
X_ACCOUNT = os.getenv('X_ACCOUNT')

# Initialize X client
auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
x_client = tweepy.API(auth)

# Initialize Telegram bot
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Store the ID of the last processed tweet
last_tweet_id = None

def get_tweets():
    global last_tweet_id
    try:
        tweets = x_client.user_timeline(screen_name=X_ACCOUNT, 
                                        tweet_mode="extended", 
                                        since_id=last_tweet_id,
                                        count=10)
        if tweets:
            last_tweet_id = tweets[0].id
        return tweets
    except Exception as e:
        logger.error(f"Error fetching tweets: {e}")
        return []

async def send_to_telegram(tweet):
    try:
        message = f"New post from @{X_ACCOUNT}:\n\n{tweet.full_text}"
        
        # If the tweet has media, add it to the message
        if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities:
            for media in tweet.extended_entities['media']:
                if media['type'] == 'photo':
                    await telegram_bot.send_photo(chat_id=TELEGRAM_CHAT_ID, 
                                                  photo=media['media_url_https'], 
                                                  caption=message)
                    return
        
        # If no media or after sending media
        await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f"Sent tweet ID {tweet.id} to Telegram")
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")

async def main():
    while True:
        tweets = get_tweets()
        for tweet in reversed(tweets):  # Process older tweets first
            await send_to_telegram(tweet)
        
        # Wait for 5 minutes before the next check
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())