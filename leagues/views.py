from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic, View
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.db import models
from .models import Player
from .forms import *


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('leagues:games'))


class SignupView(View):
    template_name = "leagues/signup.html"

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            new_user = authenticate(username=username, password=raw_password)
            player = Player.objects.create(nickname=username, first_name=username, last_name=username)
            player.user = new_user
            player.save()

            login(request, new_user)
            return HttpResponseRedirect(reverse('leagues:index'))
        else:
            return render(request, self.template_name, {'form': form})

    def get(self, request):
        form = UserCreationForm()
        return render(request, self.template_name, {'form': form})


class SettingsView(generic.TemplateView):
    template_name = "leagues/settings.html"

    def __init__(self):
        super().__init__()
        self.context = []
        self.forms = [
            (Game, GameForm),
            (Genre, GenreForm),
            (GameMode, GameModeForm),
            (Player, PlayerForm),
        ]

        self.post_actions = {
            'game_create': self.game_create,
            'game_edit': self.game_edit,
            'genre_create': self.genre_create,
            'genre_edit': self.genre_edit,
            'gamemode_create': self.gamemode_create,
            'gamemode_edit': self.gamemode_edit,
            'player_create': self.player_create,
            'player_edit': self.player_edit,
        }

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        for form in self.forms:
            edit_forms = []
            model_class = form[0]
            model_name = model_class.__name__.lower()
            form_class = form[1]
            for obj in model_class.objects.all():
                prefix = model_name + '_edit_' + str(obj.id)
                edit_forms.append(form_class(instance=obj, prefix=prefix))
            self.context[model_name + '_edit_forms'] = edit_forms
            self.context[model_name + '_form'] = form_class(prefix=model_name + '_form')
            self.context[model_name + '_list'] = model_class.objects.all()

        return self.context

    def process_edit_form(self, model_class, form_class):
        model_name = model_class.__name__.lower()
        prefix = model_name + '_edit_'
        model_object = model_class.objects.get(pk=self.request.POST['object_id'])
        edit_form = form_class(self.request.POST, instance=model_object, prefix=prefix + str(model_object.id))
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()
            return HttpResponseRedirect(reverse('leagues:settings'))
        form_list = self.context[prefix + 'forms']
        form_list[:] = [edit_form if x.instance == model_object else x for x in form_list]
        raise ValidationError(edit_form.__name__ + ' validation failed')

    def process_create_form(self, model_class, form_class):
        model_name = model_class.__name__
        create_form = form_class(self.request.POST, prefix=model_name.lower() + '_form')
        if create_form.is_bound and create_form.is_valid():
            object_name = create_form.cleaned_data['name']
            if not model_class.objects.filter(name=object_name).exists():
                # commit=False doesn't save new model object directly into the DB
                # so we can do additional processing before storing it in the DB with save method of model object
                model_object = create_form.save(commit=False)

                # ... do additional processing

                model_object.save()  # save object do DB
                create_form.save_m2m()  # need to save relations manually with commit=False
                return HttpResponseRedirect(reverse('leagues:settings'))
            return ValidationError('{0} object with name \'{1}\' already exists'.format(model_name, object_name))
        self.context[model_name.lower() + '_form'] = create_form
        raise ValidationError(create_form.__class__.__name__ + ' validation failed')

    def genre_create(self):
        return self.process_create_form(Genre, GenreForm)

    def genre_edit(self):
        return self.process_edit_form(Genre, GenreForm)

    def game_create(self):
        return self.process_create_form(Game, GameForm)

    def game_edit(self):
        return self.process_edit_form(Game, GameForm)

    def gamemode_create(self):
        return self.process_create_form(GameMode, GameModeForm)

    def gamemode_edit(self):
        return self.process_edit_form(GameMode, GameModeForm)

    def player_create(self):
        return self.process_create_form(Player, PlayerForm)

    def player_edit(self):
        return self.process_edit_form(Player, PlayerForm)

    def get(self, request, *args, **kwargs):
        self.context = self.get_context_data(**kwargs)
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        self.context = self.get_context_data(**kwargs)
        try:
            action = self.post_actions[request.POST['post_action']]
            return action()
        except ValidationError as err:
            return render(request, self.template_name, self.context)


class GamesView(generic.TemplateView):
    template_name = "leagues/games.html"

    def get_form(self, request, form_class, prefix):
        data = request.POST if prefix in request.POST else None
        return form_class(data, prefix=prefix)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        games = Game.objects.all()
        context['game_list'] = games
        edit_forms = []
        for game in games:
            edit_forms.append(GameForm(instance=game, prefix='game_edit_' + str(game.id)))
        context['edit_forms'] = edit_forms
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if 'game_create' in request.POST:
            create_form = GameForm(request.POST, prefix='game_create')
            if create_form.is_bound and create_form.is_valid():
                game_name = create_form.cleaned_data['name']
                if not Game.objects.filter(name=game_name).exists():
                    # commit=False doesn't save new model object directly into the DB
                    # so we can do additional processing before storing it in the DB with save method of model object
                    game_object = create_form.save(commit=False)

                    # ... do additional processing

                    game_object.save()  # save object do DB
                    create_form.save_m2m()  # need to save relations manually with commit=False
                    return HttpResponseRedirect(reverse('leagues:games'))

        elif 'game_id' in request.POST:
            try:
                game = Game.objects.get(pk=request.POST['game_id'])
                edit_form = GameForm(request.POST, instance=game, prefix='game_edit_' + str(game.id))
                if edit_form.is_bound and edit_form.is_valid():
                    edit_form.save()
                    return HttpResponseRedirect(reverse('leagues:games'))
                form_list = context['edit_forms']
                form_list[:] = [edit_form if x.instance == game else x for x in form_list]

            except Game.DoesNotExist as err:
                return None

        return render(request, self.template_name, context)


class DetailGameView(generic.DetailView):
    model = Game
    template_name = "leagues/game_detail.html"


class DetailGenreView(generic.DetailView):
    model = Genre
    template_name = "leagues/genre_detail.html"
