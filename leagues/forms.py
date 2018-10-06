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


class PlayerEditForm(ModelForm):
    class Meta:
        model = Player
        fields = ['nickname', 'first_name', 'last_name', 'country']


class PlayerForm(ModelForm):
    class Meta:
        model = Player
        fields = ['nickname', 'first_name', 'last_name', 'country',
                  'birth_date', 'description', 'image_url', 'user'
                  ]
        widgets = {
            'birth_date': CalendarWidget(),
        }


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
        fields = ['name', 'prize', 'opening_date', 'end_date', 'sponsors', 'description']
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


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'founded', 'active', 'leader', 'game', 'clan', 'description']
        widgets = {
            'founded': CalendarWidget()
        }

    def clean(self):
        cleaned_data = super(TeamForm, self).clean()
        foundation_date = cleaned_data['founded']
        if foundation_date > datetime.date.today():
            raise ValidationError('Team cannot be founded in future')
        return cleaned_data


class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'release_date', 'publisher', 'image_url', 'description', 'genre', 'game_modes']
        widgets = {
            'release_date': CalendarWidget()
        }


class GenreForm(ModelForm):
    class Meta:
        model = Genre
        fields = ['name', 'acronym', 'description']


class GameModeForm(ModelForm):
    class Meta:
        model = GameMode
        fields = ['name', 'team_player_count', 'description']
