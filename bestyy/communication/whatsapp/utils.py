import re


def looks_like_address(text):
    """Check if the text looks like a delivery address"""
    text_lower = text.lower().strip()

    # Skip if it's clearly a command or food order
    command_words = ['yes', 'no', 'done', 'more', 'confirm', 'cancel', 'help', 'menu', 'order', 'i want', 'give me', 'can i get', 'save']
    if any(text_lower.startswith(word) for word in command_words):
        return False

    # Skip if it's clearly a food order
    food_words = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 'vegetarian', 'vegan', 'jollof', 'shawarma', 'suya']
    if any(food in text_lower for food in food_words):
        return False

    # Check for Nigerian cities and locations (expanded list)
    nigerian_locations = [
        'lagos', 'abuja', 'port harcourt', 'kano', 'ibadan', 'benin', 'enugu',
        'ikeja', 'lekki', 'vi', 'victoria island', 'surulere', 'yaba', 'ojota',
        'maryland', 'ikorodu', 'ajah', 'berger', 'ogba', 'ilupeju', 'jibowu',
        'gariki', 'garikki', 'onwe', 'close', 'island', 'mainland', 'phase',
        'estate', 'gardens', 'crescent', 'avenue', 'street', 'road', 'drive',
        'lane', 'way', 'boulevard', 'expressway', 'highway', 'area', 'layout',
        'block', 'flat', 'apartment', 'house', 'plot', 'no', 'number'
    ]

    # Check for address indicators (expanded)
    address_indicators = [
        'street', 'road', 'avenue', 'close', 'drive', 'lane', 'way', 'estate',
        'plot', 'house', 'flat', 'apartment', 'block', 'phase', 'layout',
        'gardens', 'crescent', 'boulevard', 'expressway', 'highway',
        'no', 'number', 'area', 'phase', 'estate', 'gardens', 'island', 'mainland'
    ]

    # Check if text contains location or address-like words
    has_location = any(location in text_lower for location in nigerian_locations)
    has_address_indicator = any(indicator in text_lower for indicator in address_indicators)

    # Check for numbers (house/plot numbers)
    has_numbers = bool(re.search(r'\d+', text))

    # Check length (addresses are usually longer than commands)
    reasonable_length = len(text.split()) >= 2

    # More restrictive logic when not explicitly awaiting address
    # Require at least 2 of: location, address indicator, numbers, or comma-separated format
    has_commas = ',' in text
    address_score = sum([
        has_location,
        has_address_indicator,
        has_numbers,
        has_commas and reasonable_length
    ])

    is_address = (
        (reasonable_length and address_score >= 2) or  # At least 2 address indicators
        (has_numbers and (has_location or has_address_indicator)) or  # Numbers + location/indicator
        (len(text.split()) >= 4 and has_commas)  # Very structured long text
    )

    print(f"DEBUG: Address detection for '{text}' - score: {address_score}, has_location: {has_location}, has_address_indicator: {has_address_indicator}, has_numbers: {has_numbers}, reasonable_length: {reasonable_length}, has_commas: {has_commas}, is_address: {is_address}")

    return is_address