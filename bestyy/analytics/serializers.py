from rest_framework import serializers

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