"""
Context Window Manager for Long Conversations
Manages context windows, memory retrieval, and conversation continuity
"""
import logging
import json
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .ai_memory_service import AIMemoryService
from ..memory_models import ConversationContext

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """
    Manages context windows for long conversations with AI
    Handles memory retrieval, context compression, and conversation continuity
    """
    
    def __init__(self):
        self.memory_service = AIMemoryService()
        self.max_context_tokens = 4000
        self.compression_threshold = 3000
        self.memory_retrieval_limit = 10
        
    def get_conversation_context(self, 
                               user: User,
                               session_id: str,
                               conversation_id: str,
                               query: str = None) -> Dict:
        """
        Get comprehensive conversation context with relevant memories
        """
        try:
            # Get or create context
            context = self.memory_service.get_or_create_context(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            if not context:
                return {'error': 'Failed to get conversation context'}
            
            # Retrieve relevant memories
            relevant_memories = {}
            if query:
                relevant_memories = self.memory_service.retrieve_relevant_memories(
                    query=query,
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    limit_per_type=5
                )
            
            # Build comprehensive context
            conversation_context = {
                'context_id': context.context_id,
                'session_id': session_id,
                'conversation_id': conversation_id,
                'message_count': context.message_count,
                'last_activity': context.last_activity.isoformat(),
                'context_size': context.context_size,
                'current_context': context.current_context,
                'context_summary': context.context_summary,
                'context_history': context.context_history[-3:],  # Last 3 history entries
                'relevant_memories': relevant_memories,
                'memory_summary': self._create_memory_summary(relevant_memories),
                'conversation_continuity': self._assess_conversation_continuity(context),
                'context_health': self._assess_context_health(context)
            }
            
            return conversation_context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return {'error': str(e)}
    
    def update_conversation_context(self,
                                  user: User,
                                  session_id: str,
                                  conversation_id: str,
                                  user_message: str,
                                  ai_response: str = None,
                                  message_metadata: Dict = None) -> bool:
        """
        Update conversation context with new messages
        """
        try:
            # Get context
            context = self.memory_service.get_or_create_context(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            if not context:
                return False
            
            # Store user message as episodic memory
            user_memory_id = self.memory_service.store_episodic_memory(
                memory_type='conversation',
                title=f"User message in {conversation_id}",
                description=user_message[:100] + "..." if len(user_message) > 100 else user_message,
                content={
                    'message': user_message,
                    'message_type': 'user',
                    'metadata': message_metadata or {},
                    'session_id': session_id,
                    'conversation_id': conversation_id
                },
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                importance_score=0.6,
                tags=['conversation', 'user_message']
            )
            
            # Store AI response as episodic memory if provided
            ai_memory_id = None
            if ai_response:
                ai_memory_id = self.memory_service.store_episodic_memory(
                    memory_type='conversation',
                    title=f"AI response in {conversation_id}",
                    description=ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
                    content={
                        'message': ai_response,
                        'message_type': 'ai',
                        'metadata': message_metadata or {},
                        'session_id': session_id,
                        'conversation_id': conversation_id,
                        'related_user_message': user_memory_id
                    },
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    importance_score=0.7,
                    tags=['conversation', 'ai_response']
                )
            
            # Update context with new messages
            context.current_context['messages'] = context.current_context.get('messages', [])
            context.current_context['messages'].append({
                'user_message': user_message,
                'ai_response': ai_response,
                'timestamp': timezone.now().isoformat(),
                'user_memory_id': user_memory_id,
                'ai_memory_id': ai_memory_id,
                'metadata': message_metadata or {}
            })
            
            # Keep only recent messages in context
            if len(context.current_context['messages']) > 10:
                context.current_context['messages'] = context.current_context['messages'][-10:]
            
            # Update context
            self.memory_service.update_context(
                context=context,
                new_message=user_message,
                message_type='user',
                relevant_memories=self._get_recent_memories(context)
            )
            
            # Check for pattern recognition
            self._check_for_patterns(user, session_id, conversation_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            return False
    
    def get_context_for_ai(self,
                          user: User,
                          session_id: str,
                          conversation_id: str,
                          current_query: str) -> str:
        """
        Get formatted context for AI consumption
        """
        try:
            # Get conversation context
            context_data = self.get_conversation_context(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                query=current_query
            )
            
            if 'error' in context_data:
                return f"Error: {context_data['error']}"
            
            # Format context for AI
            formatted_context = self._format_context_for_ai(context_data, current_query)
            
            return formatted_context
            
        except Exception as e:
            logger.error(f"Error getting context for AI: {str(e)}")
            return f"Error: {str(e)}"
    
    def compress_context_if_needed(self,
                                 user: User,
                                 session_id: str,
                                 conversation_id: str) -> bool:
        """
        Compress context if it's getting too large
        """
        try:
            context = self.memory_service.get_or_create_context(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            if not context:
                return False
            
            # Check if compression is needed
            if context.context_size > context.compression_threshold:
                # Compress context
                self.memory_service._compress_context(context)
                
                # Store compression as episodic memory
                self.memory_service.store_episodic_memory(
                    memory_type='system_event',
                    title=f"Context compressed for {conversation_id}",
                    description=f"Context compressed due to size: {context.context_size} tokens",
                    content={
                        'compression_reason': 'size_threshold',
                        'original_size': context.context_size,
                        'compressed_size': context.context_size,
                        'session_id': session_id,
                        'conversation_id': conversation_id
                    },
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    importance_score=0.3,
                    tags=['system', 'compression']
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error compressing context: {str(e)}")
            return False
    
    def get_conversation_summary(self,
                               user: User,
                               session_id: str,
                               conversation_id: str) -> str:
        """
        Get a summary of the conversation
        """
        try:
            context_data = self.get_conversation_context(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            if 'error' in context_data:
                return f"Error: {context_data['error']}"
            
            # Create summary
            summary = self._create_conversation_summary(context_data)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating conversation summary: {str(e)}")
            return f"Error: {str(e)}"
    
    def _create_memory_summary(self, relevant_memories: Dict) -> str:
        """
        Create a summary of relevant memories
        """
        try:
            if not relevant_memories:
                return "No relevant memories found."
            
            summary_parts = []
            
            # Episodic memories summary
            if 'episodic' in relevant_memories and relevant_memories['episodic']:
                episodic_count = len(relevant_memories['episodic'])
                summary_parts.append(f"Found {episodic_count} relevant past conversations and events.")
            
            # Periodic memories summary
            if 'periodic' in relevant_memories and relevant_memories['periodic']:
                periodic_count = len(relevant_memories['periodic'])
                summary_parts.append(f"Identified {periodic_count} behavioral patterns.")
            
            # Semantic memories summary
            if 'semantic' in relevant_memories and relevant_memories['semantic']:
                semantic_count = len(relevant_memories['semantic'])
                summary_parts.append(f"Retrieved {semantic_count} relevant knowledge items.")
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating memory summary: {str(e)}")
            return "Error creating memory summary."
    
    def _assess_conversation_continuity(self, context: ConversationContext) -> Dict:
        """
        Assess conversation continuity and coherence
        """
        try:
            continuity_score = 0.8  # Base score
            
            # Check message count
            if context.message_count > 20:
                continuity_score += 0.1  # Long conversation bonus
            
            # Check context health
            if context.context_size < context.compression_threshold:
                continuity_score += 0.1  # Good context size
            
            # Check recent activity
            time_since_last_activity = timezone.now() - context.last_activity
            if time_since_last_activity < timedelta(hours=1):
                continuity_score += 0.1  # Recent activity
            
            return {
                'continuity_score': min(1.0, continuity_score),
                'message_count': context.message_count,
                'context_health': 'good' if context.context_size < context.compression_threshold else 'needs_compression',
                'last_activity': context.last_activity.isoformat(),
                'time_since_last_activity': str(time_since_last_activity)
            }
            
        except Exception as e:
            logger.error(f"Error assessing conversation continuity: {str(e)}")
            return {'continuity_score': 0.5, 'error': str(e)}
    
    def _assess_context_health(self, context: ConversationContext) -> Dict:
        """
        Assess the health of the conversation context
        """
        try:
            health_score = 1.0
            
            # Check context size
            if context.context_size > context.max_context_size:
                health_score -= 0.3  # Too large
            elif context.context_size > context.compression_threshold:
                health_score -= 0.1  # Approaching limit
            
            # Check message count
            if context.message_count > 100:
                health_score -= 0.2  # Very long conversation
            
            # Check last activity
            time_since_last_activity = timezone.now() - context.last_activity
            if time_since_last_activity > timedelta(days=1):
                health_score -= 0.2  # Stale conversation
            
            return {
                'health_score': max(0.0, health_score),
                'status': 'healthy' if health_score > 0.7 else 'needs_attention' if health_score > 0.4 else 'unhealthy',
                'context_size': context.context_size,
                'max_context_size': context.max_context_size,
                'compression_needed': context.context_size > context.compression_threshold,
                'message_count': context.message_count
            }
            
        except Exception as e:
            logger.error(f"Error assessing context health: {str(e)}")
            return {'health_score': 0.5, 'status': 'error', 'error': str(e)}
    
    def _format_context_for_ai(self, context_data: Dict, current_query: str) -> str:
        """
        Format context data for AI consumption
        """
        try:
            formatted_parts = []
            
            # Add conversation summary
            if context_data.get('context_summary'):
                formatted_parts.append(f"CONVERSATION SUMMARY: {context_data['context_summary']}")
            
            # Add recent messages
            if context_data.get('current_context', {}).get('messages'):
                formatted_parts.append("\nRECENT CONVERSATION:")
                for message in context_data['current_context']['messages'][-5:]:  # Last 5 messages
                    formatted_parts.append(f"User: {message['user_message']}")
                    if message.get('ai_response'):
                        formatted_parts.append(f"AI: {message['ai_response']}")
                    formatted_parts.append("---")
            
            # Add relevant memories
            if context_data.get('relevant_memories'):
                formatted_parts.append("\nRELEVANT MEMORIES:")
                
                # Episodic memories
                if context_data['relevant_memories'].get('episodic'):
                    formatted_parts.append("Past Conversations:")
                    for memory in context_data['relevant_memories']['episodic'][:3]:
                        formatted_parts.append(f"- {memory['title']}: {memory['description']}")
                
                # Periodic memories
                if context_data['relevant_memories'].get('periodic'):
                    formatted_parts.append("Behavioral Patterns:")
                    for memory in context_data['relevant_memories']['periodic'][:2]:
                        formatted_parts.append(f"- {memory['title']}: {memory['description']}")
                
                # Semantic memories
                if context_data['relevant_memories'].get('semantic'):
                    formatted_parts.append("Relevant Knowledge:")
                    for memory in context_data['relevant_memories']['semantic'][:2]:
                        formatted_parts.append(f"- {memory['title']}: {memory['description']}")
            
            # Add current query
            formatted_parts.append(f"\nCURRENT QUERY: {current_query}")
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            logger.error(f"Error formatting context for AI: {str(e)}")
            return f"Error formatting context: {str(e)}"
    
    def _get_recent_memories(self, context: ConversationContext) -> List[Dict]:
        """
        Get recent memories for context
        """
        try:
            # Get recent episodic memories
            recent_memories = self.memory_service.retrieve_episodic_memories(
                query="recent conversation",
                user=context.user,
                limit=5
            )
            
            return recent_memories
            
        except Exception as e:
            logger.error(f"Error getting recent memories: {str(e)}")
            return []
    
    def _check_for_patterns(self, user: User, session_id: str, conversation_id: str):
        """
        Check for patterns in conversation that could become periodic memories
        """
        try:
            # Get recent conversations
            recent_memories = self.memory_service.retrieve_episodic_memories(
                query="conversation",
                user=user,
                limit=20
            )
            
            # Check for patterns
            patterns = self._identify_conversation_patterns(recent_memories)
            
            # Store patterns as periodic memories
            for pattern in patterns:
                self.memory_service.store_periodic_memory(
                    pattern_type='conversation_pattern',
                    title=f"Conversation pattern: {pattern['title']}",
                    description=pattern['description'],
                    pattern_data=pattern['data'],
                    user=user,
                    frequency=pattern['frequency'],
                    confidence=pattern['confidence']
                )
            
        except Exception as e:
            logger.error(f"Error checking for patterns: {str(e)}")
    
    def _identify_conversation_patterns(self, memories: List[Dict]) -> List[Dict]:
        """
        Identify patterns in conversation memories
        """
        # Placeholder: simple pattern identification
        # In production, use more sophisticated pattern recognition
        patterns = []
        
        # Check for time-based patterns
        time_patterns = {}
        for memory in memories:
            timestamp = memory.get('timestamp')
            if timestamp:
                hour = timestamp.split('T')[1].split(':')[0]
                if hour not in time_patterns:
                    time_patterns[hour] = 0
                time_patterns[hour] += 1
        
        # Find peak hours
        for hour, count in time_patterns.items():
            if count >= 3:  # Minimum occurrences
                patterns.append({
                    'title': f"Peak conversation hour: {hour}:00",
                    'description': f"User typically converses at {hour}:00 ({count} occurrences)",
                    'data': {'hour': hour, 'count': count},
                    'frequency': 'daily',
                    'confidence': min(0.9, count * 0.1)
                })
        
        return patterns
    
    def _create_conversation_summary(self, context_data: Dict) -> str:
        """
        Create a summary of the conversation
        """
        try:
            summary_parts = []
            
            # Basic info
            summary_parts.append(f"Conversation ID: {context_data['conversation_id']}")
            summary_parts.append(f"Message Count: {context_data['message_count']}")
            summary_parts.append(f"Last Activity: {context_data['last_activity']}")
            
            # Context health
            health = context_data.get('context_health', {})
            summary_parts.append(f"Context Health: {health.get('status', 'unknown')}")
            
            # Memory summary
            memory_summary = context_data.get('memory_summary', 'No memories')
            summary_parts.append(f"Relevant Memories: {memory_summary}")
            
            # Recent messages
            if context_data.get('current_context', {}).get('messages'):
                recent_messages = context_data['current_context']['messages'][-3:]
                summary_parts.append("\nRecent Messages:")
                for message in recent_messages:
                    summary_parts.append(f"- User: {message['user_message'][:50]}...")
                    if message.get('ai_response'):
                        summary_parts.append(f"  AI: {message['ai_response'][:50]}...")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating conversation summary: {str(e)}")
            return f"Error creating summary: {str(e)}"
