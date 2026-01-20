from django.contrib import admin
from .models import Agent, Mission

admin.site.register(Agent)

@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    readonly_fields = ('nbr_jours', 'cree_par_nom', 'progression')  # champs calculés
    list_display = ('objet', 'agent', 'nbr_jours', 'progression', 'status')


