"""
Stock Trading News Alert System

This script monitors the daily price change of a specific stock. If the closing price
changes by more than a set percentage, it fetches the top 3 related news articles
and sends them as SMS alerts using the Twilio API.

Setup:
1. Install required libraries: pip install requests python-dotenv twilio
2. Create a .env file in the same directory with the following keys:
   - VIRTUAL_TWILIO_NUMBER
   - VERIFIED_NUMBER
   - STOCK_API_KEY
   - NEWS_API_KEY
   - TWILIO_SID
   - TWILIO_AUTH_TOKEN
"""
import os
import sys
import time
import requests
from twilio.rest import Client
from dotenv import load_dotenv

# --- CONFIGURATION & CONSTANTS ---

# Load environment variables from .env file for security
load_dotenv()

# Twilio credentials & numbers
VIRTUAL_TWILIO_NUMBER = os.getenv("VIRTUAL_TWILIO_NUMBER")
VERIFIED_NUMBER = os.getenv("VERIFIED_NUMBER")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Stock & News API keys
STOCK_API_KEY = os.getenv("STOCK_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Stock & Company details
STOCK_NAME = "TSLA"
COMPANY_NAME = "Tesla Inc"
PRICE_CHANGE_THRESHOLD = 5.0  # The percentage change that triggers an alert

# API endpoints
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"


def get_stock_price_difference() -> tuple | None:
    """
    Fetches daily stock data from Alpha Vantage and calculates the percentage
    difference between the last two closing days.
    
    Returns:
        A tuple containing (percentage_change, up_down_emoji) or None on failure.
    """
    stock_params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": STOCK_NAME,
        "apikey": STOCK_API_KEY,
    }
    try:
        response = requests.get(STOCK_ENDPOINT, params=stock_params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json().get("Time Series (Daily)", {})

    except requests.exceptions.RequestException as e:
        print(f"Error fetching stock data: {e}")
        return None

    # Ensure there is enough data to compare two days
    if len(data) < 2:
        print("Insufficient stock data available for comparison.")
        return None

    # Convert the dictionary of daily data into a list, sorted by date (most recent first)
    data_list = [value for (_, value) in sorted(data.items(), reverse=True)]

    # Get the closing prices for the last two trading days
    yesterday_closing = float(data_list[0]["4. close"])
    day_before_yesterday_closing = float(data_list[1]["4. close"])

    # Calculate the difference and percentage change
    difference = yesterday_closing - day_before_yesterday_closing
    percent_change = round((difference / day_before_yesterday_closing) * 100, 2)
    up_down = "🔺" if difference > 0 else "🔻"

    return percent_change, up_down


def get_news(up_down: str, diff_percent: float) -> list:
    """
    Fetches the top 3 news articles related to the company from NewsAPI.
    
    Args:
        up_down (str): The emoji indicating if the stock went up or down.
        diff_percent (float): The percentage change of the stock price.
        
    Returns:
        A list of formatted strings, where each string is a message for an SMS.
    """
    news_params = {
        "apiKey": NEWS_API_KEY,
        "qInTitle": COMPANY_NAME,  # Search for the company name in the article title
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 3  # Fetch the top 3 articles
    }
    try:
        response = requests.get(NEWS_ENDPOINT, params=news_params)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news data: {e}")
        return []

    if not articles:
        print("No news articles found.")
        return []

    # Format each article into a message string
    return [
        f"{STOCK_NAME}: {up_down}{diff_percent}%\nHeadline: {article['title']}.\nBrief: {article['description']}"
        for article in articles
    ]


def send_alerts(messages: list):
    """
    Sends a list of messages as SMS alerts via the Twilio API.
    
    Args:
        messages (list): A list of strings to be sent as SMS.
    """
    # Check for missing credentials
    if not all([TWILIO_SID, TWILIO_AUTH_TOKEN, VIRTUAL_TWILIO_NUMBER, VERIFIED_NUMBER]):
        print("Twilio credentials are not fully configured. Cannot send SMS.")
        return

    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    for message in messages:
        try:
            sms = client.messages.create(
                body=message,
                from_=VIRTUAL_TWILIO_NUMBER,
                to=VERIFIED_NUMBER
            )
            print(f"Message sent successfully! SID: {sms.sid}")
        except Exception as e:
            print(f"Failed to send SMS: {e}")
        
        # Wait for 1 second between messages to avoid rate-limiting issues
        time.sleep(1)


def main():
    """Main execution function."""
    price_data = get_stock_price_difference()

    # Proceed only if stock data was successfully fetched
    if price_data:
        diff_percent, up_down = price_data
        print(f"Today's {STOCK_NAME} price change: {up_down}{diff_percent}%")

        # Check if the absolute percentage change meets our threshold
        if abs(diff_percent) >= PRICE_CHANGE_THRESHOLD:
            print(f"Price change exceeds threshold of {PRICE_CHANGE_THRESHOLD}%. Fetching news...")
            news_messages = get_news(up_down, diff_percent)
            if news_messages:
                send_alerts(news_messages)
        else:
            print("Stock price change is not significant enough for an alert.")


if __name__ == "__main__":
    main()