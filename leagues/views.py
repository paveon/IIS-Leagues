from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic, View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.forms.models import model_to_dict
from django_countries.fields import Country
from django.db.models import F, Q
from random import randint, choice, sample
from datetime import timedelta
import json
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
        # TODO nejde pridat klan k tymu pokud uz odehral hru
        # TODO omezit vybery leader tymu muze byt jen nekdo kdo je v tom tymu (stejne klan), hry pro tymy omezeny podle her klanu (nebo se ke specializacim klanu potom prida ta hra tymu?)
        # TODO add new nevytvori novy formular pokud v predchozim byla chyba takze bud clear tlacitko a nebo to nejak vyresit at se udela prazdny formular po kliknuti na new pri predchozim erroru
        # TODO pri vytvareni tournamentu to hodi error a potom po refreshi je to tam, ale hodi to prvni chybu
        # TODO pri vytvareni hry je hra neaktivni a aktivuje se az ma prirazeny gamemode => momentalni kvuli testovani je default true ale ma byt false (doplnit pri vytvareni hry)
        # TODO pri vytvareni hrace se stejnym nickname se chyba zobrazi ale formular zavre takze to vypada jako kdyby se vytvoril
        if create_form.is_bound and create_form.is_valid():
            # commit=False doesn't save new model object directly into the DB
            # so we can do additional processing before storing it in the DB with save method of model object
            model_object = create_form.save(commit=False)
            model_object.save()  # save object do DB
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
            self.context['error_modal'] = self.request.POST['post_action'].split('_')[0] + '_form'
            object_id = self.request.POST['object_id']
            if object_id:
                self.context['object_id'] = object_id
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

        # Join all 3 types of teams into a single list
        teams = joined_teams + pending_teams + remaining_teams

        context['player_list'] = Player.objects.all()
        context['player'] = player
        context['clan_pendings'] = player.clan_pendings.all()
        context['team_list'] = teams
        context['clan_list'] = Clan.objects.all()
        context['membership'] = MembershipStatus.__members__
        return context

    def post(self, request, *args, **kwargs):
        self.action_key = request.POST['action']
        self.player_id = request.POST['player_id']
        self.object_id = request.POST['object_id']
        self.player = Player.objects.get(pk=self.player_id)
        action = self.actions[self.action_key]
        action()
        return JsonResponse(self.response)


@method_decorator(never_cache, name='dispatch')
class PlayerDetailView(generic.DetailView):
    template_name = "leagues/player_detail.html"
    model = Player

    def edit_player(self):
        user = self.player.user
        edit_form = PlayerForm(self.request.POST, instance=self.player, prefix='player_form')
        if edit_form.is_bound and edit_form.is_valid():
            player = edit_form.save(commit=False)
            player.user = user
            player.save()

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


def force_join_team(team, player):
    join_clan(team.clan, player)
    join_team(team, player, None)


def leave_team(team, player):
    team.team_members.remove(player)

    if team.leader == player:
        # Leader is leaving
        team.leader = team.team_members.first()

        # If there were no members left, check if there are pending players
        if not team.leader:
            # If team has clan, pick first pending player from this clan
            if team.clan:
                new_member = team.team_pendings.filter(clan=team.clan).first()
            else:
                new_member = team.team_pendings.first()

            if new_member:
                team.team_pendings.remove(new_member)
                team.team_members.add(new_member)
                team.leader = new_member
        team.save()


def join_team(team, player, response):
    # Player must be member of parent clan
    if team.clan and not player.clan:
        if team.clan in player.clan_pendings.all():
            # Player is already waiting to be accepted into the clan
            player.team_pendings.add(team)
        else:
            response['need_clan'] = (team.clan.name, team.clan.id)
    else:
        if team.leader:
            player.team_pendings.add(team)
        else:
            # Team has no members, join immediately and become new leader
            team.team_members.add(player)
            team.leader = player
            team.save()


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

    def __init__(self):
        super().__init__()
        self.team = None
        self.object_id = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'join_team': self.join_team,
            'force_join_team': self.force_join_team,
            'leave_team': self.leave_team,
            'leave_tournament': self.leave_tournament,
            'join_tournament': self.join_tournament,
            'kick_player': self.kick_player,
            'decline_request': self.process_request,
            'accept_request': self.process_request,
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

        context['membership_requests'] = self.team.team_pendings.all()
        context['registered'] = registered
        context['non_registered'] = non_registered
        context['member_matches'] = member_matches
        return context

    def post(self, request, *args, **kwargs):
        self.action_key = request.POST['action']
        self.team = self.get_object()
        self.object_id = int(request.POST['object_id'])
        action = self.actions[self.action_key]
        action()
        return JsonResponse(self.response)


def force_leave_clan(clan, player):
    # Leave all clan teams when force leaving clan
    for team in player.teams.filter(clan=clan):
        leave_team(team, player)
    leave_clan(clan, player, None)


def leave_clan(clan, player, response):
    clan_teams = player.teams.filter(clan=clan)
    if clan_teams.exists():
        # Player is in clan team
        teams = [(team.name, team.id) for team in clan_teams]
        response['has_clan_teams'] = teams
    else:
        clan.clan_members.remove(player)
        if clan.leader == player:
            # Leader is leaving
            clan.leader = clan.clan_members.first()
            if not clan.leader:
                # Clan had no members left, pick first pending player
                new_member = clan.clan_pendings.first()
                if new_member:
                    clan.clan_pendings.remove(new_member)
                    clan.clan_members.add(new_member)
                    clan.leader = new_member
            clan.save()


