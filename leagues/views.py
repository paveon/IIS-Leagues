from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic, View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.forms.models import model_to_dict
from django import forms
from django_countries.fields import Country
from django.db.models import F, Q
from random import randint, choice, sample
from datetime import timedelta
import json
from enum import Enum
from leagues.forms import *
from leagues.model_actions import *


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('leagues:games'))


def registered_tournaments(player):
    registered = player.teams.all()
    tournaments = RegisteredTeams.objects.filter(team__in=registered)
    return tournaments


class SignupView(View):
    template_name = "leagues/signup.html"

    def post(self, request):
        form = MyUserForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=True)

            login(request, new_user[0])
            return HttpResponseRedirect(reverse('leagues:index'))
        else:
            return render(request, self.template_name, {'form': form})

    def get(self, request):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('leagues:index'))

        form = MyUserForm()
        return render(request, self.template_name, {'form': form})


class SettingsView(LoginRequiredMixin, generic.TemplateView):
    login_url = '/login/'
    template_name = "leagues/settings.html"

    def get_leader_queryset(self):
        self.object_id = self.request.GET['object_id']
        if self.object_id:
            clan = Clan.objects.get(pk=self.object_id)
            query = Q(clan=clan) | Q(clan__isnull=True)
            queryset = Player.objects.filter(query)
        else:
            queryset = Player.objects.all()

        queryset = queryset.annotate(value=F('nickname')).values('id', 'value')
        self.response['leaders'] = list(queryset)

    # Fills json response with object data. Data is then
    # used on the client side to populate editing form with
    # current object data. This allows us to dynamically change
    # options in HTML select menus based on queryset. We also use single
    # modal form creating and editing which we modify with jquery
    def get_edit_modal_data(self):
        self.object_id = self.request.GET['object_id']
        model_object = self.model_class.objects.get(pk=self.object_id)
        self.response = model_to_dict(model_object)

        # Convert lists of references (many to many fields) to list of their IDs
        for key, value in self.response.items():
            if type(value) is list:
                id_list = [item.id for item in value]
                self.response[key] = id_list
            elif type(value) is Country:
                self.response[key] = value.code

        # Provide specific querysets for select dropdowns based on
        # integrity constraints
        form_name = self.form_class.__name__
        if form_name == 'TeamForm':
            if model_object.clan:
                query = Q(clan=model_object.clan) | Q(clan__isnull=True)
                queryset = Player.objects.filter(query)
            else:
                queryset = Player.objects.all()
            queryset = queryset.annotate(value=F('nickname')).values('id', 'value')
            self.response['leader_queryset'] = list(queryset)

        elif form_name == 'ClanForm':
            query = Q(clan=model_object) | Q(clan__isnull=True)
            queryset = Player.objects.filter(query)
            queryset = queryset.annotate(value=F('nickname')).values('id', 'value')
            self.response['leader_queryset'] = list(queryset)

    # Fills json response with default querysets for each HTML
    # select element so that we can restore its original state after
    # opening editing form which might have used different select options
    def get_create_modal_data(self):
        form_instance = self.form_class()
        form_fields_dict = dict(form_instance.fields)
        # Convert choice fields to list of ids and names
        for key, value in form_fields_dict.items():
            if type(value) is forms.ModelChoiceField:
                choice_list = list(value.choices)
                self.response[key] = choice_list

    def __init__(self):
        super().__init__()
        self.action_key = None
        self.class_name = None
        self.model_class = None
        self.form_class = None
        self.object_id = None
        self.response = {}
        self.context = []
        self.get_actions = {
            'open_edit_modal': self.get_edit_modal_data,
            'open_create_modal': self.get_create_modal_data,
            'clan_changed': self.get_leader_queryset
        }
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

        # For each model used on management page provide
        # form instance and list of all objects
        for key, config in self.used_models.items():
            model_class = config[0]
            form_class = config[1]
            class_name = model_class.__name__.lower()
            form_instance = form_class(prefix=class_name + '_form')
            self.context[class_name + '_form'] = form_instance
            self.context[class_name + '_list'] = model_class.objects.all()

        self.context['status'] = TournamentStatus.__members__
        return self.context

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_staff and not user.is_superuser:
            return HttpResponseForbidden()
        if request.is_ajax():
            # Ajax calls are used to populate opened form with existing data
            # if editing object or with default data when creating new one
            self.class_name = request.GET['modal_type']
            self.action_key = request.GET['action']
            action = self.get_actions[self.action_key]
            config = self.used_models[self.class_name]
            self.model_class = config[0]
            self.form_class = config[1]
            action()
            return JsonResponse(self.response)
        else:
            self.context = self.get_context_data(**kwargs)
            content = render(request, self.template_name, self.context)
            return content

    # Handles editing of existing object when user submits
    # modified data through form
    def process_edit_form(self):
        prefix = self.class_name.lower() + '_form'

        # Get existing object from db
        model_object = self.model_class.objects.get(pk=self.object_id)

        # Fill form with object instance and post data
        edit_form = self.form_class(self.request.POST, instance=model_object, prefix=prefix)
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()

            # elif form_name == 'ClanForm':
            #     # Leader must be a member of clan
            #     leader = edit_form.cleaned_data['leader']
            #     if leader:
            #         clan = model_object
            #         try:
            #             clan.clan_members.get(pk=leader.id)
            #         except Player.DoesNotExist:
            #             clan.clan_members.add(leader)

            return HttpResponseRedirect(reverse('leagues:settings'))

        failed = self.form_class(instance=model_object, prefix=prefix)
        failed._errors = edit_form._errors
        self.context[prefix] = failed
        raise ValidationError(self.form_class.__name__ + ' validation failed')

    def process_create_form(self):
        form_prefix = self.class_name.lower() + '_form'
        create_form = self.form_class(self.request.POST, prefix=form_prefix)
        # TODO nejde pridat klan k tymu pokud uz odehral hru
        # TODO omezit vybery leader tymu muze byt jen nekdo kdo je v tom tymu (stejne klan), hry pro tymy omezeny podle her klanu (nebo se ke specializacim klanu potom prida ta hra tymu?)
        # TODO add new nevytvori novy formular pokud v predchozim byla chyba takze bud clear tlacitko a nebo to nejak vyresit at se udela prazdny formular po kliknuti na new pri predchozim erroru
        # TODO pri vytvareni tournamentu to hodi error a potom po refreshi je to tam, ale hodi to prvni chybu
        # TODO pri vytvareni hry je hra neaktivni a aktivuje se az ma prirazeny gamemode => momentalni kvuli testovani je default true ale ma byt false (doplnit pri vytvareni hry)
        # TODO pri vytvareni hrace se stejnym nickname se chyba zobrazi ale formular zavre takze to vypada jako kdyby se vytvoril
        if create_form.is_bound and create_form.is_valid():
            create_form.save(commit=True)
            return HttpResponseRedirect(reverse('leagues:settings'))

        self.context[form_prefix] = create_form
        raise ValidationError(self.form_class.__name__ + ' validation failed')

    # All posts on management page are synchronous
    def post(self, request, *args, **kwargs):
        self.context = self.get_context_data(**kwargs)
        self.object_id = request.POST['object_id']
        self.action_key = request.POST['post_action']
        self.class_name = self.action_key.split('_')[0]
        config = self.used_models[self.class_name]
        self.model_class = config[0]
        self.form_class = config[1]
        try:
            if self.action_key.endswith('_create'):
                action = self.process_create_form
            else:
                action = self.process_edit_form
            return action()

        except ValidationError:
            self.context['error_modal'] = self.class_name + '_form'
            if self.object_id:
                self.context['object_id'] = self.object_id
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
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)


