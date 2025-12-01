from django.db import models

class Agent(models.Model):
    nom = models.CharField(max_length=100)
    fonction = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    email = models.EmailField()
    mdp = models.CharField(max_length=100)
    DIRECTION_CHOICES = [
        ('DCSI', 'Direction de la Communication et des Systèmes d\'Information'),
        ('DAF', 'Direction Administrative et Financière'),
        ('DPSE', 'Direction de la Planification et du Suivi-Evaluation'),
        ('DAJC', 'Direction des Affaires Juridiques et du Contentieux'),
        ('DRH', 'Direction des Ressources Humaines'),
        ('DGGE', 'Direction Générale de la Gouvernance Environnementale'),
        ('DGDD', 'Direction Générale du Développement Durable'),
        ('ULC', 'Unité de Lutte contre la Corruption'),
    ]
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    role_choices = [
        ('agent', 'Agent'),
        ('chef', 'Chef'),
        ('directeur', 'Directeur'),
    ]
    role = models.CharField(max_length=10, default='agent', choices=role_choices)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)