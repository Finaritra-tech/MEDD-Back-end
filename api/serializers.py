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
    cree_par_nom = serializers.CharField(read_only=True)
    # destinataire = serializers.PrimaryKeyRelatedField(
    #     queryset=Agent.objects.filter(is_staff=True),
    #     allow_null=True,
    #     required=False
    # )


    class Meta:
        model = Mission
        fields = [
            'id', 'agent', 'cree_par', 'cree_par_nom', 'objet', 'lieu',
            'date_depart', 'date_retour', 'nbr_jours', 'status',
            'description', 'motif_rejet', 'approuve_par', 
            # 'destinataire',
        ]