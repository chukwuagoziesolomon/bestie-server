"""
AI Memory Management Service
Comprehensive memory system for episodic, periodic, and semantic memory
"""
import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth.models import User
from django.db.models import Q, F
from ..memory_models import (
    EpisodicMemory, PeriodicMemory, SemanticMemory, 
    ConversationContext, MemoryRetrievalLog, MemoryConsolidation
)

logger = logging.getLogger(__name__)


class AIMemoryService:
    """
    Comprehensive AI Memory Management Service
    Handles episodic, periodic, and semantic memory with context management
    """
    
    def __init__(self):
        self.max_context_tokens = 4000
        self.compression_threshold = 3000
        self.embedding_dimension = 384  # For sentence-transformers
        
    # ==================== EPISODIC MEMORY ====================
    
    def store_episodic_memory(self, 
                            memory_type: str,
                            title: str,
                            description: str,
                            content: Dict,
                            user: User = None,
                            session_id: str = None,
                            conversation_id: str = None,
                            timestamp: datetime = None,
                            importance_score: float = 0.5,
                            emotional_tone: str = None,
                            tags: List[str] = None,
                            related_orders: List[int] = None) -> str:
        """
        Store an episodic memory (specific event/experience)
        """
        try:
            memory_id = f"episodic_{uuid.uuid4().hex[:16]}"
            
            # Generate embeddings for semantic search
            embeddings = self._generate_embeddings(f"{title} {description}")
            
            # Extract keywords
            keywords = self._extract_keywords(f"{title} {description}")
            
            memory = EpisodicMemory.objects.create(
                memory_id=memory_id,
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                memory_type=memory_type,
                title=title,
                description=description,
                content=content,
                timestamp=timestamp or timezone.now(),
                importance_score=importance_score,
                emotional_tone=emotional_tone,
                tags=tags or [],
                keywords=keywords,
                embeddings=embeddings,
                related_orders=related_orders or []
            )
            
            logger.info(f"Stored episodic memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing episodic memory: {str(e)}")
            return None
    
    def retrieve_episodic_memories(self, 
                                 query: str,
                                 user: User = None,
                                 memory_types: List[str] = None,
                                 limit: int = 10,
                                 min_importance: float = 0.0,
                                 time_range: Tuple[datetime, datetime] = None) -> List[Dict]:
        """
        Retrieve relevant episodic memories
        """
        try:
            # Start with base query
            queryset = EpisodicMemory.objects.filter(is_active=True)
            
            # Filter by user
            if user:
                queryset = queryset.filter(user=user)
            
            # Filter by memory types
            if memory_types:
                queryset = queryset.filter(memory_type__in=memory_types)
            
            # Filter by importance
            queryset = queryset.filter(importance_score__gte=min_importance)
            
            # Filter by time range
            if time_range:
                start_time, end_time = time_range
                queryset = queryset.filter(timestamp__range=[start_time, end_time])
            
            # Semantic search using embeddings
            query_embeddings = self._generate_embeddings(query)
            memories = []
            
            for memory in queryset[:limit * 2]:  # Get more for ranking
                similarity = self._calculate_similarity(query_embeddings, memory.embeddings)
                if similarity > 0.3:  # Minimum similarity threshold
                    memories.append({
                        'memory_id': memory.memory_id,
                        'title': memory.title,
                        'description': memory.description,
                        'content': memory.content,
                        'memory_type': memory.memory_type,
                        'timestamp': memory.timestamp.isoformat(),
                        'importance_score': memory.importance_score,
                        'similarity_score': similarity,
                        'tags': memory.tags,
                        'related_orders': memory.related_orders
                    })
            
            # Sort by combined score (similarity + importance)
            memories.sort(key=lambda x: x['similarity_score'] * 0.7 + x['importance_score'] * 0.3, reverse=True)
            
            # Log retrieval
            self._log_memory_retrieval(query, 'episodic', [m['memory_id'] for m in memories[:limit]], user)
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Error retrieving episodic memories: {str(e)}")
            return []
    
    # ==================== PERIODIC MEMORY ====================
    
    def store_periodic_memory(self,
                            pattern_type: str,
                            title: str,
                            description: str,
                            pattern_data: Dict,
                            user: User = None,
                            frequency: str = 'unknown',
                            confidence: float = 0.5,
                            time_of_day: str = None,
                            day_of_week: str = None) -> str:
        """
        Store a periodic memory (pattern/behavior)
        """
        try:
            pattern_id = f"periodic_{uuid.uuid4().hex[:16]}"
            
            memory = PeriodicMemory.objects.create(
                pattern_id=pattern_id,
                user=user,
                pattern_type=pattern_type,
                title=title,
                description=description,
                pattern_data=pattern_data,
                frequency=frequency,
                confidence=confidence,
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                last_observed=timezone.now(),
                occurrence_count=1
            )
            
            logger.info(f"Stored periodic memory: {pattern_id}")
            return pattern_id
            
        except Exception as e:
            logger.error(f"Error storing periodic memory: {str(e)}")
            return None
    
    def update_periodic_memory(self, pattern_id: str, new_observation: Dict) -> bool:
        """
        Update periodic memory with new observation
        """
        try:
            memory = PeriodicMemory.objects.get(pattern_id=pattern_id)
            
            # Update occurrence count
            memory.occurrence_count += 1
            memory.last_observed = timezone.now()
            
            # Update confidence based on consistency
            consistency_score = self._calculate_pattern_consistency(memory.pattern_data, new_observation)
            memory.confidence = (memory.confidence * 0.8) + (consistency_score * 0.2)
            
            # Update pattern data
            memory.pattern_data = self._merge_pattern_data(memory.pattern_data, new_observation)
            
            memory.save()
            
            logger.info(f"Updated periodic memory: {pattern_id}")
            return True
            
        except PeriodicMemory.DoesNotExist:
            logger.warning(f"Periodic memory not found: {pattern_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating periodic memory: {str(e)}")
            return False
    
    def retrieve_periodic_memories(self,
                                 user: User = None,
                                 pattern_types: List[str] = None,
                                 min_confidence: float = 0.3,
                                 limit: int = 10) -> List[Dict]:
        """
        Retrieve relevant periodic memories
        """
        try:
            queryset = PeriodicMemory.objects.filter(is_active=True)
            
            if user:
                queryset = queryset.filter(user=user)
            
            if pattern_types:
                queryset = queryset.filter(pattern_type__in=pattern_types)
            
            queryset = queryset.filter(confidence__gte=min_confidence)
            
            memories = []
            for memory in queryset[:limit]:
                memories.append({
                    'pattern_id': memory.pattern_id,
                    'title': memory.title,
                    'description': memory.description,
                    'pattern_data': memory.pattern_data,
                    'pattern_type': memory.pattern_type,
                    'frequency': memory.frequency,
                    'confidence': memory.confidence,
                    'occurrence_count': memory.occurrence_count,
                    'last_observed': memory.last_observed.isoformat(),
                    'time_of_day': memory.time_of_day,
                    'day_of_week': memory.day_of_week
                })
            
            # Log retrieval
            self._log_memory_retrieval("periodic_patterns", 'periodic', [m['pattern_id'] for m in memories], user)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving periodic memories: {str(e)}")
            return []
    
    # ==================== SEMANTIC MEMORY ====================
    
    def store_semantic_memory(self,
                            knowledge_type: str,
                            title: str,
                            description: str,
                            content: Dict,
                            domain: str,
                            confidence: float = 0.8,
                            source: str = 'ai_learning',
                            scope: str = 'global',
                            tags: List[str] = None) -> str:
        """
        Store semantic memory (fact/knowledge)
        """
        try:
            knowledge_id = f"semantic_{uuid.uuid4().hex[:16]}"
            
            # Generate embeddings
            embeddings = self._generate_embeddings(f"{title} {description}")
            keywords = self._extract_keywords(f"{title} {description}")
            
            memory = SemanticMemory.objects.create(
                knowledge_id=knowledge_id,
                knowledge_type=knowledge_type,
                title=title,
                description=description,
                content=content,
                domain=domain,
                confidence=confidence,
                source=source,
                scope=scope,
                tags=tags or [],
                keywords=keywords,
                embeddings=embeddings,
                last_verified=timezone.now(),
                verification_count=1
            )
            
            logger.info(f"Stored semantic memory: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Error storing semantic memory: {str(e)}")
            return None
    
    def retrieve_semantic_memories(self,
                                 query: str,
                                 domain: str = None,
                                 knowledge_types: List[str] = None,
                                 min_confidence: float = 0.5,
                                 limit: int = 10) -> List[Dict]:
        """
        Retrieve relevant semantic memories
        """
        try:
            queryset = SemanticMemory.objects.filter(is_active=True)
            
            if domain:
                queryset = queryset.filter(domain=domain)
            
            if knowledge_types:
                queryset = queryset.filter(knowledge_type__in=knowledge_types)
            
            queryset = queryset.filter(confidence__gte=min_confidence)
            
            # Semantic search
            query_embeddings = self._generate_embeddings(query)
            memories = []
            
            for memory in queryset[:limit * 2]:
                similarity = self._calculate_similarity(query_embeddings, memory.embeddings)
                if similarity > 0.4:  # Higher threshold for semantic memory
                    memories.append({
                        'knowledge_id': memory.knowledge_id,
                        'title': memory.title,
                        'description': memory.description,
                        'content': memory.content,
                        'knowledge_type': memory.knowledge_type,
                        'domain': memory.domain,
                        'confidence': memory.confidence,
                        'similarity_score': similarity,
                        'source': memory.source,
                        'last_verified': memory.last_verified.isoformat(),
                        'tags': memory.tags
                    })
            
            # Sort by combined score
            memories.sort(key=lambda x: x['similarity_score'] * 0.6 + x['confidence'] * 0.4, reverse=True)
            
            # Log retrieval
            self._log_memory_retrieval(query, 'semantic', [m['knowledge_id'] for m in memories[:limit]])
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Error retrieving semantic memories: {str(e)}")
            return []
    
    # ==================== CONTEXT MANAGEMENT ====================
    
    def get_or_create_context(self, 
                            user: User,
                            session_id: str,
                            conversation_id: str) -> ConversationContext:
        """
        Get or create conversation context
        """
        try:
            context, created = ConversationContext.objects.get_or_create(
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                defaults={
                    'context_id': f"context_{uuid.uuid4().hex[:16]}",
                    'current_context': {},
                    'context_history': [],
                    'message_count': 0,
                    'context_size': 0
                }
            )
            
            if created:
                logger.info(f"Created new context: {context.context_id}")
            else:
                logger.info(f"Retrieved existing context: {context.context_id}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting/creating context: {str(e)}")
            return None
    
    def update_context(self,
                      context: ConversationContext,
                      new_message: str,
                      message_type: str = 'user',
                      relevant_memories: List[Dict] = None) -> bool:
        """
        Update conversation context with new message
        """
        try:
            # Add new message to context
            context.current_context['last_message'] = {
                'content': new_message,
                'type': message_type,
                'timestamp': timezone.now().isoformat()
            }
            
            # Update message count
            context.message_count += 1
            context.last_activity = timezone.now()
            
            # Estimate context size (rough token count)
            context.context_size = self._estimate_context_size(context.current_context)
            
            # Add relevant memories to context
            if relevant_memories:
                context.current_context['relevant_memories'] = relevant_memories[:5]  # Limit to 5 most relevant
            
            # Check if context needs compression
            if context.context_size > context.compression_threshold:
                self._compress_context(context)
            
            context.save()
            
            logger.info(f"Updated context: {context.context_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating context: {str(e)}")
            return False
    
    def retrieve_relevant_memories(self,
                                 query: str,
                                 user: User,
                                 session_id: str = None,
                                 conversation_id: str = None,
                                 memory_types: List[str] = None,
                                 limit_per_type: int = 5) -> Dict[str, List[Dict]]:
        """
        Retrieve relevant memories from all types
        """
        try:
            relevant_memories = {}
            
            # Retrieve episodic memories
            if not memory_types or 'episodic' in memory_types:
                episodic = self.retrieve_episodic_memories(
                    query=query,
                    user=user,
                    limit=limit_per_type
                )
                relevant_memories['episodic'] = episodic
            
            # Retrieve periodic memories
            if not memory_types or 'periodic' in memory_types:
                periodic = self.retrieve_periodic_memories(
                    user=user,
                    limit=limit_per_type
                )
                relevant_memories['periodic'] = periodic
            
            # Retrieve semantic memories
            if not memory_types or 'semantic' in memory_types:
                semantic = self.retrieve_semantic_memories(
                    query=query,
                    limit=limit_per_type
                )
                relevant_memories['semantic'] = semantic
            
            return relevant_memories
            
        except Exception as e:
            logger.error(f"Error retrieving relevant memories: {str(e)}")
            return {}
    
    # ==================== MEMORY CONSOLIDATION ====================
    
    def consolidate_memories(self, user: User = None) -> Dict:
        """
        Consolidate memories (episodic -> periodic, episodic -> semantic)
        """
        try:
            consolidation_results = {
                'episodic_to_periodic': 0,
                'episodic_to_semantic': 0,
                'periodic_updates': 0,
                'semantic_updates': 0
            }
            
            # Consolidate episodic memories to periodic patterns
            if user:
                episodic_memories = EpisodicMemory.objects.filter(
                    user=user,
                    is_active=True,
                    timestamp__gte=timezone.now() - timedelta(days=30)
                )
            else:
                episodic_memories = EpisodicMemory.objects.filter(
                    is_active=True,
                    timestamp__gte=timezone.now() - timedelta(days=30)
                )
            
            # Group by patterns
            patterns = self._identify_patterns(episodic_memories)
            
            for pattern_type, pattern_data in patterns.items():
                if len(pattern_data['memories']) >= 3:  # Minimum occurrences for pattern
                    # Create or update periodic memory
                    periodic_id = self._create_periodic_from_episodic(pattern_data)
                    if periodic_id:
                        consolidation_results['episodic_to_periodic'] += 1
            
            # Consolidate episodic memories to semantic knowledge
            semantic_knowledge = self._extract_semantic_knowledge(episodic_memories)
            
            for knowledge in semantic_knowledge:
                semantic_id = self.store_semantic_memory(**knowledge)
                if semantic_id:
                    consolidation_results['episodic_to_semantic'] += 1
            
            logger.info(f"Memory consolidation completed: {consolidation_results}")
            return consolidation_results
            
        except Exception as e:
            logger.error(f"Error consolidating memories: {str(e)}")
            return {}
    
    # ==================== UTILITY METHODS ====================
    
    def _generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text (placeholder implementation)
        In production, use sentence-transformers or similar
        """
        # Placeholder: return random embeddings
        # In production, use: from sentence_transformers import SentenceTransformer
        import random
        return [random.random() for _ in range(self.embedding_dimension)]
    
    def _calculate_similarity(self, embeddings1: List[float], embeddings2: List[float]) -> float:
        """
        Calculate cosine similarity between embeddings
        """
        try:
            import numpy as np
            
            # Convert to numpy arrays
            vec1 = np.array(embeddings1)
            vec2 = np.array(embeddings2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text (placeholder implementation)
        """
        # Placeholder: simple keyword extraction
        # In production, use NLTK, spaCy, or similar
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        return list(set(keywords))[:10]  # Return top 10 unique keywords
    
    def _log_memory_retrieval(self, query: str, retrieval_type: str, retrieved_memories: List[str], user: User = None):
        """
        Log memory retrieval for analytics
        """
        try:
            retrieval_id = f"retrieval_{uuid.uuid4().hex[:16]}"
            
            MemoryRetrievalLog.objects.create(
                retrieval_id=retrieval_id,
                user=user,
                query=query,
                retrieval_type=retrieval_type,
                retrieved_memories=retrieved_memories,
                retrieval_time=0.1,  # Placeholder
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error logging memory retrieval: {str(e)}")
    
    def _estimate_context_size(self, context: Dict) -> int:
        """
        Estimate context size in tokens (rough approximation)
        """
        try:
            context_str = json.dumps(context)
            return len(context_str.split())  # Rough token count
        except Exception as e:
            logger.error(f"Error estimating context size: {str(e)}")
            return 0
    
    def _compress_context(self, context: ConversationContext):
        """
        Compress context when it gets too large
        """
        try:
            # Move current context to history
            context.context_history.append(context.current_context.copy())
            
            # Keep only recent history
            if len(context.context_history) > 10:
                context.context_history = context.context_history[-10:]
            
            # Create summary of compressed context
            context.context_summary = self._summarize_context(context.current_context)
            
            # Reset current context
            context.current_context = {
                'summary': context.context_summary,
                'last_activity': timezone.now().isoformat()
            }
            
            context.context_size = self._estimate_context_size(context.current_context)
            
            logger.info(f"Compressed context: {context.context_id}")
            
        except Exception as e:
            logger.error(f"Error compressing context: {str(e)}")
    
    def _summarize_context(self, context: Dict) -> str:
        """
        Summarize context (placeholder implementation)
        """
        # Placeholder: simple summarization
        # In production, use LLM for summarization
        return f"Conversation with {context.get('message_count', 0)} messages"
    
    def _identify_patterns(self, episodic_memories) -> Dict:
        """
        Identify patterns in episodic memories
        """
        # Placeholder: simple pattern identification
        # In production, use more sophisticated pattern recognition
        patterns = {}
        
        for memory in episodic_memories:
            pattern_key = f"{memory.memory_type}_{memory.user_id if memory.user else 'global'}"
            
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'memories': [],
                    'pattern_type': memory.memory_type,
                    'user': memory.user
                }
            
            patterns[pattern_key]['memories'].append(memory)
        
        return patterns
    
    def _create_periodic_from_episodic(self, pattern_data: Dict) -> str:
        """
        Create periodic memory from episodic memories
        """
        try:
            memories = pattern_data['memories']
            if len(memories) < 3:
                return None
            
            # Calculate frequency
            timestamps = [m.timestamp for m in memories]
            frequency = self._calculate_frequency(timestamps)
            
            # Create periodic memory
            periodic_id = self.store_periodic_memory(
                pattern_type=pattern_data['pattern_type'],
                title=f"Pattern: {pattern_data['pattern_type']}",
                description=f"Identified pattern from {len(memories)} occurrences",
                pattern_data={
                    'source_memories': [m.memory_id for m in memories],
                    'frequency': frequency,
                    'first_occurrence': min(timestamps).isoformat(),
                    'last_occurrence': max(timestamps).isoformat()
                },
                user=pattern_data['user'],
                frequency=frequency,
                confidence=min(0.9, len(memories) * 0.1)
            )
            
            return periodic_id
            
        except Exception as e:
            logger.error(f"Error creating periodic from episodic: {str(e)}")
            return None
    
    def _calculate_frequency(self, timestamps: List[datetime]) -> str:
        """
        Calculate frequency from timestamps
        """
        if len(timestamps) < 2:
            return 'unknown'
        
        # Calculate average interval
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Categorize frequency
        if avg_interval < 3600:  # Less than 1 hour
            return 'hourly'
        elif avg_interval < 86400:  # Less than 1 day
            return 'daily'
        elif avg_interval < 604800:  # Less than 1 week
            return 'weekly'
        elif avg_interval < 2592000:  # Less than 1 month
            return 'monthly'
        else:
            return 'yearly'
    
    def _extract_semantic_knowledge(self, episodic_memories) -> List[Dict]:
        """
        Extract semantic knowledge from episodic memories
        """
        # Placeholder: simple knowledge extraction
        # In production, use more sophisticated knowledge extraction
        knowledge = []
        
        # Group by memory type and extract common patterns
        memory_groups = {}
        for memory in episodic_memories:
            if memory.memory_type not in memory_groups:
                memory_groups[memory.memory_type] = []
            memory_groups[memory.memory_type].append(memory)
        
        for memory_type, memories in memory_groups.items():
            if len(memories) >= 5:  # Minimum for knowledge extraction
                knowledge.append({
                    'knowledge_type': 'fact',
                    'title': f"Knowledge about {memory_type}",
                    'description': f"Extracted from {len(memories)} {memory_type} memories",
                    'content': {
                        'memory_type': memory_type,
                        'source_memories': [m.memory_id for m in memories],
                        'extraction_date': timezone.now().isoformat()
                    },
                    'domain': 'delivery_system',
                    'confidence': min(0.9, len(memories) * 0.05),
                    'source': 'episodic_consolidation'
                })
        
        return knowledge
    
    def _calculate_pattern_consistency(self, existing_pattern: Dict, new_observation: Dict) -> float:
        """
        Calculate consistency between existing pattern and new observation
        """
        # Placeholder: simple consistency calculation
        # In production, use more sophisticated consistency metrics
        return 0.8  # Placeholder consistency score
    
    def _merge_pattern_data(self, existing_data: Dict, new_data: Dict) -> Dict:
        """
        Merge new observation data with existing pattern data
        """
        # Placeholder: simple merge
        # In production, use more sophisticated merging
        merged = existing_data.copy()
        merged.update(new_data)
        return merged

    

    def update_context(self,

                      context: ConversationContext,

                      new_message: str,

                      message_type: str = 'user',

                      relevant_memories: List[Dict] = None) -> bool:

        """

        Update conversation context with new message

        """

        try:

            # Add new message to context

            context.current_context['last_message'] = {

                'content': new_message,

                'type': message_type,

                'timestamp': timezone.now().isoformat()

            }

            

            # Update message count

            context.message_count += 1

            context.last_activity = timezone.now()

            

            # Estimate context size (rough token count)

            context.context_size = self._estimate_context_size(context.current_context)

            

            # Add relevant memories to context

            if relevant_memories:

                context.current_context['relevant_memories'] = relevant_memories[:5]  # Limit to 5 most relevant

            

            # Check if context needs compression

            if context.context_size > context.compression_threshold:

                self._compress_context(context)

            

            context.save()

            

            logger.info(f"Updated context: {context.context_id}")

            return True

            

        except Exception as e:

            logger.error(f"Error updating context: {str(e)}")

            return False

    

    def retrieve_relevant_memories(self,

                                 query: str,

                                 user: User,

                                 session_id: str = None,

                                 conversation_id: str = None,

                                 memory_types: List[str] = None,

                                 limit_per_type: int = 5) -> Dict[str, List[Dict]]:

        """

        Retrieve relevant memories from all types

        """

        try:

            relevant_memories = {}

            

            # Retrieve episodic memories

            if not memory_types or 'episodic' in memory_types:

                episodic = self.retrieve_episodic_memories(

                    query=query,

                    user=user,

                    limit=limit_per_type

                )

                relevant_memories['episodic'] = episodic

            

            # Retrieve periodic memories

            if not memory_types or 'periodic' in memory_types:

                periodic = self.retrieve_periodic_memories(

                    user=user,

                    limit=limit_per_type

                )

                relevant_memories['periodic'] = periodic

            

            # Retrieve semantic memories

            if not memory_types or 'semantic' in memory_types:

                semantic = self.retrieve_semantic_memories(

                    query=query,

                    limit=limit_per_type

                )

                relevant_memories['semantic'] = semantic

            

            return relevant_memories

            

        except Exception as e:

            logger.error(f"Error retrieving relevant memories: {str(e)}")

            return {}

    

    # ==================== MEMORY CONSOLIDATION ====================

    

    def consolidate_memories(self, user: User = None) -> Dict:

        """

        Consolidate memories (episodic -> periodic, episodic -> semantic)

        """

        try:

            consolidation_results = {

                'episodic_to_periodic': 0,

                'episodic_to_semantic': 0,

                'periodic_updates': 0,

                'semantic_updates': 0

            }

            

            # Consolidate episodic memories to periodic patterns

            if user:

                episodic_memories = EpisodicMemory.objects.filter(

                    user=user,

                    is_active=True,

                    timestamp__gte=timezone.now() - timedelta(days=30)

                )

            else:

                episodic_memories = EpisodicMemory.objects.filter(

                    is_active=True,

                    timestamp__gte=timezone.now() - timedelta(days=30)

                )

            

            # Group by patterns

            patterns = self._identify_patterns(episodic_memories)

            

            for pattern_type, pattern_data in patterns.items():

                if len(pattern_data['memories']) >= 3:  # Minimum occurrences for pattern

                    # Create or update periodic memory

                    periodic_id = self._create_periodic_from_episodic(pattern_data)

                    if periodic_id:

                        consolidation_results['episodic_to_periodic'] += 1

            

            # Consolidate episodic memories to semantic knowledge

            semantic_knowledge = self._extract_semantic_knowledge(episodic_memories)

            

            for knowledge in semantic_knowledge:

                semantic_id = self.store_semantic_memory(**knowledge)

                if semantic_id:

                    consolidation_results['episodic_to_semantic'] += 1

            

            logger.info(f"Memory consolidation completed: {consolidation_results}")

            return consolidation_results

            

        except Exception as e:

            logger.error(f"Error consolidating memories: {str(e)}")

            return {}

    

    # ==================== UTILITY METHODS ====================

    

    def _generate_embeddings(self, text: str) -> List[float]:

        """

        Generate embeddings for text (placeholder implementation)

        In production, use sentence-transformers or similar

        """

        # Placeholder: return random embeddings

        # In production, use: from sentence_transformers import SentenceTransformer

        import random

        return [random.random() for _ in range(self.embedding_dimension)]

    

    def _calculate_similarity(self, embeddings1: List[float], embeddings2: List[float]) -> float:

        """

        Calculate cosine similarity between embeddings

        """

        try:

            import numpy as np

            

            # Convert to numpy arrays

            vec1 = np.array(embeddings1)

            vec2 = np.array(embeddings2)

            

            # Calculate cosine similarity

            dot_product = np.dot(vec1, vec2)

            norm1 = np.linalg.norm(vec1)

            norm2 = np.linalg.norm(vec2)

            

            if norm1 == 0 or norm2 == 0:

                return 0.0

            

            similarity = dot_product / (norm1 * norm2)

            return float(similarity)

            

        except Exception as e:

            logger.error(f"Error calculating similarity: {str(e)}")

            return 0.0

    

    def _extract_keywords(self, text: str) -> List[str]:

        """

        Extract keywords from text (placeholder implementation)

        """

        # Placeholder: simple keyword extraction

        # In production, use NLTK, spaCy, or similar

        words = text.lower().split()

        keywords = [word for word in words if len(word) > 3 and word.isalpha()]

        return list(set(keywords))[:10]  # Return top 10 unique keywords

    

    def _log_memory_retrieval(self, query: str, retrieval_type: str, retrieved_memories: List[str], user: User = None):

        """

        Log memory retrieval for analytics

        """

        try:

            retrieval_id = f"retrieval_{uuid.uuid4().hex[:16]}"

            

            MemoryRetrievalLog.objects.create(

                retrieval_id=retrieval_id,

                user=user,

                query=query,

                retrieval_type=retrieval_type,

                retrieved_memories=retrieved_memories,

                retrieval_time=0.1,  # Placeholder

                success=True

            )

            

        except Exception as e:

            logger.error(f"Error logging memory retrieval: {str(e)}")

    

    def _estimate_context_size(self, context: Dict) -> int:

        """

        Estimate context size in tokens (rough approximation)

        """

        try:

            context_str = json.dumps(context)

            return len(context_str.split())  # Rough token count

        except Exception as e:

            logger.error(f"Error estimating context size: {str(e)}")

            return 0

    

    def _compress_context(self, context: ConversationContext):

        """

        Compress context when it gets too large

        """

        try:

            # Move current context to history

            context.context_history.append(context.current_context.copy())

            

            # Keep only recent history

            if len(context.context_history) > 10:

                context.context_history = context.context_history[-10:]

            

            # Create summary of compressed context

            context.context_summary = self._summarize_context(context.current_context)

            

            # Reset current context

            context.current_context = {

                'summary': context.context_summary,

                'last_activity': timezone.now().isoformat()

            }

            

            context.context_size = self._estimate_context_size(context.current_context)

            

            logger.info(f"Compressed context: {context.context_id}")

            

        except Exception as e:

            logger.error(f"Error compressing context: {str(e)}")

    

    def _summarize_context(self, context: Dict) -> str:

        """

        Summarize context (placeholder implementation)

        """

        # Placeholder: simple summarization

        # In production, use LLM for summarization

        return f"Conversation with {context.get('message_count', 0)} messages"

    

    def _identify_patterns(self, episodic_memories) -> Dict:

        """

        Identify patterns in episodic memories

        """

        # Placeholder: simple pattern identification

        # In production, use more sophisticated pattern recognition

        patterns = {}

        

        for memory in episodic_memories:

            pattern_key = f"{memory.memory_type}_{memory.user_id if memory.user else 'global'}"

            

            if pattern_key not in patterns:

                patterns[pattern_key] = {

                    'memories': [],

                    'pattern_type': memory.memory_type,

                    'user': memory.user

                }

            

            patterns[pattern_key]['memories'].append(memory)

        

        return patterns

    

    def _create_periodic_from_episodic(self, pattern_data: Dict) -> str:

        """

        Create periodic memory from episodic memories

        """

        try:

            memories = pattern_data['memories']

            if len(memories) < 3:

                return None

            

            # Calculate frequency

            timestamps = [m.timestamp for m in memories]

            frequency = self._calculate_frequency(timestamps)

            

            # Create periodic memory

            periodic_id = self.store_periodic_memory(

                pattern_type=pattern_data['pattern_type'],

                title=f"Pattern: {pattern_data['pattern_type']}",

                description=f"Identified pattern from {len(memories)} occurrences",

                pattern_data={

                    'source_memories': [m.memory_id for m in memories],

                    'frequency': frequency,

                    'first_occurrence': min(timestamps).isoformat(),

                    'last_occurrence': max(timestamps).isoformat()

                },

                user=pattern_data['user'],

                frequency=frequency,

                confidence=min(0.9, len(memories) * 0.1)

            )

            

            return periodic_id

            

        except Exception as e:

            logger.error(f"Error creating periodic from episodic: {str(e)}")

            return None

    

    def _calculate_frequency(self, timestamps: List[datetime]) -> str:

        """

        Calculate frequency from timestamps

        """

        if len(timestamps) < 2:

            return 'unknown'

        

        # Calculate average interval

        intervals = []

        for i in range(1, len(timestamps)):

            interval = (timestamps[i] - timestamps[i-1]).total_seconds()

            intervals.append(interval)

        

        avg_interval = sum(intervals) / len(intervals)

        

        # Categorize frequency

        if avg_interval < 3600:  # Less than 1 hour

            return 'hourly'

        elif avg_interval < 86400:  # Less than 1 day

            return 'daily'

        elif avg_interval < 604800:  # Less than 1 week

            return 'weekly'

        elif avg_interval < 2592000:  # Less than 1 month

            return 'monthly'

        else:

            return 'yearly'

    

    def _extract_semantic_knowledge(self, episodic_memories) -> List[Dict]:

        """

        Extract semantic knowledge from episodic memories

        """

        # Placeholder: simple knowledge extraction

        # In production, use more sophisticated knowledge extraction

        knowledge = []

        

        # Group by memory type and extract common patterns

        memory_groups = {}

        for memory in episodic_memories:

            if memory.memory_type not in memory_groups:

                memory_groups[memory.memory_type] = []

            memory_groups[memory.memory_type].append(memory)

        

        for memory_type, memories in memory_groups.items():

            if len(memories) >= 5:  # Minimum for knowledge extraction

                knowledge.append({

                    'knowledge_type': 'fact',

                    'title': f"Knowledge about {memory_type}",

                    'description': f"Extracted from {len(memories)} {memory_type} memories",

                    'content': {

                        'memory_type': memory_type,

                        'source_memories': [m.memory_id for m in memories],

                        'extraction_date': timezone.now().isoformat()

                    },

                    'domain': 'delivery_system',

                    'confidence': min(0.9, len(memories) * 0.05),

                    'source': 'episodic_consolidation'

                })

        

        return knowledge

    

    def _calculate_pattern_consistency(self, existing_pattern: Dict, new_observation: Dict) -> float:

        """

        Calculate consistency between existing pattern and new observation

        """

        # Placeholder: simple consistency calculation

        # In production, use more sophisticated consistency metrics

        return 0.8  # Placeholder consistency score

    

    def _merge_pattern_data(self, existing_data: Dict, new_data: Dict) -> Dict:

        """

        Merge new observation data with existing pattern data

        """

        # Placeholder: simple merge

        # In production, use more sophisticated merging

        merged = existing_data.copy()

        merged.update(new_data)

        return merged


