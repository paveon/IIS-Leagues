from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic, View
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.forms.models import model_to_dict
from django_countries.fields import Country
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
        self.used_models = {
            Game.__name__.lower(): (Game, GameForm),
            Genre.__name__.lower(): (Genre, GenreForm),
            GameMode.__name__.lower(): (GameMode, GameModeForm),
            Player.__name__.lower(): (Player, PlayerForm),
            Team.__name__.lower(): (Team, TeamForm),
            Clan.__name__.lower(): (Clan, ClanForm),
            Tournament.__name__.lower(): (Tournament, TournamentForm),
            Sponsor.__name__.lower(): (Sponsor, SponsorForm),
            Sponsorship.__name__.lower(): (Sponsorship, SponsorshipForm)
        }

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        for key, form in self.used_models.items():
            model_class = form[0]
            model_name = model_class.__name__.lower()
            form_class = form[1]
            self.context[model_name + '_form'] = form_class(prefix=model_name + '_form')
            self.context[model_name + '_list'] = model_class.objects.all()
        return self.context

    def process_edit_form(self, model_class, form_class):
        model_name = model_class.__name__.lower()
        prefix = model_name + '_form'
        model_object = model_class.objects.get(pk=self.request.POST['object_id'])
        edit_form = form_class(self.request.POST, instance=model_object, prefix=prefix)
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()
            return HttpResponseRedirect(reverse('leagues:settings'))
        form_list = self.context[prefix + 'forms']
        form_list[:] = [edit_form if x.instance == model_object else x for x in form_list]
        raise ValidationError(form_class.__name__ + ' validation failed')

    def process_create_form(self, model_class, form_class):
        model_name = model_class.__name__
        create_form = form_class(self.request.POST, prefix=model_name.lower() + '_form')
        if create_form.is_bound and create_form.is_valid():
            # commit=False doesn't save new model object directly into the DB
            # so we can do additional processing before storing it in the DB with save method of model object
            model_object = create_form.save(commit=False)

            # ... do additional processing

            model_object.save()  # save object do DB
            create_form.save_m2m()  # need to save relations manually with commit=False
            return HttpResponseRedirect(reverse('leagues:settings'))

        self.context[model_name.lower() + '_form'] = create_form
        raise ValidationError(create_form.__class__.__name__ + ' validation failed')

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            action = self.request.GET['action']
            if action == 'edit':
                object_id = self.request.GET['object_id']
                class_name = self.request.GET['type'].split('_')[0]
                pair = self.used_models[class_name]
                model_class = pair[0]
                form_class = pair[1]
                model_object = model_class.objects.get(pk=object_id)
                model_object_dict = model_to_dict(model_object)

                # Convert lists of references (many to many fields) to list of their IDs
                for key, value in model_object_dict.items():
                    if type(value) is list:
                        id_list = [item.id for item in value]
                        model_object_dict[key] = id_list
                    elif type(value) is Country:
                        model_object_dict[key] = value.code
                response = JsonResponse(model_object_dict)
                return response
            else:
                pass
        else:
            self.context = self.get_context_data(**kwargs)
            content = render(request, self.template_name, self.context)
            return content

    def post(self, request, *args, **kwargs):
        self.context = self.get_context_data(**kwargs)
        try:
            action_name = request.POST['post_action']
            if action_name.endswith('_create'):
                action = self.process_create_form
            else:
                action = self.process_edit_form

            action_name = action_name.split('_')[0]
            parameters = self.used_models[action_name]
            return action(*parameters)
        except ValidationError as err:
            return render(request, self.template_name, self.context)


class GamesView(generic.TemplateView):
    template_name = "leagues/games.html"

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
        return render(request, self.template_name, context)


class DetailGameView(generic.DetailView):
    model = Game
    template_name = "leagues/game_detail.html"


class DetailGenreView(generic.DetailView):
    model = Genre
    template_name = "leagues/genre_detail.html"


class SocialView(generic.TemplateView):
    template_name = "leagues/social.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        players = Player.objects.all()
        teams = Team.objects.all()
        clans = Clan.objects.all()
        context['player_list'] = players
        context['team_list'] = teams
        context['clan_list'] = clans
        return context


class PlayerDetailView(generic.DetailView):
    template_name = "leagues/player_detail.html"
    model = Player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        edit_form = PlayerEditForm(instance=context['player'], prefix='player_edit_form')
        context['edit_form'] = edit_form
        return context
    # TODO random generace noveho leadera pokud leavne leader klan nebo tym
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        if 'player_edit_form' in request.POST:
            edit_form = PlayerEditForm(request.POST, instance=context['player'], prefix='player_edit_form')
            if edit_form.is_bound and edit_form.is_valid():
                edit_form.save()
                new_slug = slugify(context['player'].nickname)
                return HttpResponseRedirect(reverse("leagues:player_detail", args=(new_slug,)))
        elif 'team_id' in request.POST:
            Player.teams.through.objects.all().filter(player__id=request.POST['player_id'], team__id=request.POST['team_id']).delete()
            return HttpResponseRedirect(reverse("leagues:player_detail", args=(kwargs['slug'],)))
        elif 'clan_id' in request.POST:
            Player.clans.through.objects.all().filter(player__id=request.POST['player_id'], team__id=request.POST['clan_id']).delete()
            return HttpResponseRedirect(reverse("leagues:player_detail", args=(kwargs['slug'],)))

        return render(request, self.template_name, context)


class TeamDetailView(generic.DetailView):
    template_name = "leagues/team_detail.html"
    model = Team


class ClanDetailView(generic.DetailView):
    template_name = "leagues/clan_detail.html"
    model = Clan
