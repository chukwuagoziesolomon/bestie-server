"""
Favorite-related serializers.
"""
from rest_framework import serializers
from user.models import Favorite
from .user_serializers import UserSerializer
from .menu_serializers import MenuItemSerializer
from .vendor_serializers import VendorProfileSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    food_item = MenuItemSerializer(read_only=True)
    vendor = VendorProfileSerializer(read_only=True)
    favorite_type = serializers.ChoiceField(
        choices=Favorite.FAVORITE_TYPES,
        error_messages={'required': 'Please select a favorite type.'}
    )

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'favorite_type', 'food_item', 'vendor', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        favorite_type = data.get('favorite_type')
        food_item = data.get('food_item')
        vendor = data.get('vendor')

        if favorite_type == 'food' and not food_item:
            raise serializers.ValidationError({'food_item': 'Food item is required for food favorites.'})
        elif favorite_type == 'venue' and not vendor:
            raise serializers.ValidationError({'vendor': 'Vendor is required for venue favorites.'})
        
        if food_item and vendor:
            raise serializers.ValidationError('Cannot have both food item and vendor in the same favorite.')

        return data




