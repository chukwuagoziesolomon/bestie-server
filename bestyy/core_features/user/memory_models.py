"""
AI Memory System Models
Comprehensive memory storage for episodic, periodic, and semantic memory
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class MemoryBase(models.Model):
    """
    Base model for all memory types
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class EpisodicMemory(MemoryBase):
    """
    Episodic Memory: Specific events and experiences
    Stores individual conversations, interactions, and events
    """
    MEMORY_TYPES = [
        ('conversation', 'Conversation'),
        ('order_event', 'Order Event'),
        ('delivery_event', 'Delivery Event'),
        ('support_interaction', 'Support Interaction'),
        ('vendor_interaction', 'Vendor Interaction'),
        ('courier_interaction', 'Courier Interaction'),
        ('system_event', 'System Event'),
    ]
    
    # Core identification
    memory_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    conversation_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Memory content
    memory_type = models.CharField(max_length=50, choices=MEMORY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.JSONField(default=dict)  # Structured content
    
    # Context and metadata
    timestamp = models.DateTimeField()
    location = models.CharField(max_length=200, null=True, blank=True)
    participants = models.JSONField(default=list)  # List of user IDs involved
    
    # Emotional and importance markers
    emotional_tone = models.CharField(max_length=50, null=True, blank=True)
    importance_score = models.FloatField(default=0.5)  # 0.0 to 1.0
    satisfaction_score = models.FloatField(null=True, blank=True)  # For customer interactions
    
    # Relationships
    related_orders = models.JSONField(default=list)  # List of order IDs
    related_memories = models.ManyToManyField('self', blank=True, symmetrical=False)
    
    # Retrieval metadata
    tags = models.JSONField(default=list)  # Searchable tags
    keywords = models.JSONField(default=list)  # Extracted keywords
    embeddings = models.JSONField(default=list)  # Vector embeddings for semantic search
    
    class Meta:
        db_table = 'ai_episodic_memory'
        ordering = ['-timestamp', '-importance_score']
        indexes = [
            models.Index(fields=['user', 'memory_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['importance_score']),
            models.Index(fields=['session_id']),
            models.Index(fields=['conversation_id']),
        ]
    
    def __str__(self):
        return f"Episodic: {self.title} ({self.memory_type})"


class PeriodicMemory(MemoryBase):
    """
    Periodic Memory: Recurring patterns, schedules, and regular events
    Stores patterns, preferences, and recurring behaviors
    """
    PATTERN_TYPES = [
        ('user_preference', 'User Preference'),
        ('delivery_pattern', 'Delivery Pattern'),
        ('vendor_behavior', 'Vendor Behavior'),
        ('courier_behavior', 'Courier Behavior'),
        ('system_pattern', 'System Pattern'),
        ('seasonal_pattern', 'Seasonal Pattern'),
        ('time_pattern', 'Time Pattern'),
    ]
    
    # Core identification
    pattern_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    
    # Pattern content
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    pattern_data = models.JSONField(default=dict)  # Structured pattern data
    
    # Pattern characteristics
    frequency = models.CharField(max_length=50)  # daily, weekly, monthly, etc.
    confidence = models.FloatField(default=0.5)  # How confident we are in this pattern
    occurrence_count = models.IntegerField(default=1)  # How many times observed
    
    # Time patterns
    time_of_day = models.CharField(max_length=20, null=True, blank=True)  # morning, afternoon, etc.
    day_of_week = models.CharField(max_length=20, null=True, blank=True)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    
    # Pattern metadata
    last_observed = models.DateTimeField()
    next_expected = models.DateTimeField(null=True, blank=True)
    deviation_threshold = models.FloatField(default=0.2)  # How much deviation is acceptable
    
    # Related data
    related_episodic_memories = models.ManyToManyField(EpisodicMemory, blank=True)
    related_orders = models.JSONField(default=list)
    
    class Meta:
        db_table = 'ai_periodic_memory'
        ordering = ['-confidence', '-occurrence_count']
        indexes = [
            models.Index(fields=['user', 'pattern_type']),
            models.Index(fields=['frequency']),
            models.Index(fields=['confidence']),
            models.Index(fields=['last_observed']),
        ]
    
    def __str__(self):
        return f"Periodic: {self.title} ({self.pattern_type})"


class SemanticMemory(MemoryBase):
    """
    Semantic Memory: Facts, knowledge, and conceptual information
    Stores general knowledge, facts, and learned information
    """
    KNOWLEDGE_TYPES = [
        ('fact', 'Fact'),
        ('rule', 'Rule'),
        ('preference', 'Preference'),
        ('relationship', 'Relationship'),
        ('concept', 'Concept'),
        ('procedure', 'Procedure'),
        ('constraint', 'Constraint'),
    ]
    
    # Core identification
    knowledge_id = models.CharField(max_length=100, unique=True)
    
    # Knowledge content
    knowledge_type = models.CharField(max_length=50, choices=KNOWLEDGE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.JSONField(default=dict)  # Structured knowledge content
    
    # Knowledge characteristics
    confidence = models.FloatField(default=0.8)  # How confident we are in this knowledge
    source = models.CharField(max_length=100)  # Where this knowledge came from
    last_verified = models.DateTimeField(default=timezone.now)
    verification_count = models.IntegerField(default=1)
    
    # Knowledge relationships
    related_concepts = models.JSONField(default=list)  # Related concept IDs
    dependencies = models.JSONField(default=list)  # Knowledge this depends on
    contradictions = models.JSONField(default=list)  # Conflicting knowledge
    
    # Context and scope
    scope = models.CharField(max_length=100, default='global')  # global, user-specific, etc.
    domain = models.CharField(max_length=100)  # delivery, customer_service, etc.
    
    # Retrieval metadata
    tags = models.JSONField(default=list)
    keywords = models.JSONField(default=list)
    embeddings = models.JSONField(default=list)  # Vector embeddings
    
    class Meta:
        db_table = 'ai_semantic_memory'
        ordering = ['-confidence', '-verification_count']
        indexes = [
            models.Index(fields=['knowledge_type', 'domain']),
            models.Index(fields=['confidence']),
            models.Index(fields=['scope']),
            models.Index(fields=['last_verified']),
        ]
    
    def __str__(self):
        return f"Semantic: {self.title} ({self.knowledge_type})"


class ConversationContext(MemoryBase):
    """
    Conversation Context: Manages context windows for long conversations
    """
    # Core identification
    context_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100)
    conversation_id = models.CharField(max_length=100)
    
    # Context content
    current_context = models.JSONField(default=dict)  # Current conversation state
    context_history = models.JSONField(default=list)  # Previous context states
    context_summary = models.TextField(null=True, blank=True)  # Summarized context
    
    # Context metadata
    message_count = models.IntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    context_size = models.IntegerField(default=0)  # Current context size in tokens
    
    # Memory references
    relevant_episodic_memories = models.ManyToManyField(EpisodicMemory, blank=True)
    relevant_periodic_memories = models.ManyToManyField(PeriodicMemory, blank=True)
    relevant_semantic_memories = models.ManyToManyField(SemanticMemory, blank=True)
    
    # Context management
    max_context_size = models.IntegerField(default=4000)  # Max tokens in context
    compression_threshold = models.IntegerField(default=3000)  # When to compress context
    
    class Meta:
        db_table = 'ai_conversation_context'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'session_id']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"Context: {self.conversation_id} ({self.message_count} messages)"


class MemoryRetrievalLog(MemoryBase):
    """
    Memory Retrieval Log: Tracks how memories are retrieved and used
    """
    # Core identification
    retrieval_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Retrieval details
    query = models.TextField()  # What was searched for
    retrieval_type = models.CharField(max_length=50)  # episodic, periodic, semantic
    retrieved_memories = models.JSONField(default=list)  # IDs of retrieved memories
    
    # Retrieval results
    relevance_scores = models.JSONField(default=dict)  # Memory ID -> relevance score
    retrieval_time = models.FloatField()  # Time taken to retrieve
    success = models.BooleanField(default=True)
    
    # Usage tracking
    memories_used = models.JSONField(default=list)  # Which memories were actually used
    context_updated = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ai_memory_retrieval_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'retrieval_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"Retrieval: {self.retrieval_type} ({len(self.retrieved_memories)} memories)"


class MemoryConsolidation(MemoryBase):
    """
    Memory Consolidation: Tracks how memories are consolidated and updated
    """
    CONSOLIDATION_TYPES = [
        ('episodic_to_periodic', 'Episodic to Periodic'),
        ('episodic_to_semantic', 'Episodic to Semantic'),
        ('periodic_update', 'Periodic Update'),
        ('semantic_update', 'Semantic Update'),
        ('memory_merge', 'Memory Merge'),
        ('memory_forgetting', 'Memory Forgetting'),
    ]
    
    # Core identification
    consolidation_id = models.CharField(max_length=100, unique=True)
    
    # Consolidation details
    consolidation_type = models.CharField(max_length=50, choices=CONSOLIDATION_TYPES)
    source_memories = models.JSONField(default=list)  # Source memory IDs
    target_memory = models.CharField(max_length=100, null=True, blank=True)  # Target memory ID
    
    # Consolidation process
    trigger_reason = models.TextField()  # Why this consolidation happened
    consolidation_data = models.JSONField(default=dict)  # Data about the consolidation
    confidence_change = models.FloatField(default=0.0)  # Change in confidence
    
    # Results
    success = models.BooleanField(default=True)
    new_memories_created = models.IntegerField(default=0)
    memories_updated = models.IntegerField(default=0)
    memories_archived = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'ai_memory_consolidation'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consolidation_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"Consolidation: {self.consolidation_type} ({self.consolidation_id})"
