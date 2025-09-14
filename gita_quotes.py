import random

# Collection of Bhagavad Gita inspired messages
GITA_QUOTES = [
    "Focus on your work, not the results. Excellence comes from dedication.",
    "Stay calm in success and failure. Balance leads to wisdom.",
    "Control your mind, for it can be your best friend or worst enemy.",
    "Work with full dedication, but remain detached from the outcome.",
    "Knowledge is power, but wisdom is knowing how to use it.",
    "Face challenges with courage. Every difficulty makes you stronger.",
    "Be present in this moment. Past and future exist only in the mind.",
    "Serve others selflessly. True joy comes from giving.",
    "Maintain equanimity in all situations. This is true strength.",
    "Your actions shape your character. Choose them wisely.",
    "Overcome fear with knowledge and faith in yourself.",
    "Practice patience and perseverance. Great things take time.",
    "Find peace within yourself. External circumstances change, but inner peace remains.",
    "Work is worship when done with the right intention.",
    "Transform obstacles into opportunities through positive thinking.",
    "Discipline your desires. True freedom comes from self-control.",
    "Share your knowledge and skills. Teaching others elevates you too.",
    "Maintain hope in difficult times. Dawn always follows the darkest hour.",
    "Be grateful for what you have. Contentment brings happiness.",
    "Live with purpose. Let your work contribute to something greater.",
]

def get_random_quote():
    """Get a random quote from the collection"""
    return random.choice(GITA_QUOTES)

def get_daily_quote():
    """Get a consistent quote for the day based on date"""
    from datetime import datetime
    import random
    
    # Use today's date as seed for consistency throughout the day
    today = datetime.now().strftime("%Y-%m-%d")
    random.seed(today)
    quote = random.choice(GITA_QUOTES)
    
    # Reset random seed
    random.seed()
    return quote