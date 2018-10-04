from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.urls import reverse
from . import views

app_name = 'leagues'
urlpatterns = [
    path('', RedirectView.as_view(pattern_name='leagues:index', permanent=False)),
    path('index/', views.GamesView.as_view(), name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='leagues/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('genre/<slug:slug>/', views.DetailGenreView.as_view(), name='genre_detail'),
    path('game/<slug:slug>/', views.DetailGameView.as_view(), name='game_detail'),
    path('games/', views.GamesView.as_view(), name='games'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
]
