from rest_framework import serializers
from .models import Agent, Mission

class AgentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = Agent
        fields = ['id', 'nom', 'fonction', 'telephone', 'email', 'password', 'photo', 'is_staff', 'direction']
        read_only_fields = ['is_staff']

        
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'