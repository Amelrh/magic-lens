import json
import random
import math 
from django.db.models import Count            
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .imaging import apply_kernel
from .models import Attempt, Drawing, Game, MagicLens, validate_pixels


def _error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def home(request):
    return render(request, "lens/home.html")


@ensure_csrf_cookie
def play(request):
    return render(request, "lens/play.html", {
        "lenses": MagicLens.objects.filter(is_active=True),
        "drawings": Drawing.objects.filter(is_active=True, is_template=True),
    })


@require_GET
def get_drawing(request, pk):
    drawing = Drawing.objects.filter(pk=pk, is_active=True).first()
    if drawing is None:
        return _error("Dessin introuvable.", 404)
    return JsonResponse({"id": drawing.id, "title": drawing.title, "pixels": drawing.pixels})


@require_GET
def get_lens(request, pk):
    lens = MagicLens.objects.filter(pk=pk, is_active=True).first()
    if lens is None:
        return _error("Loupe introuvable.", 404)
    return JsonResponse({
        "id": lens.id,
        "name": lens.name,
        "icon": lens.icon,
        "short_description": lens.short_description,
        "bubble_text": lens.bubble_text,
        "kernel": lens.kernel,
        "divisor": lens.divisor,
    })


@require_POST
def apply_lens(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _error("JSON invalide.")
    if not isinstance(data, dict):
        return _error("JSON invalide.")

    lens_id = data.get("lens_id")
    if not isinstance(lens_id, int):
        return _error("lens_id manquant ou invalide.")
    lens = MagicLens.objects.filter(pk=lens_id, is_active=True).first()
    if lens is None:
        return _error("Loupe introuvable.", 404)

    if "pixels" in data:
        pixels = data["pixels"]
        try:
            validate_pixels(pixels)
        except ValidationError as e:
            return _error(e.messages[0])
    else:
        drawing_id = data.get("drawing_id")
        if not isinstance(drawing_id, int):
            return _error("drawing_id ou pixels manquant.")
        drawing = Drawing.objects.filter(pk=drawing_id, is_active=True).first()
        if drawing is None:
            return _error("Dessin introuvable.", 404)
        pixels = drawing.pixels

    return JsonResponse({
        "success": True,
        "pixels": apply_kernel(pixels, lens.kernel, lens.divisor),
        "bubble_text": lens.bubble_text,
    })


# ======================
#      MINI-JEU 
# ======================

@require_POST
def start_game(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _error("JSON invalide.")
    if not isinstance(data, dict):
        return _error("JSON invalide.")

    player_name = (data.get("player_name") or "").strip()
    if not player_name or len(player_name) > 30:
        return _error("Pseudo invalide (1 à 30 caractères).")

    drawings = list(Drawing.objects.filter(is_active=True, is_template=True))
    lenses = list(MagicLens.objects.filter(is_active=True))

    if len(drawings) < 1 or len(lenses) < 4:
        return _error("Pas assez de données dans la base (besoin d'au moins 4 loupes).", 500)

    server_questions = []
    client_questions = []

    for i in range(5):
        drawing = random.choice(drawings)
        target = random.choice(lenses)

        # Image résultat = dessin + loupe cible
        result_pixels = apply_kernel(drawing.pixels, target.kernel, target.divisor)

        # 4 choix (1 bonne + 3 mauvaises)
        wrong = [l for l in lenses if l.id != target.id]
        choices = random.sample(wrong, 3) + [target]
        random.shuffle(choices)

        # Version serveur (avec la réponse)
        server_questions.append({
            "index": i,
            "drawing_id": drawing.id,
            "target_lens_id": target.id,
            "result_pixels": result_pixels,
        })

        # Version client (sans la réponse)
        client_questions.append({
            "index": i,
            "result_pixels": result_pixels,
            "choices": [
                {"id": c.id, "name": c.name, "icon": c.icon}
                for c in choices
            ],
        })

    
    game = Game.objects.create(
        player_name=player_name,
        questions=server_questions,
    )

    return JsonResponse({
        "success": True,
        "game_id": game.id,
        "player_name": game.player_name,
        "questions": client_questions,
    })


@require_POST
def submit_answer(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _error("JSON invalide.")
    if not isinstance(data, dict):
        return _error("JSON invalide.")

    game_id = data.get("game_id")
    question_index = data.get("question_index")
    chosen_lens_id = data.get("chosen_lens_id")  
    seconds = data.get("seconds")
    
    if not isinstance(game_id, int) or isinstance(game_id, bool):
        return _error("game_id manquant.")
    if not isinstance(question_index, int) or not (0 <= question_index <= 4):
        return _error("question_index invalide (0 à 4).")
    if (not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
            or not math.isfinite(seconds) or seconds < 0 or seconds > 60):
        return _error("seconds invalide.")
    
    game = Game.objects.filter(pk=game_id).first()
    
    if game is None:
        return _error("Partie introuvable.", 404)

    if game.attempts.count() >= 5:
        return _error("Cette partie est déjà terminée.")
    if question_index >= len(game.questions):
        return _error("Question introuvable.")
    if game.attempts.filter(question_index=question_index).exists():
        return _error("Cette question a déjà été répondue.")
    secret = game.questions[question_index]
    target_lens_id = secret["target_lens_id"]
    drawing_id = secret["drawing_id"]
    pass

    # Récupérer la question secrète
    if question_index >= len(game.questions):
        return _error("Question introuvable.")
    secret = game.questions[question_index]
    target_lens_id = secret["target_lens_id"]
    drawing_id = secret["drawing_id"]

    if game.attempts.filter(points__gte=0).count() > question_index:
        # Méthode simple et robuste : on compte le nombre d'attempts
        if game.attempts.count() > question_index:
            return _error("Cette question a déjà été répondue.")

    drawing = Drawing.objects.filter(pk=drawing_id).first()
    target = MagicLens.objects.filter(pk=target_lens_id).first()
    if drawing is None or target is None:
        return _error("Données de question corrompues.", 500)

    chosen = None
    if chosen_lens_id is not None:
        if not isinstance(chosen_lens_id, int):
            return _error("chosen_lens_id invalide.")
        chosen = MagicLens.objects.filter(pk=chosen_lens_id).first()
        if chosen is None:
            return _error("Loupe choisie introuvable.", 404)

    is_correct = (chosen is not None and chosen.id == target.id)
    if is_correct:
        points = max(20, int(100 - seconds * 8))
    else:
        points = 0

    Attempt.objects.create(
        game=game,
        question_index=question_index,
        drawing=drawing,
        target_lens=target,
        chosen_lens=chosen,
        is_correct=is_correct,
        seconds=round(float(seconds), 2),
        points=points,
    )

    game.points = sum(a.points for a in game.attempts.all())
    game.save(update_fields=["points"])

    return JsonResponse({
        "success": True,
        "is_correct": is_correct,
        "points": points,
        "total_points": game.points,
        "correct_lens": {
            "id": target.id,
            "name": target.name,
            "icon": target.icon,
        },
    })


@require_GET
def leaderboard(request):
    games = Game.objects.annotate(n=Count("attempts")).filter(n__gte=5)[:10]
    return JsonResponse({
        "success": True,
        "leaderboard": [
            {
                "player_name": g.player_name,
                "points": g.points,
                "date": g.created_at.strftime("%d/%m/%Y %H:%M"),
            }
            for g in games
        ],
    })