from django.shortcuts import render
from rest_framework import viewsets
from .models import Agent
from .serializers import AgentSerializer
from rest_framework.parsers import MultiPartParser, FormParser


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    parser_classes = (MultiPartParser, FormParser)