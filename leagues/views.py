from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic, View
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.forms.models import model_to_dict
from django_countries.fields import Country
from django.db.models import F, Q
from enum import Enum
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
            player = Player.objects.create(nickname=username)
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
            form_instance = form_class(prefix=model_name + '_form')
            self.context[model_name + '_form'] = form_instance
            self.context[model_name + '_list'] = model_class.objects.all()
        return self.context

    def process_edit_form(self, model_class, form_class):
        model_name = model_class.__name__.lower()
        prefix = model_name + '_form'
        model_object = model_class.objects.get(pk=self.request.POST['object_id'])
        edit_form = form_class(self.request.POST, instance=model_object, prefix=prefix)
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()

            # Additional processing
            form_name = form_class.__name__
            if form_name == 'TeamForm':
                # Leader must be a member of team
                leader = edit_form.cleaned_data['leader']
                if leader:
                    team = model_object
                    try:
                        team.team_members.get(pk=leader.id)
                    except Player.DoesNotExist:
                        team.team_members.add(leader)

            elif form_name == 'ClanForm':
                # Leader must be a member of clan
                leader = edit_form.cleaned_data['leader']
                if leader:
                    clan = model_object
                    try:
                        clan.clan_members.get(pk=leader.id)
                    except Player.DoesNotExist:
                        clan.clan_members.add(leader)

            return HttpResponseRedirect(reverse('leagues:settings'))

        self.context[prefix] = edit_form
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

                # Provide specific querysets for select dropdowns based on
                # integrity constraints
                # if form_class.__name__ == 'TeamForm':
                #     queryset = Team.objects.get(pk=object_id).team_members.all()
                #     queryset = queryset.annotate(value=F('nickname')).values('id', 'value')
                #     model_object_dict['leader_queryset'] = list(queryset)
                # elif form_class.__name__ == 'ClanForm':
                #     queryset = Clan.objects.get(pk=object_id).clan_members.all()
                #     queryset = queryset.annotate(value=F('nickname')).values('id', 'value')
                #     model_object_dict['leader_queryset'] = list(queryset)

                response = JsonResponse(model_object_dict)
                return response
            elif action == 'create':
                # If edit form messed up some select dropdowns, send original data back when
                # opening create form
                class_name = self.request.GET['type'].split('_')[0]
                pair = self.used_models[class_name]
                class_name = pair[1].__name__
                # if class_name == 'TeamForm' or class_name == 'ClanForm':
                #     queryset = Player.objects.all().annotate(value=F('nickname')).values('id', 'value')
                #     data = {'leader': list(queryset)}
                #     return JsonResponse(data)
                return JsonResponse({})

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


def template_enum(cls):
    cls.do_not_call_in_templates = True
    return cls


@template_enum
class MembershipStatus(Enum):
    PENDING = 2
    MEMBER = 1
    NOT_MEMBER = 0


