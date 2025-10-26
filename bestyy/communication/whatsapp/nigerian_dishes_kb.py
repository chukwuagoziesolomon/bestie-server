"""
Nigerian Dishes Knowledge Base
Comprehensive database of Nigerian dishes for better LLM understanding
"""
from typing import Optional, Dict, List

NIGERIAN_DISHES = {
    # Soups
    'egusi soup': {
        'aliases': ['egusi', 'egusi soup', 'egwusi', 'egwusi soup', 'melon soup'],
        'category': 'soup',
        'description': 'Soup made with melon seeds, leafy greens, and meat',
        'keywords': ['egusi', 'egwusi', 'melon', 'soup']
    },
    'okoro soup': {
        'aliases': ['okoro', 'okoro soup', 'okra soup'],
        'category': 'soup',
        'description': 'Soup made with okra, meat, and spices',
        'keywords': ['okoro', 'okra', 'soup']
    },
    'efo riro': {
        'aliases': ['efo riro', 'efo', 'spinach soup'],
        'category': 'soup',
        'description': 'Spinach-based soup with meat and spices',
        'keywords': ['efo', 'riro', 'spinach']
    },
    'afang soup': {
        'aliases': ['afang', 'afang soup', 'waterleaf soup'],
        'category': 'soup',
        'description': 'Soup made with waterleaf and pumpkin seeds',
        'keywords': ['afang', 'waterleaf', 'soup']
    },
    'pepper soup': {
        'aliases': ['pepper soup', 'pepper', 'spicy soup'],
        'category': 'soup',
        'description': 'Spicy soup with meat or fish and peppers',
        'keywords': ['pepper', 'soup', 'spicy']
    },
    'oha soup': {
        'aliases': ['oha', 'oha soup'],
        'category': 'soup',
        'description': 'Soup made with oha leaves and cocoyam',
        'keywords': ['oha', 'soup']
    },
    'bitter leaf soup': {
        'aliases': ['bitter leaf', 'bitter leaf soup', 'ofe onugbu'],
        'category': 'soup',
        'description': 'Soup made with bitter leaves and meat',
        'keywords': ['bitter', 'leaf', 'soup']
    },
    
    # Carbs/Staples
    'eba': {
        'aliases': ['eba', 'gari', 'cassava'],
        'category': 'staple',
        'description': 'Cassava-based staple food, smooth and dough-like',
        'keywords': ['eba', 'gari', 'cassava']
    },
    'fufu': {
        'aliases': ['fufu', 'pounded yam', 'plantain fufu'],
        'category': 'staple',
        'description': 'Pounded yam or plantain, smooth and stretchy',
        'keywords': ['fufu', 'pounded', 'yam']
    },
    'pounded yam': {
        'aliases': ['pounded yam', 'fufu', 'yam'],
        'category': 'staple',
        'description': 'Boiled and pounded yam, creamy texture',
        'keywords': ['pounded', 'yam', 'fufu']
    },
    'jollof rice': {
        'aliases': ['jollof rice', 'jollof', 'rice'],
        'category': 'rice',
        'description': 'Aromatic rice cooked in tomato sauce with spices',
        'keywords': ['jollof', 'rice', 'tomato']
    },
    'fried rice': {
        'aliases': ['fried rice', 'rice'],
        'category': 'rice',
        'description': 'Rice stir-fried with vegetables and meat',
        'keywords': ['fried', 'rice']
    },
    'amala': {
        'aliases': ['amala', 'yam flour'],
        'category': 'staple',
        'description': 'Yam flour-based staple, dark and smooth',
        'keywords': ['amala', 'yam', 'flour']
    },
    'semovita': {
        'aliases': ['semovita', 'semolina'],
        'category': 'staple',
        'description': 'Semolina-based staple, light and fluffy',
        'keywords': ['semovita', 'semolina']
    },
    
    # Proteins/Sides
    'moi moi': {
        'aliases': ['moi moi', 'moyi moyi', 'bean pudding'],
        'category': 'protein',
        'description': 'Steamed bean pudding with spices and meat',
        'keywords': ['moi', 'moyi', 'bean', 'pudding']
    },
    'akara': {
        'aliases': ['akara', 'bean cake', 'fried bean'],
        'category': 'snack',
        'description': 'Fried bean cakes, crispy outside, soft inside',
        'keywords': ['akara', 'bean', 'cake', 'fried']
    },
    'suya': {
        'aliases': ['suya', 'grilled meat', 'meat skewer'],
        'category': 'protein',
        'description': 'Spiced grilled meat on skewers',
        'keywords': ['suya', 'grilled', 'meat', 'spiced']
    },
    'kilishi': {
        'aliases': ['kilishi', 'dried meat', 'jerky'],
        'category': 'protein',
        'description': 'Dried and spiced meat strips',
        'keywords': ['kilishi', 'dried', 'meat']
    },
    'chin chin': {
        'aliases': ['chin chin', 'chinchin'],
        'category': 'snack',
        'description': 'Crispy fried snack made from flour',
        'keywords': ['chin', 'chinchin', 'snack']
    },
    'plantain chips': {
        'aliases': ['plantain chips', 'fried plantain', 'plantain'],
        'category': 'snack',
        'description': 'Fried plantain slices, crispy and golden',
        'keywords': ['plantain', 'chips', 'fried']
    },
    
    # Stews
    'tomato stew': {
        'aliases': ['tomato stew', 'stew'],
        'category': 'stew',
        'description': 'Tomato-based stew with meat and spices',
        'keywords': ['tomato', 'stew']
    },
    'groundnut stew': {
        'aliases': ['groundnut stew', 'peanut stew', 'groundnut'],
        'category': 'stew',
        'description': 'Peanut-based stew with meat',
        'keywords': ['groundnut', 'peanut', 'stew']
    },
}

