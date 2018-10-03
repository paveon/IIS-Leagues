from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'leagues'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('index/', views.IndexView.as_view(), name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='leagues/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('<slug:slug>', views.DetailGenreView.as_view(), name='genre_detail'),
    path('player/<slug:slug>', views.PlayerDetailView.as_view(), name='player_detail'),
    path('team/<slug:slug>', views.TeamDetailView.as_view(), name='team_detail'),
    path('clan/<slug:slug>', views.ClanDetailView.as_view(), name='clan_detail'),
    path('game/<slug:slug>/', views.DetailGameView.as_view(), name='game_detail'),
    path('games/', views.GamesView.as_view(), name='games'),
    path('social/', views.SocialView.as_view(), name='social'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
    path('<int:question_id>/vote/', views.vote, name='vote'),
]
