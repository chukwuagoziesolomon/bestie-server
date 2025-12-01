"""
Personalized WhatsApp Greeting System
Creates exciting, fun, and time-appropriate greetings for users
"""
from datetime import datetime, timezone
import random
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WhatsAppGreetingService:
    """Service for creating personalized WhatsApp greetings"""
    
    def __init__(self):
        # Time-based greeting templates
        self.morning_greetings = [
            "Good morning, {name}! ☀️ Ready to start your day with something delicious?",
            "Rise and shine, {name}! 🌅 What's for breakfast today?",
            "Morning, {name}! 🌤️ Let's fuel your day with amazing food!",
            "Hey {name}! 🌞 Hope you're having a fantastic morning! Hungry yet?",
            "Good morning, {name}! 🌻 Time to treat yourself to something tasty!"
        ]
        
        self.afternoon_greetings = [
            "Good afternoon, {name}! 🌤️ Ready for a delicious lunch break?",
            "Hey {name}! ☀️ Lunchtime calls - what are you craving?",
            "Afternoon, {name}! 🍽️ Time to refuel with something amazing!",
            "Hi {name}! 🌞 Perfect timing for a tasty meal!",
            "Good afternoon, {name}! 🥗 Let's make this meal memorable!"
        ]
        
        self.evening_greetings = [
            "Good evening, {name}! 🌆 Ready for a delightful dinner?",
            "Evening, {name}! 🍴 Time to unwind with something delicious!",
            "Hey {name}! 🌇 What sounds good for dinner tonight?",
            "Good evening, {name}! ✨ Let's make tonight's meal special!",
            "Hi {name}! 🌃 Perfect time for a satisfying dinner!"
        ]
        
        self.night_greetings = [
            "Hey {name}! 🌙 Late night cravings? I've got you covered!",
            "Good evening, {name}! 🌟 Hungry for a midnight treat?",
            "Hi {name}! 🌌 Sometimes the best meals happen at night!",
            "Hey there, {name}! 🌛 What's calling to you tonight?",
            "Evening, {name}! ⭐ Let's satisfy those late-night cravings!"
        ]
        
        # First-time/anonymous greetings
        self.welcome_greetings = [
            "Hello there! 👋 Welcome to Bestyy - your food adventure starts here! 🍴✨",
            "Hey! 🤗 Welcome to Bestyy! I'm here to help you discover amazing food! 🍕🎉",
            "Hi! 😊 Welcome to Bestyy - where every meal is an adventure! 🍽️🌟",
            "Hello! 👋 Welcome to the tastiest place on WhatsApp - Bestyy! 🍔🎊",
            "Hey there! 🙋‍♀️ Welcome to Bestyy! Ready to explore delicious food? 🍜💫"
        ]
        
        # Returning user greetings (when user is known)
        self.returning_user_greetings = [
            "Welcome back, {name}! 🎉 Missed you! What delicious adventure shall we go on today?",
            "Hey {name}! 😄 Great to see you again! Ready for another tasty discovery?",
            "Hi {name}! 🤗 Welcome back! I've been waiting to help you find something yummy!",
            "{name}! 🙌 You're back! Let's make this meal even better than the last one!",
            "Hey there, {name}! 😊 Ready to explore more amazing flavors today?"
        ]
        
        # Food-themed emojis for excitement
        self.food_emojis = ["🍕", "🍔", "🍜", "🍛", "🥗", "🍖", "🍗", "🥘", "🍝", "🌮", "🌯", "🥙", "🍤", "🍣", "🍱"]
        self.excitement_emojis = ["😋", "🤤", "😍", "🔥", "⭐", "✨", "💫", "🎉", "🎊", "👌", "💯"]
    
    def get_time_of_day(self) -> str:
        """Get current time of day category"""
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            return "morning"
        elif 12 <= current_hour < 17:
            return "afternoon"
        elif 17 <= current_hour < 22:
            return "evening"
        else:
            return "night"
    
    def get_welcome_greeting(self) -> str:
        """Get greeting for first-time users (no name yet)"""
        base_greeting = random.choice(self.welcome_greetings)
        food_emoji = random.choice(self.food_emojis)
        
        return f"{base_greeting}\n\nI'm your personal food guide! {food_emoji} To get started and give you the best recommendations, I'll need your email address to create your account!"
    
    def get_personalized_greeting(self, name: str, is_returning: bool = False) -> str:
        """
        Get personalized greeting based on time and user status
        
        Args:
            name: User's first name
            is_returning: True if user is returning after some time
            
        Returns:
            Personalized greeting message
        """
        time_of_day = self.get_time_of_day()
        
        # Choose appropriate greeting template
        if is_returning:
            greeting = random.choice(self.returning_user_greetings).format(name=name)
        else:
            # Use time-based greetings
            if time_of_day == "morning":
                greeting = random.choice(self.morning_greetings).format(name=name)
            elif time_of_day == "afternoon":
                greeting = random.choice(self.afternoon_greetings).format(name=name)
            elif time_of_day == "evening":
                greeting = random.choice(self.evening_greetings).format(name=name)
            else:  # night
                greeting = random.choice(self.night_greetings).format(name=name)
        
        # Add some food excitement
        food_emoji = random.choice(self.food_emojis)
        excitement_emoji = random.choice(self.excitement_emojis)
        
        # Add a fun food-related follow-up
        follow_ups = [
            f"What's making your mouth water today? {food_emoji}",
            f"Ready to discover something delicious? {excitement_emoji}",
            f"I've got amazing recommendations waiting for you! {food_emoji}",
            f"Let's find you something absolutely yummy! {excitement_emoji}",
            f"Time to treat your taste buds! {food_emoji}",
            f"What flavors are calling to you? {excitement_emoji}"
        ]
        
        follow_up = random.choice(follow_ups)
        
        return f"{greeting}\n\n{follow_up}"
    
    def get_post_signup_celebration(self, name: str) -> str:
        """Get exciting welcome message after successful signup"""
        celebration_messages = [
            f"🎉 Woohoo! Welcome to the Bestyy family, {name}! 🎊",
            f"✨ Amazing! {name}, you're all set for food adventures! 🌟",
            f"🎈 Fantastic! {name}, your taste buds are in for a treat! 🎉",
            f"🚀 Awesome! {name}, let's embark on this delicious journey together! ✨",
            f"💫 Perfect! {name}, get ready for some amazing food discoveries! 🎊"
        ]
        
        time_of_day = self.get_time_of_day()
        food_emoji = random.choice(self.food_emojis)
        excitement_emoji = random.choice(self.excitement_emojis)
        
        celebration = random.choice(celebration_messages)
        
        # Add time-appropriate food suggestion
        if time_of_day == "morning":
            suggestion = f"Ready to start your day with something delicious? {food_emoji}"
        elif time_of_day == "afternoon":
            suggestion = f"Perfect timing for lunch! What sounds good? {food_emoji}"
        elif time_of_day == "evening":
            suggestion = f"Dinner time! Let's find you something amazing! {food_emoji}"
        else:
            suggestion = f"Late night cravings? I've got the perfect suggestions! {food_emoji}"
        
        return f"{celebration}\n\n{suggestion} {excitement_emoji}\n\nWhat are you in the mood for?"
    
    def get_food_discovery_prompt(self, name: str = None) -> str:
        """Get exciting food discovery prompts"""
        if name:
            prompts = [
                f"So {name}, what's your vibe today? 😋",
                f"Tell me {name}, what flavors are you craving? 🤤",
                f"What sounds good to you today, {name}? 🍴",
                f"{name}, ready to explore some tasty options? ✨",
                f"What's calling to your taste buds, {name}? 🔥"
            ]
        else:
            prompts = [
                "So, what's your vibe today? 😋",
                "What flavors are you craving? 🤤", 
                "What sounds good to you? 🍴",
                "Ready to explore some tasty options? ✨",
                "What's calling to your taste buds? 🔥"
            ]
        
        food_suggestions = [
            "🍕 Pizza • 🍔 Burgers • 🍜 Local dishes",
            "🌮 Mexican • 🍛 Asian • 🥗 Healthy options", 
            "🍖 Grilled • 🍝 Pasta • 🍤 Seafood",
            "🥘 Spicy dishes • 🍗 Fried chicken • 🌯 Wraps",
            "🍱 Rice bowls • 🥙 Shawarma • 🍕 Italian"
        ]
        
        prompt = random.choice(prompts)
        suggestions = random.choice(food_suggestions)
        
        return f"{prompt}\n\n{suggestions}\n\nJust tell me what you're in the mood for, or I can suggest something amazing! 🎯"


# Global instance for easy import
whatsapp_greeting_service = WhatsAppGreetingService()