# Quick lookup by keyword
NIGERIAN_KEYWORDS = {}
for dish_name, dish_info in NIGERIAN_DISHES.items():
    for keyword in dish_info['keywords']:
        if keyword not in NIGERIAN_KEYWORDS:
            NIGERIAN_KEYWORDS[keyword] = []
        NIGERIAN_KEYWORDS[keyword].append(dish_name)


def find_nigerian_dish(text: str) -> Optional[str]:
    """
    Find Nigerian dish from user text
    Returns the canonical dish name or None
    """
    text_lower = text.lower()
    
    # Check exact matches first
    for dish_name in NIGERIAN_DISHES.keys():
        if dish_name in text_lower:
            return dish_name
    
    # Check aliases
    for dish_name, dish_info in NIGERIAN_DISHES.items():
        for alias in dish_info['aliases']:
            if alias in text_lower:
                return dish_name
    
    # Check keywords
    for keyword, dishes in NIGERIAN_KEYWORDS.items():
        if keyword in text_lower:
            return dishes[0]  # Return first match
    
    return None


def get_dish_info(dish_name: str) -> Optional[Dict]:
    """Get information about a Nigerian dish"""
    return NIGERIAN_DISHES.get(dish_name.lower())


def is_nigerian_dish(text: str) -> bool:
    """Check if text contains a Nigerian dish"""
    return find_nigerian_dish(text) is not None


def get_all_nigerian_dishes() -> List[str]:
    """Get list of all Nigerian dishes"""
    return list(NIGERIAN_DISHES.keys())


def get_dishes_by_category(category: str) -> List[str]:
    """Get Nigerian dishes by category"""
    return [
        dish_name for dish_name, info in NIGERIAN_DISHES.items()
        if info['category'] == category
    ]


# System prompt for LLM with Nigerian dishes context
NIGERIAN_DISHES_SYSTEM_PROMPT = """You are a helpful food delivery assistant for a Nigerian food delivery service.

You are familiar with Nigerian dishes and cuisine. Here are some common Nigerian dishes:

SOUPS:
- Egusi Soup: Made with melon seeds, leafy greens, and meat
- Okoro Soup: Made with okra, meat, and spices
- Efo Riro: Spinach-based soup with meat
- Afang Soup: Made with waterleaf and pumpkin seeds
- Pepper Soup: Spicy soup with meat or fish
- Oha Soup: Made with oha leaves and cocoyam
- Bitter Leaf Soup: Made with bitter leaves and meat

STAPLES:
- Eba: Cassava-based staple, smooth and dough-like
- Fufu/Pounded Yam: Boiled and pounded yam, creamy
- Amala: Yam flour-based staple
- Semovita: Semolina-based staple
- Jollof Rice: Aromatic rice in tomato sauce
- Fried Rice: Stir-fried rice with vegetables

PROTEINS/SIDES:
- Moi Moi: Steamed bean pudding
- Akara: Fried bean cakes
- Suya: Spiced grilled meat on skewers
- Kilishi: Dried and spiced meat strips
- Chin Chin: Crispy fried snack
- Plantain Chips: Fried plantain slices

When a user mentions any Nigerian dish, you should:
1. Recognize it immediately
2. Search for vendors serving that dish
3. Show available options
4. Help them place an order
5. NOT explain what the dish is (they already know)
6. Go straight to ordering

Be concise and action-oriented. Focus on helping them order, not explaining."""

