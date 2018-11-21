from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from leagues.models import *

class CalendarWidget(forms.TextInput):
    def __init__(self):
        super().__init__(attrs={'class': 'date_picker'})

    class Media:
        js = (
            'leagues/js/date_picker.js',
        )


class PlayerForm(ModelForm):
    class Meta:
        model = Player
        fields = ['nickname', 'first_name', 'last_name', 'country',
                  'birth_date', 'description', 'image_url', 'user'
                  ]
        widgets = {
            'birth_date': CalendarWidget(),
        }

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


class SponsorForm(ModelForm):
    class Meta:
        model = Sponsor
        fields = ['name']


class SponsorshipForm(ModelForm):
    class Meta:
        model = Sponsorship
        fields = ['sponsor', 'tournament', 'type', 'amount']


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'prize', 'opening_date', 'end_date', 'sponsors', 'description', 'game', 'game_mode']
        widgets = {
            'opening_date': CalendarWidget(),
            'end_date': CalendarWidget()
        }


class ClanForm(ModelForm):
    class Meta:
        model = Clan
        fields = ['name', 'founded', 'country', 'leader', 'games', 'description']
        widgets = {
            'founded': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super().clean()
        foundation_date = cleaned_data['founded']
        if foundation_date > datetime.date.today():
            raise ValidationError('Clan cannot be founded in future')

        return cleaned_data


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

        if team:
            # When editing, foundation date cannot be after first match (if any)
            matches = team.all_matches.all()
            for match in matches:
                # queryset filter somehow doesnt work on datetimes...
                begin_datetime = match.beginning
                if begin_datetime.date() < foundation_date:
                    raise ValidationError('Team cannot be founded after first played match')

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
        submit_genre = cleaned_data['genre']
        submit_modes = cleaned_data['game_modes']
        if game:
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


class MatchForm(ModelForm):
    class Meta:
        model = Match
        fields = ['game', 'game_mode', 'tournament', 'team_1', 'team_2']