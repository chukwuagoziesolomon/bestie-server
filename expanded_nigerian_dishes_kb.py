"""
Expanded Nigerian Dishes Knowledge Base
Comprehensive database of Nigerian dishes with regional information and detailed descriptions
"""
from typing import Optional, Dict, List

NIGERIAN_DISHES = {
    # Soups & Stews
    'egusi soup': {
        'aliases': ['egusi', 'egusi soup', 'egwusi', 'egwusi soup', 'melon soup'],
        'category': 'soup',
        'description': 'Melon seed soup, eaten across Nigeria',
        'region': 'nationwide',
        'keywords': ['egusi', 'egwusi', 'melon', 'soup']
    },
    'ogbono soup': {
        'aliases': ['ogbono', 'ogbono soup', 'wild mango seed soup'],
        'category': 'soup',
        'description': 'Wild mango seed soup',
        'region': 'nationwide',
        'keywords': ['ogbono', 'wild', 'mango', 'soup']
    },
    'nsala soup': {
        'aliases': ['nsala', 'nsala soup', 'white soup'],
        'category': 'soup',
        'description': '"White soup" (Eastern Nigeria)',
        'region': 'Eastern Nigeria',
        'keywords': ['nsala', 'white', 'soup']
    },
    'oha soup': {
        'aliases': ['oha', 'oha soup', 'ofe oha'],
        'category': 'soup',
        'description': 'Soup made with oha leaves and cocoyam',
        'region': 'Eastern Nigeria',
        'keywords': ['oha', 'soup']
    },
    'afang soup': {
        'aliases': ['afang', 'afang soup', 'waterleaf soup'],
        'category': 'soup',
        'description': 'Soup made with waterleaf and pumpkin seeds',
        'region': 'Cross River/Akwa Ibom',
        'keywords': ['afang', 'waterleaf', 'soup']
    },
    'edikang ikong': {
        'aliases': ['edikang ikong', 'edikang', 'ikong'],
        'category': 'soup',
        'description': 'Vegetable soup with meat and seafood',
        'region': 'Cross River/Akwa Ibom',
        'keywords': ['edikang', 'ikong', 'soup']
    },
    'bitter leaf soup': {
        'aliases': ['bitter leaf', 'bitter leaf soup', 'ofe onugbu'],
        'category': 'soup',
        'description': 'Soup made with bitter leaves and meat',
        'region': 'Igbo traditional',
        'keywords': ['bitter', 'leaf', 'soup', 'onugbu']
    },
    'banga soup': {
        'aliases': ['banga', 'banga soup', 'palm nut soup'],
        'category': 'soup',
        'description': 'Palm nut soup',
        'region': 'Niger Delta',
        'keywords': ['banga', 'palm', 'nut', 'soup']
    },
    'okra soup': {
        'aliases': ['okra', 'okra soup', 'slimy vegetable soup'],
        'category': 'soup',
        'description': 'Slimy vegetable soup, common nationwide',
        'region': 'nationwide',
        'keywords': ['okra', 'soup']
    },
    'ewedu soup': {
        'aliases': ['ewedu', 'ewedu soup', 'jute leaf soup'],
        'category': 'soup',
        'description': 'Jute leaf soup',
        'region': 'Yoruba',
        'keywords': ['ewedu', 'jute', 'leaf', 'soup']
    },
    'gbegiri soup': {
        'aliases': ['gbegiri', 'gbegiri soup', 'bean soup'],
        'category': 'soup',
        'description': 'Bean soup, often served with ewedu',
        'region': 'Yoruba',
        'keywords': ['gbegiri', 'bean', 'soup']
    },
    'pepper soup': {
        'aliases': ['pepper soup', 'pepper', 'spicy soup', 'ukodo'],
        'category': 'soup',
        'description': 'Watery, spicy soup with fish, chicken, or goat meat',
        'region': 'nationwide',
        'keywords': ['pepper', 'soup', 'spicy', 'ukodo']
    },

    # Swallows/Staples
    'eba': {
        'aliases': ['eba', 'gari', 'cassava'],
        'category': 'staple',
        'description': 'Cassava-based staple food, smooth and dough-like',
        'region': 'nationwide',
        'keywords': ['eba', 'gari', 'cassava']
    },
    'fufu': {
        'aliases': ['fufu', 'pounded yam', 'plantain fufu'],
        'category': 'staple',
        'description': 'Pounded yam or plantain, smooth and stretchy',
        'region': 'nationwide',
        'keywords': ['fufu', 'pounded', 'yam']
    },
    'pounded yam': {
        'aliases': ['pounded yam', 'fufu', 'iyan', 'yam'],
        'category': 'staple',
        'description': 'Boiled and pounded yam, creamy texture',
        'region': 'nationwide',
        'keywords': ['pounded', 'yam', 'iyan', 'fufu']
    },
    'amala': {
        'aliases': ['amala', 'yam flour'],
        'category': 'staple',
        'description': 'Yam flour-based staple, dark and smooth',
        'region': 'Yoruba',
        'keywords': ['amala', 'yam', 'flour']
    },
    'semovita': {
        'aliases': ['semovita', 'semolina'],
        'category': 'staple',
        'description': 'Semolina-based staple, light and fluffy',
        'region': 'nationwide',
        'keywords': ['semovita', 'semolina']
    },
    'tuwo shinkafa': {
        'aliases': ['tuwo shinkafa', 'tuwo', 'rice swallow'],
        'category': 'staple',
        'description': 'Rice swallow',
        'region': 'Northern Nigeria',
        'keywords': ['tuwo', 'shinkafa', 'rice', 'swallow']
    },
    'tuwo masara': {
        'aliases': ['tuwo masara', 'maize swallow'],
        'category': 'staple',
        'description': 'Maize swallow',
        'region': 'Northern Nigeria',
        'keywords': ['tuwo', 'masara', 'maize', 'swallow']
    },

    # Rice & Grain Dishes
    'jollof rice': {
        'aliases': ['jollof rice', 'jollof', 'rice', 'jellof', 'jellofrice'],
        'category': 'rice',
        'description': 'Aromatic rice cooked in tomato sauce with spices, nationwide favorite',
        'region': 'nationwide',
        'keywords': ['jollof', 'rice', 'tomato', 'jellof']
    },
    'fried rice': {
        'aliases': ['fried rice', 'rice'],
        'category': 'rice',
        'description': 'Rice stir-fried with vegetables and meat',
        'region': 'nationwide',
        'keywords': ['fried', 'rice']
    },
    'ofada rice': {
        'aliases': ['ofada rice', 'ofada', 'local rice'],
        'category': 'rice',
        'description': 'Local Nigerian rice variety served with Ayamase sauce',
        'region': 'Yoruba',
        'keywords': ['ofada', 'rice', 'local']
    },
    'coconut rice': {
        'aliases': ['coconut rice', 'rice'],
        'category': 'rice',
        'description': 'Rice cooked with coconut milk',
        'region': 'coastal regions',
        'keywords': ['coconut', 'rice']
    },

    # Snacks & Street Foods
    'akara': {
        'aliases': ['akara', 'bean cake', 'fried bean', 'kose'],
        'category': 'snack',
        'description': 'Deep-fried bean cakes, crispy outside, soft inside',
        'region': 'nationwide',
        'keywords': ['akara', 'bean', 'cake', 'fried', 'kose']
    },
    'moi moi': {
        'aliases': ['moi moi', 'moyi moyi', 'bean pudding'],
        'category': 'snack',
        'description': 'Steamed bean pudding with spices and meat',
        'region': 'nationwide',
        'keywords': ['moi', 'moyi', 'bean', 'pudding']
    },
    'suya': {
        'aliases': ['suya', 'grilled meat', 'meat skewer'],
        'category': 'protein',
        'description': 'Spicy grilled meat skewers',
        'region': 'Northern Nigeria',
        'keywords': ['suya', 'grilled', 'meat', 'spiced']
    },
    'kilishi': {
        'aliases': ['kilishi', 'dried meat', 'jerky'],
        'category': 'protein',
        'description': 'Dried and spiced meat strips',
        'region': 'Northern Nigeria',
        'keywords': ['kilishi', 'dried', 'meat']
    },
    'chin chin': {
        'aliases': ['chin chin', 'chinchin'],
        'category': 'snack',
        'description': 'Crispy fried snack made from flour',
        'region': 'nationwide',
        'keywords': ['chin', 'chinchin', 'snack']
    },
    'plantain chips': {
        'aliases': ['plantain chips', 'fried plantain', 'boli', 'plantain'],
        'category': 'snack',
        'description': 'Fried plantain slices, crispy and golden',
        'region': 'nationwide',
        'keywords': ['plantain', 'chips', 'fried', 'boli']
    },
    'puff puff': {
        'aliases': ['puff puff', 'puffpuff', 'fried dough'],
        'category': 'snack',
        'description': 'Fried dough balls',
        'region': 'nationwide',
        'keywords': ['puff', 'puffpuff', 'dough', 'fried']
    },
    'goat meat skewers': {
        'aliases': ['goat meat skewers', 'goat meat', 'street food'],
        'category': 'protein',
        'description': 'Grilled goat meat skewers, street favorite',
        'region': 'nationwide',
        'keywords': ['goat', 'meat', 'skewers', 'grilled']
    },

    # Protein & Special Dishes
    'nkwobi': {
        'aliases': ['nkwobi', 'cow foot delicacy'],
        'category': 'specialty',
        'description': 'Cow foot delicacy',
        'region': 'Eastern Nigeria',
        'keywords': ['nkwobi', 'cow', 'foot', 'delicacy']
    },
    'isi ewu': {
        'aliases': ['isi ewu', 'goat head dish'],
        'category': 'specialty',
        'description': 'Goat head dish',
        'region': 'Yoruba',
        'keywords': ['isi', 'ewu', 'goat', 'head']
    },
    'asun': {
        'aliases': ['asun', 'spicy grilled goat meat'],
        'category': 'protein',
        'description': 'Spicy grilled goat meat',
        'region': 'Yoruba',
        'keywords': ['asun', 'spicy', 'grilled', 'goat', 'meat']
    },
    'peppered snail': {
        'aliases': ['peppered snail', 'snail', 'street delicacy'],
        'category': 'protein',
        'description': 'Spicy snail dish, street delicacy',
        'region': 'nationwide',
        'keywords': ['peppered', 'snail', 'street', 'delicacy']
    },
    'fried fish': {
        'aliases': ['fried fish', 'fish'],
        'category': 'protein',
        'description': 'Fried fish, common in parties',
        'region': 'nationwide',
        'keywords': ['fried', 'fish']
    },
    'fried chicken': {
        'aliases': ['fried chicken', 'chicken'],
        'category': 'protein',
        'description': 'Fried chicken, common in parties',
        'region': 'nationwide',
        'keywords': ['fried', 'chicken']
    },

    # Stews
    'tomato stew': {
        'aliases': ['tomato stew', 'stew'],
        'category': 'stew',
        'description': 'Tomato-based stew with meat and spices',
        'region': 'nationwide',
        'keywords': ['tomato', 'stew']
    },
    'groundnut stew': {
        'aliases': ['groundnut stew', 'peanut stew', 'groundnut'],
        'category': 'stew',
        'description': 'Peanut-based stew with meat',
        'region': 'nationwide',
        'keywords': ['groundnut', 'peanut', 'stew']
    },

    # Beverages
    'zobo': {
        'aliases': ['zobo', 'hibiscus drink', 'sorrel drink'],
        'category': 'beverage',
        'description': 'Hibiscus drink',
        'region': 'nationwide',
        'keywords': ['zobo', 'hibiscus', 'sorrel', 'drink']
    },
    'kunu': {
        'aliases': ['kunu', 'millet drink', 'sorghum drink'],
        'category': 'beverage',
        'description': 'Millet or sorghum-based drink',
        'region': 'nationwide',
        'keywords': ['kunu', 'millet', 'sorghum', 'drink']
    },
    'palm wine': {
        'aliases': ['palm wine', 'wine'],
        'category': 'beverage',
        'description': 'Natural alcoholic drink from palm trees',
        'region': 'nationwide',
        'keywords': ['palm', 'wine', 'alcoholic']
    },
    'fura da nono': {
        'aliases': ['fura da nono', 'fura', 'fermented milk'],
        'category': 'beverage',
        'description': 'Fermented milk with millet',
        'region': 'Northern Nigeria',
        'keywords': ['fura', 'da', 'nono', 'fermented', 'milk', 'millet']
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


def get_dishes_by_region(region: str) -> List[str]:
    """Get Nigerian dishes by region"""
    return [
        dish_name for dish_name, info in NIGERIAN_DISHES.items()
        if info.get('region', '').lower() == region.lower()
    ]


# System prompt for LLM with comprehensive Nigerian dishes context
NIGERIAN_DISHES_SYSTEM_PROMPT = """You are a helpful food delivery assistant for a Nigerian food delivery service.

You are familiar with Nigerian dishes and cuisine. Here are some common Nigerian dishes:

SOUPS & STEWS:
- Egusi Soup: Melon seed soup, eaten across Nigeria
- Ogbono Soup: Wild mango seed soup
- Nsala Soup: "White soup" (Eastern Nigeria)
- Oha Soup: Made with oha leaves and cocoyam (Eastern Nigeria)
- Afang Soup: Made with waterleaf and pumpkin seeds (Cross River/Akwa Ibom)
- Edikang Ikong: Vegetable soup with meat and seafood (Cross River/Akwa Ibom)
- Bitter Leaf Soup: Made with bitter leaves and meat (Igbo traditional)
- Banga Soup: Palm nut soup (Niger Delta)
- Okra Soup: Slimy vegetable soup, common nationwide
- Ewedu Soup: Jute leaf soup (Yoruba)
- Gbegiri Soup: Bean soup, often served with ewedu (Yoruba)
- Pepper Soup: Watery, spicy soup with fish, chicken, or goat meat (nationwide)

SWALLOWS/STAPLES:
- Eba: Cassava-based staple, smooth and dough-like
- Fufu/Pounded Yam: Boiled and pounded yam, creamy
- Amala: Yam flour-based staple (Yoruba)
- Semovita: Semolina-based staple
- Tuwo Shinkafa: Rice swallow (Northern Nigeria)
- Tuwo Masara: Maize swallow (Northern Nigeria)

RICE & GRAIN DISHES:
- Jollof Rice: Aromatic rice in tomato sauce, nationwide favorite
- Fried Rice: Stir-fried rice with vegetables and meat
- Ofada Rice: Local rice served with Ayamase sauce (Yoruba)
- Coconut Rice: Rice cooked with coconut milk (coastal regions)

SNACKS & STREET FOODS:
- Akara: Deep-fried bean cakes
- Moi Moi: Steamed bean pudding
- Suya: Spicy grilled meat skewers (Northern Nigeria)
- Kilishi: Dried and spiced meat strips (Northern Nigeria)
- Chin Chin: Crispy fried snack made from flour
- Plantain Chips: Fried plantain slices
- Puff Puff: Fried dough balls
- Goat Meat Skewers: Street favorite

PROTEIN & SPECIAL DISHES:
- Nkwobi: Cow foot delicacy (Eastern Nigeria)
- Isi Ewu: Goat head dish (Yoruba)
- Asun: Spicy grilled goat meat (Yoruba)
- Peppered Snail: Street delicacy
- Fried Fish & Chicken: Common in parties

BEVERAGES:
- Zobo: Hibiscus drink
- Kunu: Millet or sorghum-based drink
- Palm Wine: Natural alcoholic drink
- Fura da Nono: Fermented milk with millet (Northern Nigeria)

When a user mentions any Nigerian dish, you should:
1. Recognize it immediately
2. Search for vendors serving that dish
3. Show available options
4. Help them place an order
5. NOT explain what the dish is (they already know)
6. Go straight to ordering

Be concise and action-oriented. Focus on helping them order, not explaining."""