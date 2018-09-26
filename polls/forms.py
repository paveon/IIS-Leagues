from django import forms
from django.forms import ModelForm
from polls.models import *


class BaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            added_classes = ' form-control'
            key = 'class'
            if key in field.widget.attrs:
                field.widget.attrs[key] += added_classes
            else:
                field.widget.attrs[key] = added_classes


class CalendarWidget(forms.TextInput):
    class Media:
        js = ('polls/date_picker.js',)


class PlayerForm(BaseForm):
    class Meta:
        model = Player
        fields = ['nickname', 'first_name', 'last_name', 'country', 'birth_date']
        widgets = {
            'birth_date': CalendarWidget(attrs={'class': 'date_picker'}),
        }


class NameForm(forms.Form):
    your_name = forms.CharField(label='Your name', max_length=100)