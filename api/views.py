from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.mail import send_mail
from .serializers import AgentSerializer, LoginSerializer, MissionSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io

from .models import Agent, Mission
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models

class AgentViewSet(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated]
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        password = serializer.validated_data.pop('password')  # Récupère et retire le mot de passe
        agent = serializer.save()
        agent.set_password(password)  # Hash le mot de passe
        agent.save()

        # Envoi email de confirmation
        subject = "Inscription réussie"
        message = f"Bonjour {agent.nom},\n\nVotre compte a été créé avec succès."
        from_email = "MEDD@gmail.com"
        recipient_list = [agent.email]

        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )

class LoginView(APIView):

    # permission_classes = [AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, email=email, password=password)

        if user is not None:
            # Générer JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'nom': user.nom,
                    'email': user.email,
                    'is_staff': user.is_staff
                }
            })

        return Response({'detail': 'Email ou mot de passe incorrect'}, status=status.HTTP_401_UNAUTHORIZED)



class MissionViewSet(viewsets.ModelViewSet):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Mission.objects.filter(models.Q(cree_par=user) | models.Q(agent=user))

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)


class MissionGeneratePdfView(APIView):
    permission_classes = []

    def post(self, request):
        data = request.data.copy()  # important : copy pour modification

        # --- charger les infos agent ---
        if "agent" in data and data["agent"]:
            try:
                agent_obj = Agent.objects.get(id=data["agent"])
                data["agent_nom"] = agent_obj.nom
                data["agent_fonction"] = agent_obj.fonction
            except Agent.DoesNotExist:
                data["agent_nom"] = "Inconnu"
                data["agent_fonction"] = ""

        # --- charger infos créateur ---
        if "cree_par" in data and data["cree_par"]:
            try:
                cree_par_obj = Agent.objects.get(id=data["cree_par"])
                data["cree_par_nom"] = cree_par_obj.nom
                data["cree_par_fonction"] = cree_par_obj.fonction
            except Agent.DoesNotExist:
                data["cree_par_nom"] = "Inconnu"
                data["cree_par_fonction"] = ""

        # Charger template PDF
        template = get_template("mission_template.html")
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)
        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=mission.pdf"
        return response

    permission_classes = []

    def post(self, request):
        data = request.data.copy()  # important : copy pour pouvoir écrire dedans

        # --- charger les infos agent ---
        if "agent" in data and data["agent"]:
            try:
                agent_obj = Agent.objects.get(id=data["agent"])
                data["agent_nom"] = agent_obj.nom
                data["agent_fonction"] = agent_obj.fonction
            except Agent.DoesNotExist:
                data["agent_nom"] = "Inconnu"
                data["agent_fonction"] = ""

        # --- charger infos créateur ---
        if "cree_par" in data and data["cree_par"]:
            try:
                cree_par_obj = Agent.objects.get(id=data["cree_par"])
                data["cree_par_nom"] = cree_par_obj.nom
                data["cree_par_fonction"] = cree_par_obj.fonction
            except Agent.DoesNotExist:
                data["cree_par_nom"] = "Inconnu"
                data["cree_par_fonction"] = ""

        # Charger template PDF
        template = get_template("mission_template.html")
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)
        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=mission.pdf"
        return response

    permission_classes = []  # tu peux mettre IsAuthenticated si besoin

    def post(self, request):
        """
        Génère un PDF à partir des données envoyées dans request.data
        """
        data = request.data

        # Charger le template HTML
        template = get_template("mission_template.html")  # à créer dans templates/
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)

        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=mission.pdf"
        return response