from django.db import models
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

GRID_SIZE = 8


def validate_pixels(value):
    ok = (isinstance(value, list) and len(value) == GRID_SIZE
          and all(isinstance(r, list) and len(r) == GRID_SIZE for r in value))
    if not ok:
        raise ValidationError("La grille doit faire 8 lignes de 8 valeurs.")
    if any(not isinstance(v, int) or not 0 <= v <= 255 for r in value for v in r):
        raise ValidationError("Chaque pixel est un entier entre 0 (noir) et 255 (blanc).")


def validate_kernel(value):
    ok = (isinstance(value, list) and len(value) == 3
          and all(isinstance(r, list) and len(r) == 3 for r in value))
    if not ok:
        raise ValidationError("Le kernel doit être une matrice 3×3.")
    if any(not isinstance(v, (int, float)) for r in value for v in r):
        raise ValidationError("Le kernel ne contient que des nombres.")


class MagicLens(models.Model):
    """Une loupe magique = un kernel 3×3."""
    name = models.CharField("Nom", max_length=60)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    icon = models.CharField(max_length=10, default="🔍")
    short_description = models.CharField(max_length=120, blank=True)
    bubble_text = models.CharField(
        "Phrase de l'animation", max_length=160, blank=True,
        help_text="Ex : Je regarde ces 9 pixels et je fais la moyenne.")
    kernel = models.JSONField(validators=[validate_kernel],
                              help_text="Ex : [[1,1,1],[1,1,1],[1,1,1]]")
    divisor = models.FloatField(default=1.0, help_text="Doit être différent de 0")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Loupe magique"
        verbose_name_plural = "Loupes magiques"

    def __str__(self):
        return self.name

    def clean(self):
        if self.divisor == 0:
            raise ValidationError({"divisor": "Le diviseur ne peut pas être 0."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Drawing(models.Model):

    title = models.CharField("Titre", max_length=100)
    pixels = models.JSONField(validators=[validate_pixels])
    is_template = models.BooleanField("Modèle pré-fait", default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Dessin"
        verbose_name_plural = "Dessins"

    def __str__(self):
        return self.title


class Game(models.Model):
    """Une partie de 5 questions."""
    player_name = models.CharField("Pseudo", max_length=30)
    points = models.PositiveIntegerField(default=0)
    # Stocke les 5 questions côté serveur 
    questions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-points", "created_at"]
        verbose_name = "Partie"
        verbose_name_plural = "Parties"

    def __str__(self):
        return f"{self.player_name} : {self.points} pts"


class Attempt(models.Model):
    """Une réponse du joueur à une question."""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="attempts")
    question_index = models.PositiveSmallIntegerField(default=0)   
    drawing = models.ForeignKey(Drawing, on_delete=models.PROTECT, related_name="attempts")
    target_lens = models.ForeignKey(MagicLens, on_delete=models.PROTECT,
                                    related_name="as_target")
    chosen_lens = models.ForeignKey(MagicLens, on_delete=models.PROTECT, null=True,
                                    blank=True, related_name="as_choice",
                                    help_text="Vide si le temps est écoulé")
    is_correct = models.BooleanField()
    seconds = models.FloatField("Temps de réponse (s)")
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["created_at"]
        constraints = [                                            
            models.UniqueConstraint(fields=["game", "question_index"],
                                    name="one_answer_per_question")
        ]
        verbose_name = "Réponse"
        verbose_name_plural = "Réponses"

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.game.player_name}"