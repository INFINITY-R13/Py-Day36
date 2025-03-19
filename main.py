import os
import requests
import time
from twilio.rest import Client
from dotenv import load_dotenv

# Load API keys from .env file (safer than hardcoding)
load_dotenv()

# Twilio credentials & numbers
VIRTUAL_TWILIO_NUMBER = os.getenv("VIRTUAL_TWILIO_NUMBER")
VERIFIED_NUMBER = os.getenv("VERIFIED_NUMBER")

# Stock & News API keys
STOCK_API_KEY = os.getenv("STOCK_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Twilio credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Stock & Company details
STOCK_NAME = "TSLA"
COMPANY_NAME = "Tesla Inc"

# API endpoints
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"

def get_stock_price_difference():
    """Fetches the stock price difference from Alpha Vantage."""
    stock_params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": STOCK_NAME,
        "apikey": STOCK_API_KEY,
    }

    response = requests.get(STOCK_ENDPOINT, params=stock_params)
    response.raise_for_status()  # Raise error if request fails

    data = response.json().get("Time Series (Daily)", {})

    if len(data) < 2:
        print("Insufficient stock data available.")
        return None, None

    # Convert stock data into a sorted list (most recent first)
    data_list = [value for (_, value) in sorted(data.items(), reverse=True)]

    # Get closing prices
    yesterday_closing = float(data_list[0]["4. close"])
    day_before_yesterday_closing = float(data_list[1]["4. close"])

    # Calculate difference
    difference = yesterday_closing - day_before_yesterday_closing
    percent_change = round((difference / day_before_yesterday_closing) * 100, 2)
    up_down = "🔺" if difference > 0 else "🔻"

    return percent_change, up_down

def get_news():
    """Fetches the top 3 news articles related to the company."""
    news_params = {
        "apiKey": NEWS_API_KEY,
        "qInTitle": COMPANY_NAME,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 3
    }

    response = requests.get(NEWS_ENDPOINT, params=news_params)
    response.raise_for_status()

    articles = response.json().get("articles", [])

    if not articles:
        print("No news articles found.")
        return []

    return [
        f"{STOCK_NAME}: {up_down}{diff_percent}%\nHeadline: {article['title']}.\nBrief: {article['description']}"
        for article in articles
    ]

def send_alerts(messages):
    """Sends stock news alerts via Twilio SMS."""
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    for message in messages:
        sms = client.messages.create(
            body=message,
            from_=VIRTUAL_TWILIO_NUMBER,
            to=VERIFIED_NUMBER
        )
        print(f"Sent: {sms.sid}")
        time.sleep(1)  # Prevent rate-limiting

if __name__ == "__main__":
    diff_percent, up_down = get_stock_price_difference()

    if diff_percent and abs(diff_percent) > 5:  # Threshold of 5% change
        news_messages = get_news()
        if news_messages:
            send_alerts(news_messages)
    else:
        print("Stock price change is not significant enough for an alert.")