def template_enum(cls):
    cls.do_not_call_in_templates = True
    return cls


@template_enum
class MembershipStatus(Enum):
    PENDING = 2
    MEMBER = 1
    NOT_MEMBER = 0


@method_decorator(never_cache, name='dispatch')
class SocialView(generic.TemplateView):
    template_name = "leagues/social.html"

    def cancel_team(self):
        team = Team.objects.get(pk=self.object_id)
        self.player.team_pendings.remove(team)

    # TODO: zkontrolovat jestli funguje
    # TODO: kdyz leavne hrac tym a ten tym je registrovany na turnaj a uz nebude dost hracu na turnaj tak co udelat?
    def cancel_clan(self):
        clan = Clan.objects.get(pk=self.object_id)
        self.player.clan_pendings.remove(clan)

        # Also remove pendings into clan teams
        pendings = self.player.team_pendings.filter(clan=clan)
        self.player.team_pendings.remove(*pendings)

    def join_team(self):
        team = Team.objects.get(pk=self.object_id)
        join_team(team, self.player, self.response)

    def join_clan(self):
        clan = Clan.objects.get(pk=self.object_id)
        if clan.leader:
            self.player.clan_pendings.add(clan)
        else:
            # Clan has no members, join immediately and become new leader
            # First remove all other clan pendings
            pendings = self.player.clan_pendings.all()
            self.player.clan_pendings.remove(*pendings)

            # Also remove pendings of teams from other clans, ignore teams without clan
            pendings = self.player.team_pendings.filter(Q(clan__isnull=False) & ~Q(clan=clan))
            self.player.team_pendings.remove(*pendings)

            self.player.clan = clan
            self.player.save()
            clan.leader = self.player
            clan.save()

    def force_join_team(self):
        team = Team.objects.get(pk=self.object_id)
        force_join_team(team, self.player)

    def leave_team(self):
        team = Team.objects.get(pk=self.object_id)
        leave_team(team, self.player)

    def leave_clan(self):
        clan = Clan.objects.get(pk=self.object_id)
        leave_clan(clan, self.player, self.response)

    def force_leave_clan(self):
        clan = Clan.objects.get(pk=self.object_id)
        force_leave_clan(clan, self.player)

    def create_team(self):
        team_form = TeamForm(self.request.POST, prefix='team_form')
        if team_form.is_bound and team_form.is_valid():
            instance = team_form.save(commit=False)
            instance.leader = self.player
            instance.save()
            self.player.teams.add(instance)
            return

        self.context['team_form'] = team_form

    def create_clan(self):
        clan_form = ClanForm(self.request.POST, prefix='clan_form')
        if clan_form.is_bound and clan_form.is_valid():
            instance = clan_form.save(commit=False)
            instance.save()
            join_clan(instance, self.player)
            return

        self.context['clan_form'] = clan_form

    def __init__(self):
        super().__init__()
        self.player_id = None
        self.object_id = None
        self.player = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'cancel_team': self.cancel_team,
            'cancel_clan': self.cancel_clan,
            'join_team': self.join_team,
            'join_clan': self.join_clan,
            'leave_team': self.leave_team,
            'leave_clan': self.leave_clan,
            'force_join_team': self.force_join_team,
            'force_leave_clan': self.force_leave_clan,
            'create_clan': self.create_clan,
            'create_team': self.create_team,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = Player.objects.get(pk=self.request.user.player.id)

        # Split all teams into 3 types and create tuple with membership info for each of them
        joined_teams = player.teams.all()
        pending_teams = player.team_pendings.all()
        remaining_teams = Team.objects.all().difference(joined_teams).difference(pending_teams)
        remaining_teams = list(map(lambda x: (x, MembershipStatus.NOT_MEMBER), remaining_teams))
        joined_teams = list(map(lambda x: (x, MembershipStatus.MEMBER), joined_teams))
        pending_teams = list(map(lambda x: (x, MembershipStatus.PENDING), pending_teams))

        # Join all 3 types of teams into a single list
        teams = joined_teams + pending_teams + remaining_teams

        context['player_list'] = Player.objects.all()
        context['player'] = player
        context['clan_pendings'] = player.clan_pendings.all()
        context['team_list'] = teams
        context['clan_list'] = Clan.objects.all()
        context['membership'] = MembershipStatus.__members__
        context['clan_form'] = ClanForm(prefix='clan_form')
        context['team_form'] = TeamForm(prefix='team_form')
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.action_key = request.POST['action']
        self.player_id = request.POST['player_id']
        self.object_id = request.POST['object_id']
        self.player = Player.objects.get(pk=self.player_id)
        action = self.actions[self.action_key]
        if request.is_ajax():
            action()
            return JsonResponse(self.response)

        self.context = self.get_context_data(**kwargs)
        action()
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)


