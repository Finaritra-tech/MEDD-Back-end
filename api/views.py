from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser

from django.core.mail import send_mail
from .models import Agent
from .serializers import AgentSerializer



class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    parser_classes = (MultiPartParser, FormParser)


    def perform_create(self, serializer):
        agent = serializer.save()

        # Prépare l'email
        subject = "Inscription réussie"
        message = f"Bonjour {agent.nom},\n\nVotre compte a été créé avec succès."
        from_email = "MEDD@gmail.com" 
        recipient_list = [agent.email]

        # Envoi email  
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )