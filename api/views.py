from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.mail import send_mail
from .serializers import AgentSerializer, LoginSerializer, MissionSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.decorators import action

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io

from .models import Agent, Mission
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models

from django.utils import timezone
from django.db.models import Count, Q

class AgentViewSet(viewsets.ModelViewSet):
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
        today = timezone.now().date()

        # 🔹 Mise à jour automatique de la progression (DEV)
        Mission.objects.filter(
            date_retour__lt=today,
            progression="En cours"
        ).update(progression="Terminée")

        qs = Mission.objects.filter(
            models.Q(cree_par=user) |
            models.Q(agent=user) |
            models.Q(destinataire=user)
        ).distinct()

        # 🔹 Filtrage par type via query params
        if self.request.query_params.get("type") == "destinataire":
            qs = qs.filter(destinataire=user)

        return qs

        
    @action(detail=True, methods=["get"], url_path="pdf")
    def generate_pdf(self, request, pk=None):
        mission = self.get_object()

        data = {
            "objet": mission.objet,
            "lieu": mission.lieu,
            "date_depart": mission.date_depart,
            "date_retour": mission.date_retour,
            "description": mission.description,
            "cree_par": mission.cree_par.id if mission.cree_par else "",
            "cree_par_nom": mission.cree_par.nom if mission.cree_par else "",
        }

        template = get_template("mission_template.html")
        html = template.render(data)

        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)

        if pdf.err:
            return Response({"error": "Erreur génération PDF"}, status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename=mission_{mission.id}.pdf'
        return response

    @action(detail=True, methods=["post"], url_path="approuver")
    def approuver(self, request, pk=None):
        mission = self.get_object()
        mission.status = "Approuvée"
        mission.approuve_par = request.user
        mission.save()
        return Response({"message": "Mission approuvée"})

    @action(detail=True, methods=["post"], url_path="rejeter")
    def rejeter(self, request, pk=None):
        mission = self.get_object()
        mission.status = "Rejetée"
        mission.motif_rejet = request.data.get("motif_rejet", "")
        mission.approuve_par = request.user
        mission.save()
        return Response({"message": "Mission rejetée"})


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

    permission_classes = []  
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

class OMissionGeneratePdfView(APIView):
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
        template = get_template("ordre_de_mission.html")
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)
        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=om.pdf"
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
        template = get_template("ordre_de_mission.html")
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)
        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=om.pdf"
        return response

    permission_classes = []  # tu peux mettre IsAuthenticated si besoin

    def post(self, request):
        """
        Génère un PDF à partir des données envoyées dans request.data
        """
        data = request.data

        # Charger le template HTML
        template = get_template("ordre_de_mission.html")  # à créer dans templates/
        html = template.render(data)

        # Génération PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(io.StringIO(html), dest=result)

        if pdf.err:
            return HttpResponse("Erreur lors de la génération du PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=om.pdf"
        return response

class AgentsEnCoursAPIView(APIView):
    """
    Retourne la liste des agents ayant des missions en cours
    """
    def get(self, request):
        agents = Agent.objects.filter(missions__progression='En cours').distinct()
        serializer = AgentSerializer(agents, many=True)
        return Response(serializer.data)


class TotalMissionsEnCoursAPIView(APIView):
    """
    Retourne le nombre total de missions en cours
    """
    def get(self, request):
        total = Mission.objects.filter(progression='En cours').count()
        return Response({"total_missions_en_cours": total})
  