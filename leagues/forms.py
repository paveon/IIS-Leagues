from django import forms
from django.forms import ModelForm
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
        fields = ['nickname', 'first_name', 'last_name', 'country', 'birth_date']
        widgets = {
            'birth_date': CalendarWidget(),
        }


class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'release_date', 'publisher', 'image_url', 'genre', 'game_modes']
        widgets = {
            'release_date': CalendarWidget()
        }


class GenreForm(ModelForm):
    class Meta:
        model = Genre
        fields = ['name', 'acronym', 'description']


class NameForm(forms.Form):
    your_name = forms.CharField(label='Your name', max_length=100)
