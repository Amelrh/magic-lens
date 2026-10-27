import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .imaging import apply_kernel
from .models import Drawing, MagicLens, validate_pixels


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
    drawing = get_object_or_404(Drawing, pk=pk, is_active=True)
    return JsonResponse({"id": drawing.id, "title": drawing.title, "pixels": drawing.pixels})


@require_GET
def get_lens(request, pk):
    lens = get_object_or_404(MagicLens, pk=pk, is_active=True)
    return JsonResponse({
        "id": lens.id, "name": lens.name, "icon": lens.icon,
        "short_description": lens.short_description, "bubble_text": lens.bubble_text,
        "kernel": lens.kernel, "divisor": lens.divisor,
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