@method_decorator(never_cache, name='dispatch')
class PlayerDetailView(generic.DetailView):
    template_name = "leagues/player_detail.html"
    model = Player

    def edit_player(self):
        edit_form = PlayerForm(self.request.POST, instance=self.player, prefix='player_form')
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()

    def leave_clan(self):
        leave_clan(self.player.clan, self.player, self.response)

    def force_leave_clan(self):
        force_leave_clan(self.player.clan, self.player)

    def leave_team(self):
        team_id = self.request.POST['object_id']
        team = Team.objects.get(pk=team_id)
        leave_team(team, self.player)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.get_object()
        edit_form = PlayerForm(instance=self.object, prefix='player_form')
        games = Game.objects.filter(id__in=PlayedMatch.objects.filter(player=player).values_list("match__game_id"))
        player_stats = []
        for game in games:
            death_obj = Death.objects.filter(match__game=game)
            try:
                kill_death = death_obj.filter(killer=player).count() / death_obj.filter(victim=player).count()
            except:
                kill_death = None
            won_games = PlayedMatch.objects.filter(match__game=game, player=player,
                                                   match__winner__in=player.teams.all()).count()
            try:
                win_ratio = round(
                    (won_games / PlayedMatch.objects.filter(match__game=game, player=player).count()) * 100, 2)
            except:
                win_ratio = None
            player_stats.append((game, kill_death, str(win_ratio) + "%"))
        context['player_stats'] = player_stats
        context['player_form'] = edit_form
        return context

    def __init__(self):
        super().__init__()
        self.object = None
        self.player = None
        self.object_id = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'player_edit': self.edit_player,
            'leave_clan': self.leave_clan,
            'leave_team': self.leave_team,
            'force_leave_clan': self.force_leave_clan
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.player = self.object
        self.action_key = request.POST['action']
        action = self.actions[self.action_key]
        action()
        if request.is_ajax():
            return JsonResponse(self.response)
        else:
            return HttpResponseRedirect(reverse("leagues:player_detail", args=[self.player.slug]))


