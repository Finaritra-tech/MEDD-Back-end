from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from datetime import timedelta

class AgentManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class Agent(AbstractBaseUser, PermissionsMixin):
    nom = models.CharField(max_length=100)
    fonction = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)
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
     # Champs Django obligatoires
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom"]

    objects = AgentManager()

    def __str__(self):
        return self.nom

class Mission(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='missions')
    
    cree_par = models.ForeignKey(
        Agent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='missions_creees'
    )
    cree_par_nom = models.CharField(max_length=100, blank=True, null=True)  # Nouveau champ

    objet = models.CharField(max_length=255)
    lieu = models.CharField(max_length=100)
    date_depart = models.DateField()
    date_retour = models.DateField()

    nbr_jours = models.IntegerField(editable=False)   

    status_choices = [
        ('En attente', 'En attente'),
        ('Approuvée', 'Approuvée'),
        ('Rejetée', 'Rejetée'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='En attente')

    description = models.TextField(blank=True, null=True)
    motif_rejet = models.TextField(blank=True, null=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    approuve_par = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="missions_approuvees"
    )

    def save(self, *args, **kwargs):
        # Calcul du nombre de jours
        if self.date_depart and self.date_retour:
            self.nbr_jours = (self.date_retour - self.date_depart).days + 1
        
        # Remplissage automatique du nom du créateur
        if self.cree_par:
            self.cree_par_nom = self.cree_par.nom
        
        super().save(*args, **kwargs)

    def is_directe(self):
        """Retourne True si la mission n'a PAS été créée par l'agent lui-même"""
        return self.cree_par and self.cree_par != self.agent
