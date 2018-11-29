from builtins import type

from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from leagues.models import *
from leagues.model_actions import *


class CalendarWidget(forms.TextInput):
    def __init__(self):
        super().__init__(attrs={
            'class': 'date_picker',
        })

    class Media:
        js = (
            'leagues/js/date_picker.js',
        )


class MyUserForm(UserCreationForm):
    birth_date = forms.DateField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'birth_date', 'first_name', 'last_name']
        widgets = {
            'birth_date': CalendarWidget(),
        }

    def save(self, commit=True):
        if not commit:
            raise NotImplementedError("Can't create User and UserProfile without database save")
        user = super().save(commit=True)
        username = self.cleaned_data['username']
        birth_date = self.cleaned_data['birth_date']
        user_profile = Player(nickname=username, birth_date=birth_date, user=user)
        user_profile.save()
        user.player = user_profile
        user.save()
        return user, user_profile

    def clean(self):
        cleaned_data = super().clean()
        born = cleaned_data['birth_date']
        today = datetime.date.today()
        if born > today:
            raise ValidationError('Invalid birth date, can\'t be in future')
        else:
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if age < 15:
                raise ValidationError('Player must be at least 15 years old!')
            else:
                return cleaned_data


class PlayerForm(ModelForm):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = Player
        fields = ['nickname', 'first_name', 'last_name', 'country',
                  'birth_date', 'description', 'image_url'
                  ]
        widgets = {
            'birth_date': CalendarWidget(),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        player = self.instance
        if player.pk:
            self.fields['first_name'].initial = player.user.first_name
            self.fields['last_name'].initial = player.user.last_name

    def clean(self):
        cleaned_data = super().clean()
        born = cleaned_data['birth_date']
        today = datetime.date.today()
        if born > today:
            raise ValidationError('Invalid birth date, can\'t be in future')
        else:
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if age < 15:
                raise ValidationError('Player must be at least 15 years old!')

        return cleaned_data

    def save(self, commit=True):
        player = super().save(commit=False)
        if player.user:
            first_name = self.cleaned_data['first_name']
            last_name = self.cleaned_data['last_name']
            player.user.first_name = first_name
            player.user.last_name = last_name
        if commit:
            player.save()
        return player


class SettingsPlayerForm(PlayerForm):
    ROLES = (
        (1, 'Staff'),
        (2, 'User'),
    )

    role = forms.ChoiceField(choices=ROLES, initial=2)

    class Meta(PlayerForm.Meta):
        fields = PlayerForm.Meta.fields + ['role']

    def save(self, commit=True):
        player = super().save(commit=False)
        if not player.user:
            # Creating new player, create new corresponding user with generic password
            nickname = self.cleaned_data['nickname']
            user = User(username=nickname)
            user.set_password('1234')
            player.user = user

        role = int(self.cleaned_data['role'])
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        player.user.first_name = first_name
        player.user.last_name = last_name
        player.user.is_staff = (role == UserRole.STAFF.value)
        if commit:
            player.save()
        return player


class SponsorForm(ModelForm):
    class Meta:
        model = Sponsor
        fields = ['name']


class SponsorshipForm(ModelForm):
    class Meta:
        model = Sponsorship
        fields = ['sponsor', 'tournament', 'type', 'amount']

    def clean(self):
        cleaned_data = super().clean()
        tournament = cleaned_data['tournament']
        sponsorship_type = cleaned_data['type']
        if sponsorship_type == 'MAIN':
            if tournament.sponsorship_set.filter(type='MAIN').exists():
                raise ValidationError('Tournament can have only one main sponsor')
        return cleaned_data


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'opening_date', 'end_date', 'description', 'game', 'game_mode']
        widgets = {
            'opening_date': CalendarWidget(),
            'end_date': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super().clean()
        begin = cleaned_data['opening_date']
        end = cleaned_data['end_date']
        tommorow = datetime.date.today() + datetime.timedelta(days=1)
        tournament = self.instance
        if tournament.pk:
            # Editing existing one
            status = tournament.status
            if status == TournamentStatus.UPCOMING:
                if begin < tommorow:
                    raise ValidationError('Upcoming tournament can begin tommorow at the earliest')

            elif status == TournamentStatus.IN_PROGRESS:
                if begin != tournament.opening_date:
                    self.cleaned_data['opening_date'] = tournament.opening_date
                    raise ValidationError('Cannot change opening date of tournament '
                                          'which is already in progress')
                elif end < tournament.end_date:
                    self.cleaned_data['end_date'] = tournament.end_date
                    raise ValidationError('Tournament which is in progress can only be extended')
            else:
                if begin != tournament.opening_date:
                    self.cleaned_data['opening_date'] = tournament.opening_date
                    raise ValidationError('Cannot change opening date of tournament '
                                          'which has already ended')
                if end != tournament.end_date:
                    self.cleaned_data['end_date'] = tournament.end_date
                    raise ValidationError('Cannot change end date of tournament '
                                          'which has already ended')
        else:
            if begin < tommorow:
                raise ValidationError('Upcoming tournament can begin tommorow at the earliest')

        if end < begin:
            raise ValidationError('Tournament cannot end before it starts')
        elif end == begin:
            raise ValidationError('Tournament cannot end at the same day it starts')

        return cleaned_data


class ClanForm(ModelForm):
    class Meta:
        model = Clan
        fields = ['name', 'founded', 'country', 'leader', 'description']
        widgets = {
            'founded': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super().clean()
        clan = self.instance
        foundation_date = cleaned_data['founded']
        if foundation_date > datetime.date.today():
            raise ValidationError('Clan cannot be founded in future')

        if clan.pk:
            # When editing, foundation date cannot be after first match (if any)
            matches = clan.all_matches
            for match in matches:
                # queryset filter somehow doesnt work on datetimes...
                begin_datetime = match.beginning
                if begin_datetime.date() < foundation_date:
                    raise ValidationError('Clan cannot be founded after first played match')

            if 'leader' in self.changed_data:
                # Changing leader of the clan
                new_clan_leader = cleaned_data['leader']
                if new_clan_leader:
                    if not new_clan_leader.clan:
                        # New leader is not member of this clan
                        clan.leader = None
                        join_clan(clan, new_clan_leader)

                    clan.leader = new_clan_leader
                    clan.save()
                else:
                    # Clan must have a leader unless it has no members.
                    # If current leader is the last member, kick him from
                    # clan and all clan teams. Otherwise its an error
                    if clan.clan_members.all().count() == 1:
                        force_leave_clan(clan, clan.leader)
                    else:
                        raise ValidationError('Clan must have a leader unless it has no members')

        return cleaned_data


class TeamFormUser(ModelForm):
    class Meta:
        model = Team
        fields = ['clan']


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'founded', 'active', 'leader', 'game', 'clan', 'description']
        widgets = {
            'founded': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super().clean()
        team = self.instance
        foundation_date = cleaned_data['founded']
        if foundation_date > datetime.date.today():
            raise ValidationError('Team cannot be founded in future')

        if team.pk:
            # When editing, foundation date cannot be after first match (if any)
            matches = team.all_matches.all()
            for match in matches:
                # queryset filter somehow doesnt work on datetimes...
                begin_datetime = match.beginning
                if begin_datetime.date() < foundation_date:
                    raise ValidationError('Team cannot be founded after first played match')

            if 'leader' in self.changed_data:
                # Changing leader of the team
                new_team_leader = cleaned_data['leader']
                if new_team_leader:
                    if team.clan and new_team_leader.clan != team.clan:
                        # Team is under clan and player is not part of it
                        clan_leader = team.clan.leader
                        if clan_leader:
                            # Hack around join_clan function, save old clan leader
                            # and restore it after joining the clan
                            team.clan.leader = None
                            join_clan(team.clan, new_team_leader)
                            team.clan.leader = clan_leader
                            team.clan.save()
                        else:
                            join_clan(team.clan, new_team_leader)

                    if new_team_leader not in team.team_members.all():
                        # Player is not a team member yet
                        if team.leader:
                            # Hack around join_team function so that player
                            # can join immediately
                            team.leader = None
                        join_team(team, new_team_leader, None)
                    team.leader = new_team_leader
                    team.save()

                else:
                    # Team must have a leader unless it has no members.
                    # If current leader is the last member, kick him from
                    # team. Otherwise its an error
                    if team.team_members.all().count() == 1:
                        leave_team(team, team.leader)
                    else:
                        raise ValidationError('Team must have a leader unless it has no members')

            if 'clan' in self.changed_data:
                # Changing clan
                new_clan = cleaned_data['clan']
                if new_clan:
                    team_members = team.team_members.all()
                    if team_members.exclude(clan=new_clan).exists():
                        # Team has a member which is not member of specified clan
                        raise ValidationError('All team members must be members of specified clan'
                                              ' in order to move team under clan')
                team.clan = new_clan
                team.save()

        return cleaned_data


class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'release_date', 'publisher', 'image_url', 'description', 'genre', 'game_modes']
        widgets = {
            'release_date': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super().clean()
        release_date = cleaned_data['release_date']
        if release_date and release_date > datetime.date.today():
            raise ValidationError('Game not released yet')

        game = self.instance
        if game.pk:
            submit_genre = cleaned_data['genre']
            submit_modes = cleaned_data['game_modes']
            if release_date:
                matches = game.match_set.all()
                for match in matches:
                    begin_datetime = match.beginning
                    if begin_datetime.date() < release_date:
                        raise ValidationError('Game cannot be released after first played match')

            if game.genre != submit_genre and game.match_set.all().count() > 0:
                raise ValidationError('Cannot change genre of game with existing matches')

            removed_modes = game.game_modes.all().difference(submit_modes)
            for mode in removed_modes:
                if Match.objects.filter(game_mode=mode).exists():
                    raise ValidationError('Cannot remove game mode with existing matches')

        return cleaned_data


class GenreForm(ModelForm):
    class Meta:
        model = Genre
        fields = ['name', 'acronym', 'description']


class GameModeForm(ModelForm):
    class Meta:
        model = GameMode
        fields = ['name', 'team_player_count', 'description']
        widgets = {
            'team_player_count': forms.NumberInput(attrs={'min': 1, 'max': 50, 'type': 'number'})
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['team_player_count'] > 50:
            raise ValidationError('Game mode can support only up to 50 players per team')

        mode = self.instance
        if mode.pk:
            count_changed = 'team_player_count' in self.changed_data
            if count_changed and mode.match_set.all().exists():
                raise ValidationError('Cannot change player count of game mode with existing matches')


class MatchForm(ModelForm):
    class Meta:
        model = Match
        fields = ['game', 'game_mode', 'tournament', 'team_1', 'team_2']