@method_decorator(never_cache, name='dispatch')
class TeamDetailView(generic.DetailView):
    template_name = "leagues/team_detail.html"
    model = Team

    def force_join_team(self):
        player = Player.objects.get(pk=self.object_id)
        force_join_team(self.team, player)

    def join_team(self):
        player = Player.objects.get(pk=self.object_id)
        join_team(self.team, player, self.response)

    def leave_team(self):
        player = Player.objects.get(pk=self.object_id)
        leave_team(self.team, player)

    def leave_tournament(self):
        RegisteredTeams.objects.filter(team=self.team, tournament_id=self.object_id).delete()

    def join_tournament(self):
        tournament = Tournament.objects.get(pk=self.object_id)
        if tournament.team_set.filter(clan=self.team.clan).exists():
            self.response['error'] = 'Another team from your clan is ' \
                                     'already registered for this tournament'

        elif self.team.team_members.all().count() < tournament.game_mode.team_player_count:
            self.response['error'] = 'Not enough players in team to join tournament'
        else:
            self.team.tournaments.add(tournament)

    def kick_player(self):
        player = Player.objects.get(pk=self.object_id)
        self.team.team_members.remove(player)

    def process_request(self):
        player = Player.objects.get(pk=self.object_id)
        self.team.team_pendings.remove(player)
        if self.action_key == 'accept_request':
            self.team.team_members.add(player)
            if self.team.clan_pending and player.clan != self.team.clan_pending:
                self.team.clan_pending = None
                self.team.save()

    def remove_clan(self):
        self.team.clan = None
        self.team.save()

    def add_clan(self, request):
        clan_form = TeamFormUser(request.POST, prefix='clan_join')
        if clan_form.is_bound and clan_form.is_valid():
            clan = clan_form.cleaned_data['clan']
            self.team.clan_pending = clan
            self.team.save()
            return HttpResponseRedirect(reverse("leagues:team_detail", args=[self.team.slug]))
        self.context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, self.context)

    def cancel_clan_request(self):
        self.team.clan_pending = None
        self.team.save()

    def edit_team(self, request):
        edit_form = TeamForm(request.POST, instance=self.team, prefix='edit_form')
        if edit_form.is_bound and edit_form.is_valid():
            edit_form.save()
            return HttpResponseRedirect(reverse("leagues:team_detail", args=[self.team.slug]))
        self.context['edit_form'] = edit_form
        self.context['team'] = self.get_object()
        self.context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, self.context)

    def __init__(self):
        super().__init__()
        self.object = None
        self.context = None
        self.team = None
        self.object_id = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'edit_team': self.edit_team,
            'join_team': self.join_team,
            'force_join_team': self.force_join_team,
            'leave_team': self.leave_team,
            'leave_tournament': self.leave_tournament,
            'join_tournament': self.join_tournament,
            'kick_player': self.kick_player,
            'decline_request': self.process_request,
            'accept_request': self.process_request,
            'remove_clan': self.remove_clan,
            'add_clan': self.add_clan,
            'cancel_clan_request': self.cancel_clan_request,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.team = self.get_object()
        members = self.team.team_members.all()
        member_matches = []
        for member in members:
            team_matches = PlayedMatch.objects.filter(team=self.team, player=member)
            won_matches = team_matches.filter(match__winner=self.team)
            member_matches.append((member, team_matches, won_matches))

        registered = Tournament.objects.filter(team=self.team)
        non_registered = Tournament.objects.filter(Q(game=self.team.game) & ~Q(team=self.team))

        if not self.team.clan_pending:
            clan_id_list = []
            for clan in Clan.objects.all():
                # Check if all team members are members of this clan
                if not members.exclude(clan=clan).exists():
                    clan_id_list.append(clan.id)
            queryset = Clan.objects.filter(pk__in=clan_id_list)
            clan_join_form = TeamFormUser(instance=self.team, prefix='clan_join')
            clan_join_form.fields['clan'].queryset = queryset
            context['clan_form'] = clan_join_form

        edit_form = TeamForm(instance=self.team, prefix='edit_form')
        leader_field = edit_form.fields['leader']
        leader_field.queryset = members
        leader_field.empty_label = None

        context['registered'] = registered
        context['non_registered'] = non_registered
        context['member_matches'] = member_matches
        context['edit_form'] = edit_form
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.context = self.get_context_data(**kwargs)
        self.team = self.object
        self.action_key = request.POST['action']
        action = self.actions[self.action_key]
        if request.is_ajax():
            self.object_id = int(request.POST['object_id'])
            action()
            return JsonResponse(self.response)
        else:
            return action(request)


