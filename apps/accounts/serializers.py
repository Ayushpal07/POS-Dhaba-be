from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'role', 'business', 'business_name', 'is_active')
        read_only_fields = ('business',)
