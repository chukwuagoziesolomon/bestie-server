"""
User Type Identification Service
Identifies whether a user is a customer, vendor, or courier
"""
import logging
from typing import Dict, Optional, Tuple
from django.contrib.auth.models import User
from django.utils import timezone
from ..models import VendorProfile, CourierProfile
from .ai_memory_service import AIMemoryService

logger = logging.getLogger(__name__)


class UserTypeIdentificationService:
    """
    Service for identifying user types (customer, vendor, courier)
    """
    
    def __init__(self):
        self.memory_service = AIMemoryService()
        
    def identify_user_type(self, 
                          user: User = None,
                          phone_number: str = None,
                          message: str = None,
                          session_id: str = None) -> Dict:
        """
        Identify user type using multiple methods
        
        Args:
            user: Django User object
            phone_number: Phone number to check
            message: Message content for analysis
            session_id: Session ID for context
            
        Returns:
            Dictionary with user type identification results
        """
        try:
            identification_results = {
                'user_type': 'unknown',
                'confidence': 0.0,
                'identification_method': 'none',
                'user_id': None,
                'profile_id': None,
                'phone_number': phone_number,
                'timestamp': timezone.now().isoformat()
            }
            
            # Method 1: Direct user object check
            if user:
                user_type_result = self._identify_from_user_object(user)
                if user_type_result['user_type'] != 'unknown':
                    identification_results.update(user_type_result)
                    identification_results['identification_method'] = 'user_object'
                    return identification_results
            
            # Method 2: Phone number lookup
            if phone_number:
                phone_result = self._identify_from_phone_number(phone_number)
                if phone_result['user_type'] != 'unknown':
                    identification_results.update(phone_result)
                    identification_results['identification_method'] = 'phone_lookup'
                    return identification_results
            
            # Method 3: Message content analysis
            if message:
                message_result = self._identify_from_message_content(message)
                if message_result['user_type'] != 'unknown':
                    identification_results.update(message_result)
                    identification_results['identification_method'] = 'message_analysis'
                    return identification_results
            
            # Method 4: Session context
            if session_id:
                session_result = self._identify_from_session_context(session_id)
                if session_result['user_type'] != 'unknown':
                    identification_results.update(session_result)
                    identification_results['identification_method'] = 'session_context'
                    return identification_results
            
            # Method 5: Memory-based identification
            memory_result = self._identify_from_memory(phone_number, message)
            if memory_result['user_type'] != 'unknown':
                identification_results.update(memory_result)
                identification_results['identification_method'] = 'memory_based'
                return identification_results
            
            return identification_results
            
        except Exception as e:
            logger.error(f"Error identifying user type: {str(e)}")
            return {
                'user_type': 'unknown',
                'confidence': 0.0,
                'identification_method': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def _identify_from_user_object(self, user: User) -> Dict:
        """
        Identify user type from Django User object
        """
        try:
            # Check if user has vendor profile
            try:
                vendor_profile = VendorProfile.objects.get(user=user)
                return {
                    'user_type': 'vendor',
                    'confidence': 1.0,
                    'user_id': user.id,
                    'profile_id': vendor_profile.id,
                    'phone_number': vendor_profile.phone_number,
                    'business_name': vendor_profile.business_name
                }
            except VendorProfile.DoesNotExist:
                pass
            
            # Check if user has courier profile
            try:
                courier_profile = CourierProfile.objects.get(user=user)
                return {
                    'user_type': 'courier',
                    'confidence': 1.0,
                    'user_id': user.id,
                    'profile_id': courier_profile.id,
                    'phone_number': courier_profile.phone_number,
                    'courier_name': f"{courier_profile.user.first_name} {courier_profile.user.last_name}".strip()
                }
            except CourierProfile.DoesNotExist:
                pass
            
            # If no profile found, assume customer
            return {
                'user_type': 'customer',
                'confidence': 0.8,
                'user_id': user.id,
                'profile_id': None,
                'phone_number': getattr(user, 'phone_number', None)
            }
            
        except Exception as e:
            logger.error(f"Error identifying from user object: {str(e)}")
            return {'user_type': 'unknown', 'confidence': 0.0}
    
    def _identify_from_phone_number(self, phone_number: str) -> Dict:
        """
        Identify user type from phone number
        """
        try:
            # Normalize phone number
            normalized_phone = self._normalize_phone_number(phone_number)
            
            # Check vendor profiles
            try:
                vendor_profile = VendorProfile.objects.get(phone_number=normalized_phone)
                return {
                    'user_type': 'vendor',
                    'confidence': 0.95,
                    'user_id': vendor_profile.user.id,
                    'profile_id': vendor_profile.id,
                    'phone_number': normalized_phone,
                    'business_name': vendor_profile.business_name
                }
            except VendorProfile.DoesNotExist:
                pass
            
            # Check courier profiles
            try:
                courier_profile = CourierProfile.objects.get(phone_number=normalized_phone)
                return {
                    'user_type': 'courier',
                    'confidence': 0.95,
                    'user_id': courier_profile.user.id,
                    'profile_id': courier_profile.id,
                    'phone_number': normalized_phone,
                    'courier_name': f"{courier_profile.user.first_name} {courier_profile.user.last_name}".strip()
                }
            except CourierProfile.DoesNotExist:
                pass
            
            # Check if phone number exists in user records
            try:
                user = User.objects.get(phone_number=normalized_phone)
                return {
                    'user_type': 'customer',
                    'confidence': 0.7,
                    'user_id': user.id,
                    'profile_id': None,
                    'phone_number': normalized_phone
                }
            except User.DoesNotExist:
                pass
            
            return {'user_type': 'unknown', 'confidence': 0.0}
            
        except Exception as e:
            logger.error(f"Error identifying from phone number: {str(e)}")
            return {'user_type': 'unknown', 'confidence': 0.0}
    
    def _identify_from_message_content(self, message: str) -> Dict:
        """
        Identify user type from message content analysis
        """
        try:
            message_lower = message.lower()
            
            # Vendor-specific keywords
            vendor_keywords = [
                'order ready', 'preparing', 'cooking', 'kitchen', 'restaurant',
                'business', 'menu', 'ingredient', 'equipment', 'staff',
                'vendor', 'restaurant owner', 'chef', 'cook'
            ]
            
            # Courier-specific keywords
            courier_keywords = [
                'picked up', 'delivery', 'on the way', 'arrived', 'delivered',
                'courier', 'driver', 'bike', 'motorcycle', 'vehicle',
                'traffic', 'location', 'address', 'customer location'
            ]
            
            # Customer-specific keywords
            customer_keywords = [
                'where is my order', 'delivery time', 'order status',
                'customer', 'hungry', 'food', 'meal', 'order',
                'delivery address', 'payment', 'refund', 'cancel'
            ]
            
            # Count keyword matches
            vendor_score = sum(1 for keyword in vendor_keywords if keyword in message_lower)
            courier_score = sum(1 for keyword in courier_keywords if keyword in message_lower)
            customer_score = sum(1 for keyword in customer_keywords if keyword in message_lower)
            
            # Determine user type based on highest score
            max_score = max(vendor_score, courier_score, customer_score)
            
            if max_score == 0:
                return {'user_type': 'unknown', 'confidence': 0.0}
            
            if vendor_score == max_score:
                confidence = min(0.8, vendor_score * 0.2)
                return {
                    'user_type': 'vendor',
                    'confidence': confidence,
                    'user_id': None,
                    'profile_id': None,
                    'phone_number': None,
                    'message_analysis': {
                        'vendor_score': vendor_score,
                        'courier_score': courier_score,
                        'customer_score': customer_score
                    }
                }
            elif courier_score == max_score:
                confidence = min(0.8, courier_score * 0.2)
                return {
                    'user_type': 'courier',
                    'confidence': confidence,
                    'user_id': None,
                    'profile_id': None,
                    'phone_number': None,
                    'message_analysis': {
                        'vendor_score': vendor_score,
                        'courier_score': courier_score,
                        'customer_score': customer_score
                    }
                }
            else:
                confidence = min(0.8, customer_score * 0.2)
                return {
                    'user_type': 'customer',
                    'confidence': confidence,
                    'user_id': None,
                    'profile_id': None,
                    'phone_number': None,
                    'message_analysis': {
                        'vendor_score': vendor_score,
                        'courier_score': courier_score,
                        'customer_score': customer_score
                    }
                }
            
        except Exception as e:
            logger.error(f"Error identifying from message content: {str(e)}")
            return {'user_type': 'unknown', 'confidence': 0.0}
    
    def _identify_from_session_context(self, session_id: str) -> Dict:
        """
        Identify user type from session context
        """
        try:
            # Get recent memories for this session
            recent_memories = self.memory_service.retrieve_episodic_memories(
                query=f"session {session_id}",
                limit=10
            )
            
            if not recent_memories:
                return {'user_type': 'unknown', 'confidence': 0.0}
            
            # Analyze memory types
            memory_types = {}
            for memory in recent_memories:
                memory_type = memory.get('memory_type', 'unknown')
                memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
            
            # Determine user type based on memory types
            if memory_types.get('vendor_interaction', 0) > memory_types.get('courier_interaction', 0):
                if memory_types.get('vendor_interaction', 0) > memory_types.get('support_interaction', 0):
                    return {
                        'user_type': 'vendor',
                        'confidence': 0.7,
                        'user_id': None,
                        'profile_id': None,
                        'phone_number': None,
                        'session_analysis': memory_types
                    }
            
            if memory_types.get('courier_interaction', 0) > memory_types.get('vendor_interaction', 0):
                if memory_types.get('courier_interaction', 0) > memory_types.get('support_interaction', 0):
                    return {
                        'user_type': 'courier',
                        'confidence': 0.7,
                        'user_id': None,
                        'profile_id': None,
                        'phone_number': None,
                        'session_analysis': memory_types
                    }
            
            if memory_types.get('support_interaction', 0) > 0:
                return {
                    'user_type': 'customer',
                    'confidence': 0.6,
                    'user_id': None,
                    'profile_id': None,
                    'phone_number': None,
                    'session_analysis': memory_types
                }
            
            return {'user_type': 'unknown', 'confidence': 0.0}
            
        except Exception as e:
            logger.error(f"Error identifying from session context: {str(e)}")
            return {'user_type': 'unknown', 'confidence': 0.0}
    
    def _identify_from_memory(self, phone_number: str = None, message: str = None) -> Dict:
        """
        Identify user type from memory patterns
        """
        try:
            # Search for patterns in memory
            search_queries = []
            
            if phone_number:
                search_queries.append(phone_number)
            
            if message:
                search_queries.append(message[:50])  # First 50 characters
            
            if not search_queries:
                return {'user_type': 'unknown', 'confidence': 0.0}
            
            # Search memories
            all_memories = []
            for query in search_queries:
                memories = self.memory_service.retrieve_episodic_memories(
                    query=query,
                    limit=5
                )
                all_memories.extend(memories)
            
            if not all_memories:
                return {'user_type': 'unknown', 'confidence': 0.0}
            
            # Analyze memory patterns
            user_type_counts = {}
            for memory in all_memories:
                memory_type = memory.get('memory_type', 'unknown')
                if memory_type in ['vendor_interaction', 'courier_interaction', 'support_interaction']:
                    user_type = memory_type.replace('_interaction', '')
                    user_type_counts[user_type] = user_type_counts.get(user_type, 0) + 1
            
            if not user_type_counts:
                return {'user_type': 'unknown', 'confidence': 0.0}
            
            # Get most common user type
            most_common_type = max(user_type_counts, key=user_type_counts.get)
            confidence = min(0.8, user_type_counts[most_common_type] * 0.2)
            
            return {
                'user_type': most_common_type,
                'confidence': confidence,
                'user_id': None,
                'profile_id': None,
                'phone_number': phone_number,
                'memory_analysis': user_type_counts
            }
            
        except Exception as e:
            logger.error(f"Error identifying from memory: {str(e)}")
            return {'user_type': 'unknown', 'confidence': 0.0}
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """
        Normalize phone number format
        """
        try:
            # Remove all non-digit characters
            digits_only = ''.join(filter(str.isdigit, phone_number))
            
            # Handle different formats
            if digits_only.startswith('234'):
                # Nigerian format: 2348123456789
                return f"+{digits_only}"
            elif digits_only.startswith('081'):
                # Nigerian format: 08123456789
                return f"+234{digits_only[1:]}"
            elif digits_only.startswith('812'):
                # Nigerian format: 8123456789
                return f"+234{digits_only}"
            elif len(digits_only) == 10:
                # Assume Nigerian format
                return f"+234{digits_only}"
            else:
                # Return as is
                return f"+{digits_only}"
                
        except Exception as e:
            logger.error(f"Error normalizing phone number: {str(e)}")
            return phone_number
    
    def store_user_type_identification(self, 
                                     identification_result: Dict,
                                     phone_number: str = None,
                                     message: str = None) -> str:
        """
        Store user type identification as episodic memory
        """
        try:
            memory_id = self.memory_service.store_episodic_memory(
                memory_type='system_event',
                title=f"User Type Identification: {identification_result['user_type']}",
                description=f"Identified user as {identification_result['user_type']} with {identification_result['confidence']} confidence",
                content={
                    'identification_result': identification_result,
                    'phone_number': phone_number,
                    'message': message,
                    'identification_timestamp': timezone.now().isoformat()
                },
                importance_score=0.6,
                tags=['user_identification', identification_result['user_type']]
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing user type identification: {str(e)}")
            return None
    
    def get_user_type_statistics(self) -> Dict:
        """
        Get statistics about user type identifications
        """
        try:
            # Get recent identifications
            recent_memories = self.memory_service.retrieve_episodic_memories(
                query="user type identification",
                limit=100
            )
            
            # Analyze statistics
            user_type_counts = {}
            method_counts = {}
            confidence_scores = []
            
            for memory in recent_memories:
                content = memory.get('content', {})
                identification_result = content.get('identification_result', {})
                
                user_type = identification_result.get('user_type', 'unknown')
                method = identification_result.get('identification_method', 'unknown')
                confidence = identification_result.get('confidence', 0.0)
                
                user_type_counts[user_type] = user_type_counts.get(user_type, 0) + 1
                method_counts[method] = method_counts.get(method, 0) + 1
                confidence_scores.append(confidence)
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                'total_identifications': len(recent_memories),
                'user_type_distribution': user_type_counts,
                'method_distribution': method_counts,
                'average_confidence': round(avg_confidence, 2),
                'high_confidence_rate': len([c for c in confidence_scores if c > 0.7]) / len(confidence_scores) if confidence_scores else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting user type statistics: {str(e)}")
            return {'error': str(e)}
