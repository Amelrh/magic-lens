from django.core.management.base import BaseCommand
from lens.models import Drawing, MagicLens

LEVELS = [0, 85, 170, 255]  # noir → blanc


def grid(rows):
    return [[LEVELS[int(c)] for c in row] for row in rows]


LENSES = [
    {
        "slug": "flou",
        "name": "Loupe Brouillard",
        "icon": "🌫️",
        "order": 1,
        "short_description": "Mélange chaque pixel avec ses voisins : l'image devient douce.",
        "bubble_text": "Je regarde ces 9 pixels et je fais la moyenne : tout devient doux.",
        "kernel": [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
        "divisor": 9,
    },
    {
        "slug": "contour",
        "name": "Loupe Contour",
        "icon": "✏️",
        "order": 2,
        "short_description": "Allume les endroits où la couleur change d'un coup.",
        "bubble_text": "Je compare le pixel du milieu à ses voisins : s'il est différent, je l'allume !",
        "kernel": [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]],
        "divisor": 1,
    },
    {
        "slug": "eclat",
        "name": "Loupe Éclat",
        "icon": "✨",
        "order": 3,
        "short_description": "Renforce les différences : l'image devient plus nette.",
        "bubble_text": "J'accentue le pixel du milieu par rapport à ses voisins : plus de contraste !",
        "kernel": [[0, -1, 0], [-1, 5, -1], [0, -1, 0]],
        "divisor": 1,
    },
    {
        "slug": "lignes",
        "name": "Loupe Lignes",
        "icon": "➖",
        "order": 4,
        "short_description": "Repère les lignes couchées (horizontales).",
        "bubble_text": "Je cherche une ligne couchée au milieu de ces 9 pixels.",
        "kernel": [[-1, -1, -1], [2, 2, 2], [-1, -1, -1]],
        "divisor": 1,
    },
]

DRAWINGS = [
    ("Smiley", [
        "00333300", "03222230", "32022023", "32222223",
        "32022023", "32200223", "03222230", "00333300"
    ]),
    ("Maison", [
        "00033000", "00322300", "03222230", "32222223",
        "01111110", "01311310", "01100110", "01100110"
    ]),
    ("Cœur", [
        "02200220", "23322332", "23333332", "23333332",
        "02333320", "00233200", "00023000", "00000000"
    ]),
    ("Dégradé", [
        "00001122", "00011222", "00112223", "01122233",
        "11222333", "12223333", "22233333", "22333333"
    ]),
]


class Command(BaseCommand):
    help = "Remplit la base avec les loupes et les dessins modèles (peut être relancé sans risque)."

    def handle(self, *args, **options):
        for data in LENSES:
            data = data.copy()
            slug = data.pop("slug")
            obj, created = MagicLens.objects.update_or_create(slug=slug, defaults=data)
            obj.full_clean()
            self.stdout.write(f"{'Créée' if created else 'Mise à jour'} : {obj.name}")

        for title, rows in DRAWINGS:
            obj, created = Drawing.objects.update_or_create(
                title=title,
                defaults={"pixels": grid(rows), "is_template": True, "is_active": True}
            )
            obj.full_clean()
            self.stdout.write(f"{'Créé' if created else 'Mis à jour'} : {obj.title}")

        self.stdout.write(self.style.SUCCESS("Base remplie avec succès."))