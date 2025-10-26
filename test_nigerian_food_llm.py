#!/usr/bin/env python3
"""
Test script to verify LLM categorization of Nigerian dishes and food requests
"""
import os
import sys
import requests
import json

# Direct test without Django setup - just test the LLM API call

def test_llm_categorization_direct():
    """Test LLM categorization directly with OpenRouter API"""

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return

    openrouter_base_url = "https://openrouter.ai/api/v1"

    # Test cases for Nigerian foods
    test_cases = [
        # Nigerian dishes
        ("i want egusi soup", "nigerian_food_request"),
        ("i want egwusi soup", "nigerian_food_request"),  # Alternative spelling
        ("can i get jollof rice", "nigerian_food_request"),
        ("i need pounded yam", "nigerian_food_request"),
        ("bring me efo riro", "nigerian_food_request"),
        ("i want afang soup", "nigerian_food_request"),
        ("give me okra soup", "nigerian_food_request"),
        ("i need moi moi", "nigerian_food_request"),
        ("can i get akara", "nigerian_food_request"),
        ("i want suya", "nigerian_food_request"),
        ("bring me kilishi", "nigerian_food_request"),
        ("i need fufu", "nigerian_food_request"),
        ("can i get semovita", "nigerian_food_request"),
        ("i want amala", "nigerian_food_request"),
        ("give me eba", "nigerian_food_request"),

        # International foods
        ("i want pizza", "specific_food_request"),
        ("can i get burger", "specific_food_request"),
        ("i need chicken", "specific_food_request"),

        # General requests
        ("hello", "greeting"),
        ("how are you", "greeting"),
        ("where is my order", "delivery_status"),
        ("i have a complaint", "complaint"),
    ]

    print("Testing LLM Categorization for Nigerian Foods (Direct API)")
    print("=" * 70)

    results = []

    for message, expected_category in test_cases:
        try:
            print(f"\nTesting: '{message}'")
            print(f"Expected: {expected_category}")

            # Make direct API call
            response = requests.post(
                url=f"{openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://bestyy.com",
                    "X-Title": "Bestyy LLM Test",
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.3-8b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a message categorization assistant for a Nigerian food delivery service called Bestyy.
We serve both international and traditional Nigerian cuisine.

Categorize the user's message into one of these categories:
- greeting: Simple greetings like 'hi', 'hello', 'good morning'
- order_inquiry: Questions about ordering, placing orders, how to order
- menu_request: Requests to see menu, what food is available, dish inquiries
- delivery_status: Questions about delivery time, where is my order, tracking
- payment_help: Questions about payment, pricing, billing, costs
- complaint: Negative feedback, problems, issues, dissatisfaction
- general_info: General questions about the service, business info
- food_recommendation: Requests for food suggestions or recommendations
- specific_food_request: Requests for specific food types (pizza, burger, chicken, rice, pasta, etc.)
- nigerian_food_request: Requests for Nigerian dishes (egusi soup, jollof rice, pounded yam, efo riro, afang soup, okra soup, moi moi, akara, suya, kilishi, fufu, semovita, amala, eba, etc.)

IMPORTANT: Always respond with ONLY the category name, nothing else.
If you're unsure, choose the most appropriate category from the list above.
Pay special attention to Nigerian food names and local delicacies."""
                        },
                        {
                            "role": "user",
                            "content": f"Categorize this message: '{message}'"
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 20
                }),
                timeout=15
            )

            if response.status_code == 200:
                response_data = response.json()
                category = response_data['choices'][0]['message']['content'].strip().lower()

                # Validate the category
                valid_categories = [
                    'greeting', 'order_inquiry', 'menu_request', 'delivery_status',
                    'payment_help', 'complaint', 'general_info', 'food_recommendation',
                    'specific_food_request', 'nigerian_food_request'
                ]

                if category in valid_categories:
                    if category == expected_category:
                        print(f"Correct: {category}")
                        results.append((message, expected_category, category, True))
                    else:
                        print(f"Wrong: Got '{category}' instead of '{expected_category}'")
                        results.append((message, expected_category, category, False))
                else:
                    print(f"Invalid category: '{category}' (not in valid list)")
                    results.append((message, expected_category, f"INVALID: {category}", False))
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                results.append((message, expected_category, f"API_ERROR: {response.status_code}", False))

        except Exception as e:
            print(f"Error: {str(e)}")
            results.append((message, expected_category, f"ERROR: {str(e)}", False))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    correct = sum(1 for _, _, _, success in results if success)
    total = len(results)

    print(f"Total Tests: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {correct/total*100:.1f}%")

    # Show failures
    failures = [(msg, exp, got) for msg, exp, got, success in results if not success]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for msg, exp, got in failures:
            print(f"  '{msg}' -> Expected: {exp}, Got: {got}")

    return results

if __name__ == "__main__":
    test_llm_categorization_direct()