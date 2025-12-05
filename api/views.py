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

class MissionGeneratePdfView(APIView):
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