@method_decorator(never_cache, name='dispatch')
class ClanDetailView(generic.DetailView):
    template_name = "leagues/clan_detail.html"
    model = Clan

    @staticmethod
    def win_ratio(won, total):
        if total > 0:
            ratio = round((won / total) * 100, 2)
            return str(ratio) + ' %'
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.clan = self.get_object()

        # Get played and won matches under this clan by each member
        member_stats = []
        for member in self.clan.clan_members.all():
            matches = PlayedMatch.objects.filter(player=member, clan=self.clan)
            matches_won = matches.filter(team=F('match__winner'))
            matches_total = matches.count()
            matches_won = matches_won.count()
            win_ratio = self.win_ratio(matches_won, matches_total)
            member_stats.append((member, matches_total, matches_won, win_ratio))

        # Get played and won matches in each game

        clan_matches = self.clan.all_matches
        win_ratio = self.clan.win_ratio
        matches_won = self.clan.matches_won
        stats = (clan_matches.count(), matches_won.count(), win_ratio)

        game_stats = []
        for game in Game.objects.all():
            matches = game.match_set.filter(Q(clan_1=self.clan) | Q(clan_2=self.clan))
            matches_total = matches.count()
            if matches_total > 0:
                won_count = matches.filter(clan_winner=self.clan).count()
                win_ratio = self.win_ratio(won_count, matches_total)
                game_stats.append((game, won_count, matches_total, win_ratio))

        context['stats'] = stats
        context['member_stats'] = member_stats
        context['game_stats'] = game_stats
        context['membership_requests'] = self.clan.clan_pendings.all()
        return context

    def force_leave_clan(self):
        player = Player.objects.get(pk=self.object_id)
        force_leave_clan(self.clan, player)

    def leave_clan(self):
        player = Player.objects.get(pk=self.object_id)
        leave_clan(self.clan, player, self.response)

    def join_clan(self):
        player = Player.objects.get(pk=self.object_id)
        join_clan(self.clan, player)

    def kick_player(self):
        player = Player.objects.get(pk=self.object_id)
        # Kick player out of every clan team
        player.teams.remove(*player.teams.filter(clan=self.clan))

        # Also remove all pendings to clan teams
        active_pendings = player.team_pendings.filter(clan=self.clan)
        player.team_pendings.remove(*active_pendings)
        self.clan.clan_members.remove(player)

    def process_player_request(self):
        player = Player.objects.get(pk=self.object_id)
        self.clan.clan_pendings.remove(player)
        if self.action_key == 'accept_player_request':
            self.clan.clan_members.add(player)

    def process_team_request(self):
        team = Team.objects.get(pk=self.object_id)
        team.clan_pending = None
        if self.action_key == 'accept_team_request':
            team.clan = self.clan
        team.save()

    def remove_team(self):
        team = Team.objects.get(pk=self.object_id)
        team.clan = None
        team.save()

    def __init__(self):
        super().__init__()
        self.clan = None
        self.object_id = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'join_clan': self.join_clan,
            'leave_clan': self.leave_clan,
            'force_leave_clan': self.force_leave_clan,
            'kick_player': self.kick_player,
            'accept_player_request': self.process_player_request,
            'decline_player_request': self.process_player_request,
            'accept_team_request': self.process_team_request,
            'decline_team_request': self.process_team_request,
            'remove_team': self.remove_team
        }

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.clan = self.get_object()
        self.action_key = request.POST['action']
        self.object_id = request.POST['object_id']
        action = self.actions[self.action_key]
        action()
        return JsonResponse(self.response)


