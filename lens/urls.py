from django.urls import path
from . import views

app_name = "lens"

urlpatterns = [
    path("", views.home, name="home"),
    path("play/", views.play, name="play"),

    path("api/drawing/<int:pk>/", views.get_drawing, name="get_drawing"),
    path("api/lens/<int:pk>/", views.get_lens, name="get_lens"),
    path("api/apply/", views.apply_lens, name="apply_lens"),

    path("api/game/start/", views.start_game, name="start_game"),
    path("api/game/answer/", views.submit_answer, name="submit_answer"),
    path("api/game/leaderboard/", views.leaderboard, name="leaderboard"),
]