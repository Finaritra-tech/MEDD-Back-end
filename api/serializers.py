from rest_framework import serializers
from .models import Agent, Mission

class AgentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    missions_en_cours = serializers.SerializerMethodField()  # ✅ champ calculé

    class Meta:
        model = Agent
        fields = [
            'id', 'nom', 'fonction', 'telephone', 'email', 'password', 
            'photo', 'is_staff', 'direction', 'missions_en_cours'
        ]
        read_only_fields = ['is_staff', 'missions_en_cours']

    def get_missions_en_cours(self, obj):
        # Filtre les missions "En cours" pour cet agent
        missions = obj.missions.filter(progression='En cours')
        return MissionEnCoursSerializer(missions, many=True).data

        
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MissionSerializer(serializers.ModelSerializer):
    cree_par_nom = serializers.CharField(read_only=True)
    destinataire = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(is_staff=True),
        allow_null=True,
        required=False
    )
    destinataire_nom = serializers.CharField(read_only=True)

    class Meta:
        model = Mission
        fields = [
            'id', 'agent', 'cree_par', 'cree_par_nom', 'objet', 'lieu',
            'date_depart', 'date_retour', 'nbr_jours', 'status',
            'description', 'motif_rejet', 'approuve_par', 
            'destinataire', 'destinataire_nom', 'destinatairee', 'progression',
        ]

# serializers.py

class MissionEnCoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ['id', 'objet', 'date_depart', 'date_retour', 'progression']
        read_only_fields = ['id', 'objet', 'date_depart', 'date_retour', 'progression']
