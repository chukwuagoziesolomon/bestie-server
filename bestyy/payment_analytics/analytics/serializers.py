from rest_framework import serializers
from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'icon', 'color', 'amount',
            'actor', 'target_type', 'target_id', 'metadata', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']

class TopDishSerializer(serializers.Serializer):
    dish_name = serializers.CharField()
    orders = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    change_pct = serializers.FloatField()

class OrderActivitySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    rejected = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    completed_change_pct = serializers.FloatField()
    rejected_change_pct = serializers.FloatField()

class DashboardAnalyticsSerializer(serializers.Serializer):
    order_activity = OrderActivitySerializer()
    top_dishes = TopDishSerializer(many=True)