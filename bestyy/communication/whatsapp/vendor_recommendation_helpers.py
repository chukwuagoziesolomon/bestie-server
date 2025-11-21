"""
Add these functions to bestyy/communication/whatsapp/views.py at the end
"""

def _handle_vendor_recommendation(dish_name: str, vendor_name: str, conversation, phone_number: str, meta_service, user=None):
    """
    Handle vendor recommendation with featured priority
    """
    from .vendor_recommendation_service import VendorRecommendationService
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize recommendation service
        recommender = VendorRecommendationService(user=user)
        
        # Search for vendors
        result = recommender.search_vendors_for_dish(
            dish_name=dish_name,
            preferred_vendor_name=vendor_name if vendor_name else None,
            page=1
        )
        
        # Cache the search results for pagination
        if result['total_vendors'] > 0:
            conversation.context_data = conversation.context_data or {}
            conversation.context_data['vendor_search'] = {
                'dish_name': dish_name,
                'preferred_vendor': vendor_name,
                'current_page': 1,
                'total_vendors': result['total_vendors']
            }
            conversation.context_data['vendor_selection_active'] = True
            conversation.context_data['vendor_options'] = [
                {
                    'vendor_id': v['vendor_id'],
                    'product_id': v['product_id'],
                    'vendor_name': v['vendor_name'],
                    'product_name': v['product_name'],
                    'price': str(v['price'])
                }
                for v in result['recommended_vendors']
            ]
            conversation.save()
            
            logger.info(f"Stored {len(result['recommended_vendors'])} vendor options for {dish_name}")
        
        return result['message']
        
    except Exception as e:
        logger.error(f"Error in vendor recommendation: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I had trouble finding vendors for {dish_name}. Please try again!"


def _handle_more_vendors(conversation, phone_number: str, meta_service):
    """Handle MORE pagination for vendor recommendations"""
    from .vendor_recommendation_service import VendorRecommendationService
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        vendor_search = conversation.context_data.get('vendor_search')
        if not vendor_search:
            return None
        
        # Get next page
        current_page = vendor_search.get('current_page', 1)
        next_page = current_page + 1
        
        recommender = VendorRecommendationService(user=conversation.user)
        result = recommender.search_vendors_for_dish(
            dish_name=vendor_search['dish_name'],
            preferred_vendor_name=vendor_search.get('preferred_vendor'),
            page=next_page
        )
        
        if result['recommended_vendors']:
            # Update page number and options
            conversation.context_data['vendor_search']['current_page'] = next_page
            conversation.context_data['vendor_options'] = [
                {
                    'vendor_id': v['vendor_id'],
                    'product_id': v['product_id'],
                    'vendor_name': v['vendor_name'],
                    'product_name': v['product_name'],
                    'price': str(v['price'])
                }
                for v in result['recommended_vendors']
            ]
            conversation.save()
            
            logger.info(f"Showing page {next_page} of vendor results")
            return result['message']
        else:
            return "That's all the vendors we have! Reply with a number to select from the current page."
        
    except Exception as e:
        logger.error(f"Error handling MORE vendors: {str(e)}")
        return None


def _handle_vendor_selection(selection_number: int, conversation, phone_number: str, meta_service, user=None):
    """Handle vendor selection by number"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        vendor_options = conversation.context_data.get('vendor_options', [])
        
        if not vendor_options:
            return None
        
        # Adjust for 1-based indexing
        if selection_number < 1 or selection_number > len(vendor_options):
            return f"Please select a number between 1 and {len(vendor_options)}"
        
        selected_vendor = vendor_options[selection_number - 1]
        
        # Store the selected dish for order creation
        conversation.context_data['pending_dish'] = {
            'product_id': selected_vendor['product_id'],
            'dish_name': selected_vendor['product_name'],
            'price': selected_vendor['price'],
            'vendor_id': selected_vendor['vendor_id'],
            'vendor_name': selected_vendor['vendor_name']
        }
        
        # Clear vendor selection state
        conversation.context_data.pop('vendor_selection_active', None)
        conversation.context_data.pop('vendor_options', None)
        conversation.context_data.pop('vendor_search', None)
        conversation.save()
        
        logger.info(f"User selected vendor {selected_vendor['vendor_name']} for {selected_vendor['product_name']}")
        
        # Return confirmation message
        message = f"✅ Great choice!\n\n"
        message += f"🏪 *{selected_vendor['vendor_name']}*\n"
        message += f"🍽️ {selected_vendor['product_name']} - ₦{float(selected_vendor['price']):,.0f}\n\n"
        message += f"Would you like to confirm this order?\n\n"
        message += f"💬 Reply:\n"
        message += f"• *YES* - Confirm and proceed\n"
        message += f"• *NO* - Choose another dish"
        
        return message
        
    except Exception as e:
        logger.error(f"Error handling vendor selection: {str(e)}")
        import traceback
        traceback.print_exc()
        return "Sorry, there was an error processing your selection. Please try again!"


def _extract_vendor_and_dish(content: str):
    """
    Extract vendor name and dish name from message
    Examples:
    - "I want jollof rice from Ntachi" -> ("jollof rice", "Ntachi")
    - "Order jollof rice" -> ("jollof rice", None)
    - "Get me suya from Mama's Kitchen" -> ("suya", "Mama's Kitchen")
    """
    import re
    
    content_lower = content.lower()
    
    # Pattern: "dish from vendor"
    pattern1 = r'(?:i want|order|get me|give me)\s+(.+?)\s+from\s+(.+?)(?:\.|$|please|pls)'
    match1 = re.search(pattern1, content_lower)
    if match1:
        dish = match1.group(1).strip()
        vendor = match1.group(2).strip()
        return (dish, vendor)
    
    # Pattern: "vendor's dish" (e.g., "Ntachi's jollof rice")
    pattern2 = r"(.+?)(?:'s|s)\s+(.+?)(?:\.|$|please|pls)"
    match2 = re.search(pattern2, content_lower)
    if match2:
        vendor = match2.group(1).strip()
        dish = match2.group(2).strip()
        return (dish, vendor)
    
    # Pattern: Just the dish (no vendor specified)
    pattern3 = r'(?:i want|order|get me|give me)\s+(.+?)(?:\.|$|please|pls|from)'
    match3 = re.search(pattern3, content_lower)
    if match3:
        dish = match3.group(1).strip()
        return (dish, None)
    
    # Fallback: entire content as dish name
    return (content.strip(), None)
