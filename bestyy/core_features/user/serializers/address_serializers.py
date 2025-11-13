"""
Address-related serializers.
"""
from rest_framework import serializers
from ..models import Address


class AddressSerializer(serializers.ModelSerializer):
    address_type = serializers.ChoiceField(
        choices=Address.ADDRESS_TYPE_CHOICES,
        error_messages={'required': 'Please select an address type.'}
    )
    address = serializers.CharField(
        source='street_address',
        required=True,
        error_messages={'required': 'Please enter the address.'}
    )
    city = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the city.'}
    )
    state = serializers.CharField(
        required=True,
        error_messages={'required': 'Please enter the state.'}
    )
    zip_code = serializers.CharField(
        source='postal_code',
        required=True,
        error_messages={'required': 'Please enter the zip code.'}
    )
    is_default = serializers.BooleanField(
        default=False,
        required=False
    )

    class Meta:
        model = Address
        fields = ['id', 'address_type', 'address', 'city', 'state', 'zip_code', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
            # Set default values for required fields that are not in the simplified payload
            validated_data['full_name'] = request.user.get_full_name() or request.user.username
            validated_data['phone_number'] = getattr(request.user.profile, 'phone', '')
        else:
            # For anonymous users, set default values
            validated_data['full_name'] = 'Anonymous User'
            validated_data['phone_number'] = ''
        return super().create(validated_data)




