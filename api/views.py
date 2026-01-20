import os
import base64
import pdfkit
from pdfkit.configuration import Configuration   
from django.conf import settings
from django.template.loader import render_to_string
from django.template.loader import get_template

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

from .models import Agent, Mission
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from django.db import models

from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import api_view

from django.db.models.functions import ExtractMonth, ExtractYear
from .serializers import MissionMensuelleSerializer


class MissionGeneratePdfView(APIView):
    permission_classes = []

    

    def post(self, request):
        data = request.data.copy()  # copie pour modification

        # --- Infos agent ---
        if "agent" in data and data["agent"]:
            try:
                agent_obj = Agent.objects.get(id=data["agent"])
                data["agent_nom"] = agent_obj.nom
                data["agent_fonction"] = agent_obj.fonction
            except Agent.DoesNotExist:
                data["agent_nom"] = "Inconnu"
                data["agent_fonction"] = ""

        # --- Infos créateur ---
        if "cree_par" in data and data["cree_par"]:
            try:
                cree_par_obj = Agent.objects.get(id=data["cree_par"])
                data["cree_par_nom"] = cree_par_obj.nom
                data["cree_par_fonction"] = cree_par_obj.fonction
            except Agent.DoesNotExist:
                data["cree_par_nom"] = "Inconnu"
                data["cree_par_fonction"] = ""

        image_path = os.path.join(settings.BASE_DIR, "templates", "repoblika.png")
        repoblika_b64 = ""
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                repoblika_b64 = base64.b64encode(img_file.read()).decode("utf-8")
        

        data["repoblika_b64"] = repoblika_b64

        # --- Charger le template HTML ---
        template = get_template("mission_template.html")
        html = template.render(data)

        # --- Configuration wkhtmltopdf ---
        config = Configuration(
            wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        )

        # --- Génération PDF ---
        pdf = pdfkit.from_string(
            html,
            False,  # retourner le PDF en mémoire
            options={
                "page-size": "A4",
                "encoding": "UTF-8",
                "margin-top": "15mm",
                "margin-bottom": "15mm",
                "margin-left": "10mm",
                "margin-right": "10mm",
            },
            configuration=config
        )

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=mission.pdf"
        return response


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        agent = serializer.save()  # récupère l’instance créée

        # Maintenant tu accèdes aux champs de l'instance
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
                    'fonction': user.fonction,
                    'direction': user.direction,
                    'photo': user.photo.url if user.photo else None,
                    'is_staff': user.is_staff,
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

        # Préparer les données pour le template
        data = {
            "cree_le": mission.cree_le.strftime("%d/%m/%Y") if mission.cree_le else "",
            "objet": mission.objet,
            "lieu": mission.lieu,
            "date_depart": mission.date_depart.strftime("%d/%m/%Y") if mission.date_depart else "",
            "date_retour": mission.date_retour.strftime("%d/%m/%Y") if mission.date_retour else "",
            "description": mission.description,
            "cree_par": mission.cree_par.id if mission.cree_par else "",
            "cree_par_nom": mission.cree_par.nom if mission.cree_par else "",
            "agent_nom": mission.agent.nom if mission.agent else "",
            "agent_email": mission.agent.email if mission.agent else "",
            "agent_fonction": mission.agent.fonction if mission.agent else "",
            "agent_direction": mission.agent.get_direction_display() if mission.agent else "",
            "agent_matricule": mission.agent.matricule if mission.agent else "",
            "nbr_jours": mission.nbr_jours,
            "background_b64": "",
        }

        # Charger le template HTML
        template = get_template("mission_template.html")  # notre modèle lettre
        html = template.render(data)

        # Configurer pdfkit avec chemin complet de wkhtmltopdf
        config = Configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

        # Générer le PDF
        pdf = pdfkit.from_string(
            html, 
            False,  # False = renvoie bytes
            options={
                "page-size": "A4",
                "encoding": "UTF-8",
                "margin-top": "15mm",
                "margin-bottom": "15mm",
                "margin-left": "15mm",
                "margin-right": "15mm",
            },
            configuration=config
        )

        # Retourner le PDF en réponse
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename=mission_{mission.id}.pdf'
        return response
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


