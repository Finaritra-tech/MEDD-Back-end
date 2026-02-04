from rest_framework import serializers
from .models import Agent, Mission


from rest_framework import serializers

class AgentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=6
    )
    missions_en_cours = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            'id', 'matricule','nom', 'fonction', 'telephone', 'email',
            'password', 'photo', 'is_staff', 'direction',
            'missions_en_cours', 'superieur_hierarchique'
        ]
        read_only_fields = ['is_staff', 'missions_en_cours']

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = Agent.objects.create_user(
            password=password,
            **validated_data
        )
        return user

    def get_missions_en_cours(self, obj):
        missions = obj.missions.filter(progression='En cours')
        return MissionEnCoursSerializer(missions, many=True).data

        
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MissionSerializer(serializers.ModelSerializer):
    cree_par_nom = serializers.CharField(read_only=True)

    # Filtrer les agents qui ne sont pas déjà en mission
    agent = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(is_active=True).exclude(
            missions__progression='En cours'
        )
    )

    destinataire = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(is_staff=True).exclude(
            missions__progression='En cours'
        ),
        allow_null=False,
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

    def validate_agent(self, value):
        if Mission.objects.filter(agent=value, progression='En cours').exists():
            raise serializers.ValidationError("Cet agent est déjà en mission en cours.")
        return value

    def validate_destinatairee(self, value):
        if value and Mission.objects.filter(agent=value, progression='En cours').exists():
            raise serializers.ValidationError("Le destinataire est déjà en mission en cours.")
        return value
# serializers.py

class MissionEnCoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ['id', 'objet', 'date_depart', 'date_retour', 'progression']
        read_only_fields = ['id', 'objet', 'date_depart', 'date_retour', 'progression']

# serializers.py

class MissionMensuelleSerializer(serializers.ModelSerializer):
    agent_nom = serializers.CharField(source='agent.nom', read_only=True)

    class Meta:
        model = Mission
        fields = [
            'id',
            'objet',
            'lieu',
            'agent_nom',
            'date_depart',
            'date_retour',
            'nbr_jours',
            'status',
        ]
