#!/usr/bin/env python3
"""
Enhanced WhatsApp conversation state manager for complaint handling
Tracks conversation context and manages multi-turn complaint resolution
"""
import logging
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WhatsAppConversationStateManager:
    """
    Manages conversation state for multi-turn complaint handling
    Tracks what information we've requested and received from users
    """
    
    def __init__(self):
        self.cache_prefix = "whatsapp_complaint_"
        self.cache_timeout = 3600  # 1 hour
    
    def set_complaint_state(self, phone_number: str, complaint_data: Dict[str, Any]):
        """Set complaint state for a user"""
        cache_key = f"{self.cache_prefix}{phone_number}"
        cache.set(cache_key, complaint_data, self.cache_timeout)
    
    def get_complaint_state(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get complaint state for a user"""
        cache_key = f"{self.cache_prefix}{phone_number}"
        return cache.get(cache_key)
    
    def clear_complaint_state(self, phone_number: str):
        """Clear complaint state when resolved"""
        cache_key = f"{self.cache_prefix}{phone_number}"
        cache.delete(cache_key)
    
    def is_expecting_order_details(self, phone_number: str) -> bool:
        """Check if we're waiting for order details from this user"""
        state = self.get_complaint_state(phone_number)
        return state and state.get('status') == 'awaiting_order_details'
    
    def mark_awaiting_order_details(self, phone_number: str, complaint_type: str):
        """Mark that we're awaiting order details from user"""
        self.set_complaint_state(phone_number, {
            'status': 'awaiting_order_details',
            'complaint_type': complaint_type,
            'requested_at': timezone.now().isoformat(),
            'step': 1
        })
    
    def is_expecting_confirmation(self, phone_number: str) -> bool:
        """Check if we're waiting for user confirmation"""
        state = self.get_complaint_state(phone_number)
        return state and state.get('status') == 'awaiting_confirmation'
    
    def is_expecting_category_selection(self, phone_number: str) -> bool:
        """Check if we're waiting for problem category selection"""
        state = self.get_complaint_state(phone_number)
        return state and state.get('status') == 'awaiting_category_selection'
    
    def mark_awaiting_confirmation(self, phone_number: str, action: str):
        """Mark that we're awaiting confirmation from user"""
        self.set_complaint_state(phone_number, {
            'status': 'awaiting_confirmation', 
            'action': action,
            'requested_at': timezone.now().isoformat(),
            'step': 2
        })
    
    def get_conversation_context(self, phone_number: str) -> Dict[str, Any]:
        """Get full conversation context for intelligent responses"""
        state = self.get_complaint_state(phone_number)
        if not state:
            return {'is_new_conversation': True}
        
        return {
            'is_new_conversation': False,
            'complaint_in_progress': True,
            'current_status': state.get('status'),
            'complaint_type': state.get('complaint_type'),
            'step': state.get('step', 0),
            'time_elapsed': self._calculate_time_elapsed(state.get('requested_at'))
        }
    
    def _calculate_time_elapsed(self, requested_at_iso: str) -> int:
        """Calculate minutes elapsed since request"""
        try:
            requested_at = datetime.fromisoformat(requested_at_iso.replace('Z', '+00:00'))
            now = timezone.now()
            return int((now - requested_at).total_seconds() / 60)
        except:
            return 0