class OMissionGeneratePdfView(APIView):
    permission_classes = []

    def post(self, request):
        mission_id = request.data.get("id")
        mission = Mission.objects.select_related("agent").get(id=mission_id)
        agent = mission.agent

        # Convertir l'image en base64
        image_path = os.path.join(settings.BASE_DIR, "templates", "mission.jpg")
        background_b64 = ""
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                background_b64 = base64.b64encode(img_file.read()).decode("utf-8")

        context = {
            "id": mission.id,
            "objet": mission.objet,
            "lieu": mission.lieu,
            "nbr_jours": mission.nbr_jours,
            "cree_le": mission.cree_le.strftime("%d/%m/%Y"),
            "agent_nom": agent.nom,
            "agent_matricule": agent.matricule,
            "agent_fonction": agent.fonction,
            "agent_direction": agent.get_direction_display(),
            "background_b64": background_b64,
        }

        html = render_to_string("ordre_de_mission.html", context)

        # Configuration wkhtmltopdf
        config = Configuration(
            wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        )

        pdf = pdfkit.from_string(
            html,
            False,
            options={
                "page-size": "A4",
                "encoding": "UTF-8",
            },
            configuration=config
        )

        response = HttpResponse(pdf, content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename="ordre_de_mission.pdf"'
        return response
class AgentsEnCoursAPIView(APIView):
    """
    Retourne la liste des agents, triés pour afficher ceux ayant des missions en cours avant les autres
    """
    def get(self, request):
        # Annotation : on compte le nombre de missions en cours par agent
        agents = Agent.objects.annotate(
            missions_en_cours_count=Count('missions', filter=Q(missions__progression='En cours'))
        ).order_by('-missions_en_cours_count', 'nom')  # Tri : d'abord ceux avec missions en cours, puis par nom

        serializer = AgentSerializer(agents, many=True)
        return Response(serializer.data)

class TotalMissionsEnCoursAPIView(APIView):
    """
    Retourne le nombre total de missions en cours
    """
    def get(self, request):
        total = Mission.objects.filter(progression='En cours').count()
        return Response({"total_missions_en_cours": total})

class MissionsParDirectionAPIView(APIView):
    # permission_classes = [AllowAny]
    def get(self, request):
        stats = (
            Mission.objects
            .values("agent__direction")
            .annotate(total=Count("id"))
            .order_by("agent__direction")
        )
        return Response(stats)



class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ici, on ne fait rien côté serveur, juste informer le client
        return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)

class MissionsParMoisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mois = request.query_params.get('mois')
        annee = request.query_params.get('annee')

        missions = Mission.objects.filter(status='Approuvée')

        if mois:
            missions = missions.annotate(
                mois=ExtractMonth('date_depart')
            ).filter(mois=mois)

        if annee:
            missions = missions.annotate(
                annee=ExtractYear('date_depart')
            ).filter(annee=annee)

        serializer = MissionMensuelleSerializer(missions, many=True)
        return Response(serializer.data)        

# class OMissionGeneratePdfView(APIView):
    permission_classes = []  # Pas de restriction pour l'instant

    def post(self, request):
        mission_id = request.data.get("id")
        mission = Mission.objects.select_related("agent").get(id=mission_id)
        agent = mission.agent

        def image_to_base64(path):
            if not path or not os.path.exists(path):
                return ""
            with open(path, "rb") as img:
                return base64.b64encode(img.read()).decode("utf-8")

        # Chemin vers l'image de fond
        background_path = os.path.join(settings.BASE_DIR, "templates", "mission.jpg")
        background_b64 = image_to_base64(background_path)

        # Contexte pour le template
        context = {
            "id": mission.id,
            "objet": mission.objet,
            "lieu": mission.lieu,
            "nbr_jours": mission.nbr_jours,
            "cree_le": mission.cree_le.strftime("%d/%m/%Y"),

            "agent_nom": agent.nom,
            "agent_matricule": agent.matricule,
            "agent_fonction": agent.fonction,
            "agent_direction": agent.get_direction_display(),
            "background_b64": background_b64,
        }

        # Rendu HTML
        html_string = render_to_string("ordre_de_mission.html", context)

        # Création PDF avec WeasyPrint
        html = HTML(string=html_string, base_url=settings.BASE_DIR)
        pdf = html.write_pdf(stylesheets=[CSS(string="""
            @page { size: A4; margin: 0; }
            body { font-family: Arial, Helvetica, sans-serif; font-size: 12px; margin: 0; padding: 0; }
        """)])

        # Retourner la réponse
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="ordre_de_mission.pdf"'
        return response