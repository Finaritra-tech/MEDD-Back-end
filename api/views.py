from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.mail import send_mail
from .serializers import AgentSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .serializers import LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Agent


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