def join_clan(clan, player):
    if clan.leader:
        player.clan_pendings.add(clan)
    else:
        # Clan has no members, join immediately and become new leader
        # First remove all other clan pendings
        pendings = player.clan_pendings.all()
        player.clan_pendings.remove(*pendings)

        # Also remove pendings of teams from other clans, ignore teams without clan
        pendings = player.team_pendings.filter(Q(clan__isnull=False) & ~Q(clan=clan))
        player.team_pendings.remove(*pendings)

        player.clan = clan
        player.save()
        clan.leader = player
        clan.save()


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
        members = self.clan.clan_members.all()
        member_matches_list = []
        clan_matches = PlayedMatch.objects.filter(clan=self.clan)

        for member in members:
            member_matches = clan_matches.filter(player=member)
            matches_won = member_matches.filter(team=F('match__winner')).count()
            matches_total = member_matches.count()
            win_ratio = self.win_ratio(matches_won, matches_total)
            member_matches_list.append((member, matches_total, matches_won, win_ratio))

        clan_matches = clan_matches.values('match').distinct()
        matches_won = clan_matches.filter(team=F('match__winner')).count()
        matches_total = clan_matches.count()
        win_ratio = self.win_ratio(matches_won, matches_total)
        stats = (matches_total, matches_won, win_ratio)

        context['stats'] = stats
        context['clan_teams'] = self.clan.team_set.all()
        context['member_matches'] = member_matches_list
        context['membership_requests'] = self.clan.clan_pendings.all()
        return context

    def force_leave_clan(self):
        force_leave_clan(self.clan, self.player)

    def leave_clan(self):
        leave_clan(self.clan, self.player, self.response)

    def join_clan(self):
        join_clan(self.clan, self.player)

    def kick_player(self):
        # Kick player out of every clan team
        self.player.teams.remove(*self.player.teams.filter(clan=self.clan))

        # Also remove all pendings to clan teams
        active_pendings = self.player.team_pendings.filter(clan=self.clan)
        self.player.team_pendings.remove(*active_pendings)
        self.clan.clan_members.remove(self.player)

    def process_request(self):
        self.clan.clan_pendings.remove(self.player)
        if self.action_key == 'accept_request':
            self.clan.clan_members.add(self.player)

    def __init__(self):
        super().__init__()
        self.clan = None
        self.player_id = None
        self.player = None
        self.action_key = None
        self.response = {}
        self.actions = {
            'join_clan': self.join_clan,
            'leave_clan': self.leave_clan,
            'force_leave_clan': self.force_leave_clan,
            'kick_player': self.kick_player,
            'accept_request': self.process_request,
            'decline_request': self.process_request
        }

    def post(self, request, *args, **kwargs):
        self.clan = self.get_object()
        self.action_key = request.POST['action']
        self.player_id = request.POST['player_id']
        self.player = Player.objects.get(pk=self.player_id)
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

        context['match_form'] = MatchForm(prefix='match_create')
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

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)
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
                dictionaries = [team.team.as_array() for team in registered_teams]
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
            possible_teams = Team.objects.filter(game_id=game)
            for t in possible_teams:
                if t.team_members.all().count() >= GameMode.objects.get(pk=game_mode).team_player_count:
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
            possible_teams = Team.objects.filter(Q(game_id=game) & ~Q(clan=team.clan))
            for t in possible_teams:
                t1 = Team.objects.get(pk=team_1)
                players1 = t.team_members.all()
                players2 = t1.team_members.all()
                players = players1.difference(players2).count()
                players1 = players1.count() - players
                count = GameMode.objects.get(pk=game_mode).team_player_count
                # if distinct number of player of both teams can make together
                if (players1 + players2.count()) >= (2 * count) and (players1 + players) >= count:
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
            minutes = randint(20, 59)
            seconds = randint(0, 59)
            mode = GameMode.objects.get(pk=game_mode)
            winner = choice((team_1_id, team_2_id))
            match = Match(game_id=game, game_mode_id=game_mode, team_1_id=team_1_id, team_2_id=team_2_id,
                          duration=timedelta(minutes=minutes, seconds=seconds), winner_id=winner)
            match.save()

            # random players for first team
            team_1 = Team.objects.get(pk=team_1_id)
            players = set(team_1.team_members.all().values_list('id', flat=True))
            count = mode.team_player_count
            p1 = sample(players, count)
            for i in range(0, count):
                played = PlayedMatch(player_id=p1[i], team=team_1, clan=team_1.clan, match=match)
                played.save()

            # random players for second team
            team_2 = Team.objects.get(pk=team_2_id)
            players = set(team_2.team_members.all().values_list('id', flat=True))
            players.intersection(p1)
            p2 = sample(players, count)
            for i in range(0, count):
                played = PlayedMatch(player_id=p2[i], team=team_2, clan=team_2.clan, match=match)
                played.save()

            self.generateStats(match, p1, p2)

            return JsonResponse(response_data)  # TODO generovani udalosti
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


class GameModeDetailView(generic.DetailView):
    template_name = "leagues/game_mode_detail.html"
    model = GameMode

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mode = self.get_object()
        games = Game.objects.filter(game_modes=mode)
        context['games'] = games
        return context


class GenreDetailView(generic.DetailView):
    template_name = "leagues/genre_detail.html"
    model = Genre

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genre = self.get_object()
        games = Game.objects.filter(genre=genre)
        context['games'] = games
        return context
