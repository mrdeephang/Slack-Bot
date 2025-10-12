import random
from gita_quotes_data import GITA_QUOTES

def get_random_quote():
    """Return a random Gita-inspired quote"""
    return random.choice(GITA_QUOTES)

def get_daily_quote():
    """Return a consistent quote for the day based on the date"""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    random.seed(today)
    quote = random.choice(GITA_QUOTES)
    random.seed()  # Reset seed for other random ops
    return quote