class TournamentView(generic.TemplateView):
    template_name = "leagues/tournaments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournaments = Tournament.objects.all()
        matches = Match.objects.all()
        context['tournaments'] = tournaments
        context['matches'] = matches
        context['match_form'] = MatchForm()
        return context

    def generateStats(self, match, players_1, players_2):
        event_interval = match.duration_seconds // (30 + 1)
        event_time = 0
        while 1:
            event_time += randint(15, event_interval)
            if event_time >= match.duration_seconds:
                break
            num_of_assists = randint(0, match.game_mode.team_player_count - 2)
            who = randint(1, 2)
            if who == 1:
                victim = sample(players_1, 1)
                killer = sample(players_2, 1)
                possible_assists = players_2.copy()
                possible_assists.remove(killer[0])
            else:
                victim = sample(players_2, 1)
                killer = sample(players_1, 1)
                possible_assists = players_1.copy()
                possible_assists.remove(killer[0])

            death = Death(match=match, victim_id=victim[0], killer_id=killer[0],
                          match_time=timedelta(seconds=event_time))
            death.save()
            for i in range(num_of_assists):
                assist_type = choice(['HEALING', 'DAMAGE'])
                assist_player = sample(possible_assists, 1)
                possible_assists.remove(assist_player[0])
                assist = Assist(death=death, player_id=assist_player[0], type=assist_type)
                assist.save()

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tournaments = Tournament.objects.all()
        form_data = set()

        for tournament in tournaments:
            teams = RegisteredTeams.objects.filter(tournament=tournament)
            if teams.count() >= 2 and teams.filter(team__leader=request.user.player):
                form_data.add(tournament)

        context['match_form_data'] = form_data
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        response_data = {}
        dictionaries = []

        form_data_dict = {}
        form_data_list = json.loads(request.POST['data'])
        for field in form_data_list:
            form_data_dict[field["name"]] = field["value"]

        if action_key == 'picked_tournament':
            try:
                tournament_id = int(form_data_dict['match_create-tournament'])
                tournament = Tournament.objects.get(pk=tournament_id)
                registered_teams = RegisteredTeams.objects.all().filter(tournament=tournament)
                for team in registered_teams:
                    if not team.team.is_playing:
                        dictionaries.append(team.team.as_array())
                response_data['teams'] = json.dumps({"data": dictionaries})
                response_data['tournament'] = tournament.id
                response_data['status'] = "pick_teams"
            except:
                games = Game.objects.filter()
                dictionaries = [game.as_array() for game in games]
                response_data['games'] = json.dumps({"data": dictionaries})
                response_data['status'] = "pick_game"
            return JsonResponse(response_data)
        elif action_key == 'picked_game':
            game_id = int(form_data_dict['match_create-game'])
            game = Game.objects.get(pk=game_id)
            modes = game.game_modes.all()
            dictionaries = [mode.as_array() for mode in modes]
            response_data['game_modes'] = json.dumps({"data": dictionaries})
            response_data['game'] = game_id
            response_data['status'] = "pick_game_mode"
            return JsonResponse(response_data)
        elif action_key == 'picked_game_mode':
            game = int(form_data_dict['game_mode-game'])
            game_mode = int(form_data_dict['match_create-game_mode'])
            player_id = int(form_data_dict['player_id'])
            possible_teams = Team.objects.filter(game_id=game, active=True)
            for t in possible_teams:
                if (t.team_members.all().count() >= GameMode.objects.get(pk=game_mode).team_player_count)\
                        and t.team_members.filter(id=player_id).exists() and not t.is_playing:
                    valid_team = [t.id, t.name]
                    dictionaries.append(valid_team)
            response_data['teams_1'] = json.dumps({"data": dictionaries})
            response_data['game'] = game
            response_data['game_mode'] = game_mode
            response_data['status'] = "pick_team1"
            return JsonResponse(response_data)
        elif action_key == 'picked_team1':
            game = int(form_data_dict['team_1-game'])
            game_mode = int(form_data_dict['team_1-game_mode'])
            team_1 = int(form_data_dict['team_1'])
            team = Team.objects.get(pk=team_1)
            possible_teams = Team.objects.filter(Q(game_id=game) & Q(active=True) & ~Q(clan=team.clan))
            for t in possible_teams:
                players1 = set(t.team_members.all())
                players2 = set(team.team_members.all())
                players = len(players1.intersection(players2))
                players1 = len(players1) - players
                count = GameMode.objects.get(pk=game_mode).team_player_count
                # if distinct number of player of both teams can make together
                if (players1 + len(players2)) >= (2 * count) and (players1 + players) >= count\
                        and not t.is_playing:
                    valid_team = [t.id, t.name]
                    dictionaries.append(valid_team)
            response_data['teams_2'] = json.dumps({"data": dictionaries})
            response_data['game'] = game
            response_data['game_mode'] = game_mode
            response_data['team_1'] = team_1
            response_data['status'] = "pick_team2"
            return JsonResponse(response_data)
        elif action_key == 'non_turnament_done':
            game = int(form_data_dict['team_2-game'])
            game_mode = int(form_data_dict['team_2-game_mode'])
            team_1_id = int(form_data_dict['team_2-team1'])
            team_2_id = int(form_data_dict['team_2'])
            player_id = int(form_data_dict['player_id'])
            minutes = randint(20, 59)
            seconds = randint(0, 59)
            mode = GameMode.objects.get(pk=game_mode)
            winner = choice((team_1_id, team_2_id))
            match = Match(game_id=game, game_mode_id=game_mode, team_1_id=team_1_id, team_2_id=team_2_id,
                          duration=timedelta(minutes=minutes, seconds=seconds), winner_id=winner)
            match.save()

            # random players for first team
            team_1 = Team.objects.get(pk=team_1_id)
            players_1 = set(team_1.team_members.all().values_list('id', flat=True))
            player = {Player.objects.get(pk=player_id).id}
            players_1 -= player
            count = mode.team_player_count
            played = PlayedMatch(player_id=player_id, team=team_1, clan=team_1.clan, match=match)
            played.save()
            p1 = sample(players_1, count - 1)
            for i in range(0, count - 1):
                played = PlayedMatch(player_id=p1[i], team=team_1, clan=team_1.clan, match=match)
                played.save()

            p1 = set(p1)
            p1.add(player_id)

            # random players for second team
            team_2 = Team.objects.get(pk=team_2_id)
            players_2 = set(team_2.team_members.all().values_list('id', flat=True))
            players_2 -= p1
            p2 = sample(players_2, count)
            for i in range(0, count):
                played = PlayedMatch(player_id=p2[i], team=team_2, clan=team_2.clan, match=match)
                played.save()

            self.generateStats(match, p1, p2)

            return JsonResponse(response_data)
        elif action_key == 'match_done':
            team_1_id = int(form_data_dict['match_create-team_1'])
            team_2_id = int(form_data_dict['match_create-team_2'])
            tournament = int(form_data_dict['tournament'])
            t = Tournament.objects.get(pk=tournament)
            minutes = randint(20, 59)
            seconds = randint(0, 59)
            winner = choice((team_1_id, team_2_id))
            match = Match(tournament=t, game=t.game, game_mode=t.game_mode, team_1_id=team_1_id, team_2_id=team_2_id,
                          duration=timedelta(minutes=minutes, seconds=seconds), winner_id=winner)
            match.save()

            # random players for first team
            team_1 = Team.objects.get(pk=team_1_id)
            players = set(team_1.team_members.all().values_list('id', flat=True))
            count = t.game_mode.team_player_count
            p1 = sample(players, count)
            for i in range(0, count):
                played = PlayedMatch(player_id=p1[i], team=team_1, clan=team_1.clan, match=match)
                played.save()

            # random players for second team
            team_2 = Team.objects.get(pk=team_2_id)
            players = set(team_2.team_members.all().values_list('id', flat=True))
            p2 = sample(players, count)
            for i in range(0, count):
                played = PlayedMatch(player_id=p2[i], team=team_2, clan=team_2.clan, match=match)
                played.save()

            self.generateStats(match, p1, p2)

            return JsonResponse(response_data)

        return HttpResponseRedirect(reverse("leagues:tournaments"))


