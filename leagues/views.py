from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views import generic, View
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


class SocialView(generic.TemplateView):
    template_name = "leagues/social.html"

    def cancel_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)

        jsonResponse = {}

        if request_type == 'cancel_team':
            team = Team.objects.get(pk=object_id)
            player.team_pendings.remove(team)
        elif request_type == 'cancel_clan':
            clan = Clan.objects.get(pk=object_id)
            player.clan_pendings.remove(clan)

            # Also remove pendings into clan's teams
            relations = player.team_pendings.through.objects.filter(team__clan=clan)
            relations.delete()

        return jsonResponse

    # Processes join request for teams and clans
    def join_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)
        group_pendings = None
        group_members = None
        group = None
        response = {}

        # Nested method to avoid code duplication
        def join_group(clan):
            if group.leader:
                # Need confirmation if group has a leader
                group_pendings.add(group)
                player.save()
            else:
                # Join immediately and become new leader
                group.leader = player
                if clan:
                    # remove all other clan pendings while entering clan without leader
                    player.clan_pendings.remove(*player.clan_pendings.all())

                    # remove pendings of teams from other clans, ignore teams without clan
                    pendings = player.team_pendings.filter(Q(clan__isnull=False) & ~Q(clan=group))
                    player.team_pendings.remove(*pendings)

                    player.clan = group
                    player.save()

                    # pendings_to_remove = player.clan_pendings.all()
                    # for pending in pendings_to_remove:
                    #     group_pendings.remove(pending)
                    # pendings_to_remove = player.team_pendings.all()
                    # for pending in pendings_to_remove:
                    #     if pending.clan != group and pending.clan:  # remove all team pendins with teams which have clans
                    #         player.team_pendings.remove(pending)
                else:
                    group_members.add(player)
                group.save()

        # Check which type of request it is and initialize common variables
        if request_type == 'force_join_team':
            request_type = 'join_team'
            team = Team.objects.get(pk=object_id)
            group = team.clan
            group_pendings = player.clan_pendings
            join_group(True)

        if request_type == 'join_team':
            player_clan = player.clan
            group = Team.objects.get(pk=object_id)
            team_clan = group.clan
            # Check if player is in parent clan of team
            if team_clan and not player_clan:
                if team_clan.clan_pendings.filter(pk=player.pk).exists():
                    group.team_pendings.add(player)
                    group.save()
                else:
                    response['need_clan'] = (team_clan.name, team_clan.id)

                return response

            group_members = group.team_members
            group_pendings = player.team_pendings
            join_group(False)

        elif request_type == 'join_clan':
            group = Clan.objects.get(pk=object_id)
            group_members = Player.objects.filter(clan=group)
            group_pendings = player.clan_pendings
            join_group(True)

        return response

    def leave_request(self, request_type):
        player_id = self.request.POST['player_id']
        object_id = self.request.POST['object_id']
        player = Player.objects.get(pk=player_id)
        group = None
        group_members = None
        jsonResponse = {}
        is_clan = False

        # Nested method to avoid code duplication
        def leave_group():
            if is_clan:
                player.clan = None
                player.save()
                pendings = player.team_pendings.all()
                for pending in pendings:
                    if pending.clan == group:
                        player.team_pendings.remove(pending)
                        player.save()
            else:
                group_members.remove(player)
            # Check if leaving player is a group leader and revoke the privilege if so
            if group.leader and group.leader.id == player.id:
                # Pick first player to become a new leader (None if there are no players left)
                group.leader = group_members.first()
                group.save()

        if request_type == 'force_leave_clan':
            # Leave all clan teams and then leave the clan
            request_type = 'leave_clan'
            joined_clan_teams = player.teams.all().filter(clan=player.clan)
            for team in joined_clan_teams:
                group = team
                group_members = team.team_members
                leave_group()

        if request_type == 'leave_team':
            group = Team.objects.get(pk=object_id)
            group_members = group.team_members
        elif request_type == 'leave_clan':
            group = Clan.objects.get(pk=object_id)
            group_members = group.clan_members
            joined_clan_teams = player.teams.all().filter(clan=group)
            is_clan = True

            # Check if player is in any team under this clan
            if joined_clan_teams.count() > 0:
                teams = [(team.name, team.id) for team in joined_clan_teams.all()]
                jsonResponse['has_clan_teams'] = teams
                return jsonResponse

        if group:
            leave_group()
        return jsonResponse

    def __init__(self):
        super().__init__()
        self.actions = {
            'cancel_team': self.cancel_request,
            'cancel_clan': self.cancel_request,
            'join_team': self.join_request,
            'join_clan': self.join_request,
            'leave_team': self.leave_request,
            'leave_clan': self.leave_request,
            'force_join_team': self.join_request,
            'force_join_clan': self.join_request,
            'force_leave_clan': self.leave_request,
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
        context = super().get_context_data(**kwargs)
        player_id = request.POST['player_id']
        player = Player.objects.get(pk=player_id)

        if request.is_ajax():
            # Get callable object from action dictionary and call action method
            action_key = request.POST['action']
            action = self.actions[action_key]
            jsonResponse = action(action_key)
            return JsonResponse(jsonResponse)

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

    def leave_clan(self):
        player = self.get_object()
        teams = player.teams.filter(clan=player.clan)
        player.teams.remove(*teams)

        team_pendings = player.team_pendings.filter(clan=player.clan)
        player.team_pendings.remove(*team_pendings)

        player.clan = None
        player.save()

    def leave_team(self, team_id):
        player = self.get_object()
        team = Team.objects.get(pk=team_id)
        teams = player.teams.remove(team)

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        edit_form = PlayerForm(instance=self.object, prefix='player_form')
        context['player_form'] = edit_form
        context['authorized'] = (self.object.user == self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        player = self.get_object()
        if action_key == 'player_edit':
            self.edit_player()
        elif action_key == 'leave_clan':
            self.leave_clan()
            return JsonResponse({})
        else:
            self.leave_team(request.POST['object_id'])
            return JsonResponse({})

        return HttpResponseRedirect(reverse("leagues:player_detail", args=[player.slug]))



class TeamDetailView(generic.DetailView):
    template_name = "leagues/team_detail.html"
    model = Team

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        members = team.team_members.all()
        member_matches = []
        for member in members:
            team_matches = PlayedMatch.objects.filter(team=team, player=member)
            won_matches = team_matches.filter(match__winner=team)
            member_matches.append((member, team_matches, won_matches))

        registered = Tournament.objects.filter(team=team)
        non_registered = Tournament.objects.filter(Q(game=team.game) & ~Q(team=team))

        context['registered'] = registered
        context['non_registered'] = non_registered
        context['member_matches'] = member_matches
        return context

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        team = self.get_object()
        response = {}
        if action_key == 'leave_tournament':
            tournament_id = int(request.POST['object_id'])
            tournaments = RegisteredTeams.objects.filter(team=team, tournament_id=tournament_id)
            tournaments.delete()
        elif action_key == 'join_tournament':
            tournament_id = int(request.POST['object_id'])
            tournament = Tournament.objects.get(pk=tournament_id)
            teams = RegisteredTeams.objects.filter(team__clan=team.clan)
            if teams.filter(tournament_id=tournament_id):
                response['error'] = "teams"
            elif Player.objects.filter(teams=team).count() < tournament.game_mode.team_player_count:
                response['error'] = "players"
            else:
                tournaments = RegisteredTeams(team=team, tournament_id=tournament_id)
                tournaments.save()

        return JsonResponse(response)


class ClanDetailView(generic.DetailView):
    template_name = "leagues/clan_detail.html"
    model = Clan

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clan = self.get_object()
        members = clan.clan_members.all()
        member_matches = []
        win_ratio = None
        for member in members:
            clan_matches = PlayedMatch.objects.filter(clan=clan, player=member)
            won_matches = clan_matches.filter(team=F('match__winner'))
            if clan_matches:
                win_ratio = str(round((won_matches.count() / clan_matches.count()) * 100, 2)) + " %"
            member_matches.append((member, clan_matches, won_matches, win_ratio))
        context['member_matches'] = member_matches
        clan_teams = Team.objects.filter(clan_id=clan.id)

        all_matches = PlayedMatch.objects.filter(clan=clan).values_list("match").distinct()
        win_matches = all_matches.filter(team=F('match__winner'))
        win_ratio = None
        if all_matches.count() != 0:
            win_ratio = str(round((win_matches.count() / all_matches.count()) * 100, 2)) + " %"
        stats = (all_matches, win_matches, win_ratio)
        context['stats'] = stats
        context['clan_teams'] = clan_teams
        return context

    def leave_request(self):
        player_id = self.request.POST['player_id']
        clan_id = self.request.POST['clan_id']
        player = Player.objects.get(pk=player_id)
        teams = player.teams.all()
        for team in teams:
            if team.clan_id == int(clan_id):
                player.teams.remove(team)

        player.save()

        group = Clan.objects.get(pk=clan_id)
        group_members = group.clan_members

        group_members.remove(player)
        group.leader = group_members.first()
        group.save()

    def kick_request(self):
        player_id = self.request.POST['player_id']
        clan_id = self.request.POST['clan_id']
        player = Player.objects.get(pk=player_id)
        group = Clan.objects.get(pk=clan_id)

        teams = player.teams.all()
        for team in teams:
            if team.clan_id == int(clan_id):
                player.teams.remove(team)
                player.save()
        pendings = player.team_pendings.all()
        for pending in pendings:
            if pending.clan == group:
                player.team_pendings.remove(pending)
                player.save()

        group.clan_members.remove(player)
        group.save()

    def __init__(self):
        super().__init__()
        self.actions = {
            'leave_clan': self.leave_request,
            'kick_player': self.kick_request,
        }

    def post(self, request, *args, **kwargs):
        action_key = request.POST['action']
        action = self.actions[action_key]
        action()
        return JsonResponse({})


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
            num_of_assists = randint(0,match.game_mode.team_player_count - 2)
            who = randint(1,2)
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

            death = Death(match=match, victim_id=victim[0], killer_id=killer[0], match_time=timedelta(seconds=event_time))
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
                if (players1 + players2.count()) >= (2*count) and (players1 + players) >= count:
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
        context['assist_num'] = range(1, match.game_mode.team_player_count-1)
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
