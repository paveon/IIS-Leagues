from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.urls import reverse
from . import views

app_name = 'leagues'
urlpatterns = [
    path('', RedirectView.as_view(pattern_name='leagues:index', permanent=False)),
    path('index/', views.GamesView.as_view(), name='index'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('genre/<slug:slug>/', views.GenreDetailView.as_view(), name='genre_detail'),
    path('player/<slug:slug>/', views.PlayerDetailView.as_view(), name='player_detail'),
    path('team/<slug:slug>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('clan/<slug:slug>/', views.ClanDetailView.as_view(), name='clan_detail'),
    path('game/<slug:slug>/', views.GameDetailView.as_view(), name='game_detail'),
    path('match/<pk>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('games/', views.GamesView.as_view(), name='games'),
    path('social/', views.SocialView.as_view(), name='social'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('tournaments/', views.TournamentView.as_view(), name='tournaments'),
    path('tournament/<slug:slug>/', views.TournamentDetailView.as_view(), name='tournament_detail'),
    path('gamemode/<slug:slug>/', views.GameModeDetailView.as_view(), name='game_mode_detail')
]