class MatchDetailView(generic.DetailView):
    template_name = "leagues/match_detail.html"
    model = Match

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.get_object()
        players_1 = list(PlayedMatch.objects.filter(match=match, team=match.team_1))
        players_2 = list(PlayedMatch.objects.filter(match=match, team=match.team_2))
        players = []
        for i in range(len(players_1)):
            players.append((players_1[i], players_2[i]))

        deaths = Death.objects.filter(match=match)

        context['deaths'] = deaths
        context['assist_num'] = range(1, match.game_mode.team_player_count - 1)
        context['teams'] = (match.team_1, match.team_2)
        context['players'] = players
        # TODO footer tabulky u statistik se jebe (rika ze ukazuje 5 ale je tam vse)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)


class TournamentDetailView(generic.DetailView):
    template_name = "leagues/tournament_detail.html"
    model = Tournament

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_object()
        teams = Team.objects.filter(tournaments=tournament)  # TODO u prize a amount nevim jednotku!!
        team_matches = []
        registered = None
        for team in teams:
            if RegisteredTeams.objects.filter(team=team, tournament=tournament):
                registered = team
            all_matches = team.all_tournament_matches(tournament.id)
            won_matches = team.matcher_won_tournament(tournament.id)
            win_rate = team.win_ratio_tournament(tournament.id)
            team_matches.append((team, all_matches, won_matches, win_rate))
        matches = Match.objects.filter(tournament=tournament)
        sponsors = Sponsorship.objects.filter(tournament=tournament)
        main_sponsor = sponsors.get(type='MAIN')
        context['registered'] = registered
        context['main_sponsor'] = main_sponsor
        context['team_matches'] = team_matches
        context['matches'] = matches
        context['sponsors'] = sponsors
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        tournament = self.get_object()
        response_data = {}

        form_data_dict = {}
        form_data_list = json.loads(request.POST['data'])
        for field in form_data_list:
            form_data_dict[field["name"]] = field["value"]

        if action_key == 'set_teams':
            clan_id = form_data_dict['clan']
            teams = Team.objects.filter(clan_id=clan_id, game=tournament.game, active=True)
            valid_teams = []
            for team in teams:
                if Player.objects.filter(team=team).count() >= tournament.game_mode.team_player_count:
                    valid_team = [team.id, team.name]
                    valid_teams.append(valid_team)
            if valid_teams:
                response_data['teams'] = json.dumps({"data": valid_teams})
                response_data['status'] = "good"
            else:
                response_data['status'] = "error"
            return JsonResponse(response_data)
        elif action_key == 'team_selected':
            team_id = int(form_data_dict['team_select'])
            team = Team.objects.get(pk=team_id)
            register = RegisteredTeams(team=team, tournament=tournament)
            register.save()
            return JsonResponse(response_data)
        elif action_key == 'unregister':
            team_id = int(form_data_dict['team_unreg'])
            team = RegisteredTeams.objects.filter(team_id=team_id)
            team.tournaments.remove(tournament)
            team.save()
            return JsonResponse(response_data)

        return HttpResponseRedirect(reverse("leagues:tournament_detail", args=[tournament.slug]))


class GameDetailView(generic.DetailView):
    template_name = "leagues/game_detail.html"
    model = Game

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = self.get_object()
        players = Player.objects.filter(games=game)
        context['players'] = players
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)


class GameModeDetailView(generic.DetailView):
    template_name = "leagues/game_mode_detail.html"
    model = GameMode

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mode = self.get_object()
        games = Game.objects.filter(game_modes=mode)
        context['games'] = games
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)


class GenreDetailView(generic.DetailView):
    template_name = "leagues/genre_detail.html"
    model = Genre

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genre = self.get_object()
        games = Game.objects.filter(genre=genre)
        context['games'] = games
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['reg_tournaments'] = registered_tournaments(request.user.player)
        return render(request, self.template_name, context)