class SocialView(generic.TemplateView):
    template_name = "leagues/social.html"

    def cancel_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)

        if request_type == 'cancel_team':
            team = Team.objects.get(pk=object_id)
            player.team_pendings.remove(team)
        elif request_type == 'cancel_clan':
            clan = Clan.objects.get(pk=object_id)
            player.clan_pendings.remove(clan)

    # Processes join request for teams and clans
    def join_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)
        group_pendings = None
        group_members = None
        group = None

        # Check which type of request it is and initialize common variables
        if request_type == 'join_team':
            group = Team.objects.get(pk=object_id)
            group_members = group.team_members
            group_pendings = player.team_pendings
        elif request_type == 'join_clan':
            group = Clan.objects.get(pk=object_id)
            group_members = group.clan_members
            group_pendings = player.clan_pendings

        if group:
            if group.leader:
                # Need confirmation if group has a leader
                group_pendings.add(group)
            else:
                # Join immediately
                group.leader = player
                group_members.add(player)
                group.save()

    def leave_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)
        group = None
        group_members = None

        if request_type == 'leave_team':
            group = Team.objects.get(pk=object_id)
            group_members = group.team_members
        elif request_type == 'leave_clan':
            group = Clan.objects.get(pk=object_id)
            group_members = group.clan_members

        if group:
            group_members.remove(player)
            # Check if leaving player is a group leader and revoke the privilege if so
            if group.leader and group.leader.id == player.id:
                # Pick first player to become a new leader (None if there are no players left)
                group.leader = group_members.first()
                group.save()

    def __init__(self):
        super().__init__()
        self.actions = {
            'cancel_team': self.cancel_request,
            'cancel_clan': self.cancel_request,
            'join_team': self.join_request,
            'join_clan': self.join_request,
            'leave_team': self.leave_request,
            'leave_clan': self.leave_request,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.request.user.player

        # Split all teams into 3 types and create tuple with membership info for each of them
        joined_teams = player.teams.all()
        pending_teams = player.team_pendings.all()
        remaining_teams = Team.objects.all().difference(joined_teams).difference(pending_teams)
        remaining_teams = list(map(lambda x: (x, MembershipStatus.NOT_MEMBER), remaining_teams))
        joined_teams = list(map(lambda x: (x, MembershipStatus.MEMBER), joined_teams))
        pending_teams = list(map(lambda x: (x, MembershipStatus.PENDING), pending_teams))

        # Split all clans into 3 types and create tuple with membership info for each of them
        joined_clans = player.clans.all()
        pending_clans = player.clan_pendings.all()
        remaining_clans = Clan.objects.all().difference(joined_clans).difference(pending_clans)
        remaining_clans = list(map(lambda x: (x, MembershipStatus.NOT_MEMBER), remaining_clans))
        joined_clans = list(map(lambda x: (x, MembershipStatus.MEMBER), joined_clans))
        pending_clans = list(map(lambda x: (x, MembershipStatus.PENDING), pending_clans))

        # Join all 3 types of teams into a single list
        teams = joined_teams + pending_teams + remaining_teams
        clans = joined_clans + pending_clans + remaining_clans

        context['player_list'] = Player.objects.all()
        context['team_list'] = teams
        context['clan_list'] = clans
        context['membership'] = MembershipStatus.__members__
        return context

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        player_id = request.POST['player_id']
        player = Player.objects.get(pk=player_id)

        if request.is_ajax():
            # Get callable object from action dictionary and call action method
            action_key = request.POST['action']
            action = self.actions[action_key]
            action(action_key)
            return JsonResponse({})

        else:
            if 'leave_team_id' in request.POST:
                team_id = request.POST['leave_team_id']
                team = Team.objects.get(pk=team_id)
                team.team_members.remove(player)

                # Check if leaving player is a team leader and revoke the privilege if so
                if team.leader and team.leader.id == player.id:
                    # Pick first player to become a new leader (None if there are no players left)
                    team.leader = team.team_members.first()
                    team.save()

            elif 'leave_clan_id' in request.POST:
                clan_id = request.POST['leave_clan_id']
                clan = Clan.objects.get(pk=clan_id)
                clan.clan_members.remove(player)

                # Check if leaving player is a clan leader and revoke the privilege if so
                if clan.leader and clan.leader.id == player.id:
                    # Pick first player to become a new leader (None if there are no players left)
                    clan.leader = clan.clan_members.first()
                    clan.save()

            else:
                return render(request, self.template_name, context)

        return HttpResponseRedirect(reverse("leagues:social"))


class PlayerDetailView(generic.DetailView):
    template_name = "leagues/player_detail.html"
    model = Player

    def edit_player(self):
        player = self.object
        user = player.user
        edit_form = PlayerForm(self.request.POST, instance=player, prefix='player_form')
        if edit_form.is_bound and edit_form.is_valid():
            player = edit_form.save(commit=False)
            player.user = user
            player.save()

    def __init__(self):
        super().__init__()
        self.object = None
        self.actions = {
            'player_edit': self.edit_player,
        }

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        edit_form = PlayerForm(instance=self.object, prefix='player_form')
        context['player_form'] = edit_form
        context['authorized'] = (self.object.user == self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        action = self.actions[action_key]
        action()
        return HttpResponseRedirect(reverse("leagues:player_detail", args=[self.object.slug]))

        # if 'player_form' in request.POST:
        #     edit_form = PlayerForm(request.POST, instance=context['player'], prefix='player_form')
        #     if edit_form.is_bound and edit_form.is_valid():
        #         edit_form.save()
        #         new_slug = slugify(context['player'].nickname)
        #         return HttpResponseRedirect(reverse("leagues:player_detail", args=(new_slug,)))
        # elif 'team_id' in request.POST:
        #     Player.teams.through.objects.all().filter(player__id=request.POST['player_id'],
        #                                               team__id=request.POST['team_id']).delete()
        #     return HttpResponseRedirect(reverse("leagues:player_detail", args=(kwargs['slug'],)))
        # elif 'clan_id' in request.POST:
        #     Player.clans.through.objects.all().filter(player__id=request.POST['player_id'],
        #                                               team__id=request.POST['clan_id']).delete()
        #     return HttpResponseRedirect(reverse("leagues:player_detail", args=(kwargs['slug'],)))

        # return render(request, self.template_name, context)


class TeamDetailView(generic.DetailView):
    template_name = "leagues/team_detail.html"
    model = Team

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        members = team.team_members.all()
        member_matches = []
        for member in members:
            team_matches = PlayedMatch.objects.filter(Q(team=team) & Q(player=member))
            won_matches = team_matches.filter(match__winner=team)
            member_matches.append((member, team_matches, won_matches))
        context['member_matches'] = member_matches
        return context


class ClanDetailView(generic.DetailView):
    template_name = "leagues/clan_detail.html"
    model = Clan


class MatchDetailView(generic.DetailView):
    template_name = "leagues/match_detail.html"
    model = Match
