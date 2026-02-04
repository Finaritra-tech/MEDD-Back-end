from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from datetime import timedelta
from django.utils import timezone


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
    matricule = models.CharField(max_length=20, unique=True, null=True, blank=True, default="pas de matricule")
    nom = models.CharField(max_length=100)
    fonction = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)
    DIRECTION_CHOICES = [
        ('SG', 'Secrétariat Général'),
        ('cabinet','cabinet'),
        ('OC-DVOR', 'Organe de Coordination des actions stratégiques pour la Diplomatie Verte et des Organismes Rattachés'),
        ('PRMP', 'Personne Responsable des Marchés Publics'),
        ('DCSI', 'Direction de la Communication et des Systèmes d\'Information'),
        ('DAF', 'Direction Administrative et Financière'),
        ('DPSE', 'Direction de la Planification et du Suivi-Evaluation'),
        ('DAJC', 'Direction des Affaires Juridiques et du Contentieux'),
        ('DRH', 'Direction des Ressources Humaines'),
        ('DGGE', 'Direction Générale de la Gouvernance Environnementale'),
        ('DGDD', 'Direction Générale du Développement Durable'),
        ('ULC', 'Unité de Lutte contre la Corruption'),
        ('DREDD', 'Direction Régional de l\'Environnement et du Developpement Durable'),
        ('DDVP', 'Direction de la Diplomatie Verte et des Partenariats'),
        ('UCOR', 'Unité de Coordination des Organismes Rattachés'),
        ('UCREF', 'Unité de Coordination de la Recherche, de l\'Education et de la Formation'),
        ('DMFD','Direction du Mécanisme de Financement Durable'),
        ('DEVB', 'Direction d\'Appui à la Promotion de l\'Economie Verte et Bleue'),
        ('DPRIDDD', 'Direction de la Promotion de la Recherche et de l\'Intégration de la Démarche de Développement Durable'),
        ('DAPRNE', 'Directeur des Aires Protégées, des Ressources Naturelles renouvelables et des Ecosystème'),
        ('DRGPF' , 'Directeur de Reboisement et de la Gestion des Paysages et des Forêts'),
        ('DPDIDE', 'Directeur de la Gestion des Pollutions, des Déchets et de l\'Intégration de la Dimension Environnementale'),
    ]
    direction = models.CharField(max_length=7, choices=DIRECTION_CHOICES)
    superieur_hierarchique =models.CharField(max_length=20, unique=False, null=True, blank=True)
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
    cree_par_nom = models.CharField(max_length=100, blank=True, null=True)  

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
    status = models.CharField(max_length=20, choices=status_choices)

    description = models.TextField(blank=True, null=True)
    motif_rejet = models.TextField(blank=True, null=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    approuve_par = models.ForeignKey(
        Agent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="missions_approuvees"
    )

    destinataire = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='missions_destinees'
    )

    destinataire_nom = models.CharField(max_length=100, blank=True, null=True)

    destinatairee = models.ForeignKey(
        Agent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='destinatairee_missions'
    )

    PROGRESSION_CHOICES = [
        ('En cours', 'En cours'),
        ('Terminée', 'Terminée'),
    ]

    progression = models.CharField(
        max_length=20,
        choices=PROGRESSION_CHOICES,
        editable=False,
        default='En cours'
    )
    

    def save(self, *args, **kwargs):
        # Calcul du nombre de jours
        if self.date_depart and self.date_retour:
            self.nbr_jours = (self.date_retour - self.date_depart).days + 1
        
        # 🔹 Mise à jour automatique de la progression
            today = timezone.now().date()
            if self.date_retour < today:
                self.progression = 'Terminée'
            else:
                self.progression = 'En cours'
        # Remplissage automatique du nom du créateur
        if self.cree_par:
            self.cree_par_nom = self.cree_par.nom
        
        super().save(*args, **kwargs)

    def is_directe(self):
        """Retourne True si la mission n'a PAS été créée par l'agent lui-même"""
        return self.cree_par and self.cree_par != self.agent
