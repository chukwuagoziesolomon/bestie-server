#!/usr/bin/env python3
"""
Simple in-memory conversation state manager for complaint handling
More reliable than Django cache for development/testing
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SimpleConversationStateManager:
    """
    Simple in-memory conversation state manager
    Reliable alternative to Django cache for development
    """
    _instance = None
    _states = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._timeout_minutes = 60  # 1 hour timeout
        return cls._instance
    
    def __init__(self):
        # This will only run once due to singleton pattern
        pass
    
    def set_complaint_state(self, phone_number: str, complaint_data: Dict[str, Any]):
        """Set complaint state for a user"""
        complaint_data['timestamp'] = datetime.now()
        self._states[phone_number] = complaint_data
        logger.info(f"Set complaint state for {phone_number}: {complaint_data.get('status')}")
    
    def get_complaint_state(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get complaint state for a user"""
        state = self._states.get(phone_number)
        
        if state:
            # Check if state has expired
            if self._is_state_expired(state):
                logger.info(f"Complaint state expired for {phone_number}")
                self._states.pop(phone_number, None)
                return None
            
            logger.info(f"Retrieved complaint state for {phone_number}: {state.get('status')}")
            return state
        
        logger.info(f"No complaint state found for {phone_number}")
        return None
    
    def clear_complaint_state(self, phone_number: str):
        """Clear complaint state when resolved"""
        if phone_number in self._states:
            self._states.pop(phone_number)
            logger.info(f"Cleared complaint state for {phone_number}")
    
    def is_expecting_order_details(self, phone_number: str) -> bool:
        """Check if we're waiting for order details from this user"""
        state = self.get_complaint_state(phone_number)
        is_expecting = state and state.get('status') == 'awaiting_order_details'
        logger.info(f"Is expecting order details for {phone_number}: {is_expecting}")
        return is_expecting
    
    def mark_awaiting_order_details(self, phone_number: str, complaint_type: str):
        """Mark that we're awaiting order details from user"""
        self.set_complaint_state(phone_number, {
            'status': 'awaiting_order_details',
            'complaint_type': complaint_type,
            'step': 1
        })
    
    def is_expecting_confirmation(self, phone_number: str) -> bool:
        """Check if we're waiting for user confirmation"""
        state = self.get_complaint_state(phone_number)
        is_expecting = state and state.get('status') == 'awaiting_confirmation'
        logger.info(f"Is expecting confirmation for {phone_number}: {is_expecting}")
        return is_expecting
    
    def mark_awaiting_confirmation(self, phone_number: str, action: str):
        """Mark that we're awaiting confirmation from user"""
        self.set_complaint_state(phone_number, {
            'status': 'awaiting_confirmation', 
            'action': action,
            'step': 2
        })
    
    def is_expecting_category_selection(self, phone_number: str) -> bool:
        """Check if we're waiting for problem category selection"""
        state = self.get_complaint_state(phone_number)
        is_expecting = state and state.get('status') == 'awaiting_category_selection'
        logger.info(f"Is expecting category selection for {phone_number}: {is_expecting}")
        return is_expecting
    
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
            'time_elapsed': self._calculate_time_elapsed(state.get('timestamp'))
        }
    
    def _is_state_expired(self, state: Dict[str, Any]) -> bool:
        """Check if conversation state has expired"""
        if 'timestamp' not in state:
            return True
        
        expiry_time = state['timestamp'] + timedelta(minutes=self._timeout_minutes)
        return datetime.now() > expiry_time
    
    def _calculate_time_elapsed(self, timestamp: datetime) -> int:
        """Calculate minutes elapsed since request"""
        try:
            if timestamp:
                return int((datetime.now() - timestamp).total_seconds() / 60)
        except:
            pass
        return 0