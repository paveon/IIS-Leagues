from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic, View
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Player
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        games = Game.objects.all()
        context['game_list'] = games
        context['game_form'] = GameForm(prefix='game_create')
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
        if 'game_create' in request.POST:
            create_form = GameForm(request.POST, prefix='game_create')
            if create_form.is_bound and create_form.is_valid():
                game_name = create_form.cleaned_data['name']
                if not Game.objects.filter(name=game_name).exists():
                    # commit=False doesn't save new model object directly into the DB
                    # so we can do additional processing before storing it in the DB with save method of model object
                    game_object = create_form.save(commit=False)

                    # ... do additional processing

                    game_object.save()  # save object do DB
                    create_form.save_m2m()  # need to save relations manually with commit=False
                    return HttpResponseRedirect(reverse('leagues:settings'))

        elif 'game_id' in request.POST:
            try:
                game = Game.objects.get(pk=request.POST['game_id'])
                edit_form = GameForm(request.POST, instance=game, prefix='game_edit_' + str(game.id))
                if edit_form.is_bound and edit_form.is_valid():
                    edit_form.save()
                    return HttpResponseRedirect(reverse('leagues:settings'))
                form_list = context['edit_forms']
                form_list[:] = [edit_form if x.instance == game else x for x in form_list]

            except Game.DoesNotExist as err:
                return None

        return render(request, self.template_name, context)


class GamesView(generic.TemplateView):
    template_name = "leagues/games.html"

    def get_form(self, request, form_class, prefix):
        data = request.POST if prefix in request.POST else None
        return form_class(data, prefix=prefix)

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
        if 'game_create' in request.POST:
            create_form = GameForm(request.POST, prefix='game_create')
            if create_form.is_bound and create_form.is_valid():
                game_name = create_form.cleaned_data['name']
                if not Game.objects.filter(name=game_name).exists():
                    # commit=False doesn't save new model object directly into the DB
                    # so we can do additional processing before storing it in the DB with save method of model object
                    game_object = create_form.save(commit=False)

                    # ... do additional processing

                    game_object.save()  # save object do DB
                    create_form.save_m2m()  # need to save relations manually with commit=False
                    return HttpResponseRedirect(reverse('leagues:games'))

        elif 'game_id' in request.POST:
            try:
                game = Game.objects.get(pk=request.POST['game_id'])
                edit_form = GameForm(request.POST, instance=game, prefix='game_edit_' + str(game.id))
                if edit_form.is_bound and edit_form.is_valid():
                    edit_form.save()
                    return HttpResponseRedirect(reverse('leagues:games'))
                form_list = context['edit_forms']
                form_list[:] = [edit_form if x.instance == game else x for x in form_list]

            except Game.DoesNotExist as err:
                return None

        return render(request, self.template_name, context)


class DetailGameView(generic.DetailView):
    model = Game
    template_name = "leagues/game_detail.html"


class IndexView(generic.ListView):
    template_name = 'leagues/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = Question.objects.filter(pub_date__lte=timezone.now()).order_by('-pub_date')[:5]
        context['latest_question_list'] = data
        context['form'] = NameForm()
        context['player'] = PlayerForm()
        return context

    def get_queryset(self):
        return Question.objects.filter(pub_date__lte=timezone.now()).order_by('-pub_date')[:5]

    def post(self, request):
        form = NameForm(self.request.POST)
        if form.is_valid():
            print(form.cleaned_data)
            return HttpResponseRedirect(reverse('leagues:index'))
        return render(request, self.template_name)


class DetailView(generic.DetailView):
    model = Question
    template_name = 'leagues/detail.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(pub_date__lte=timezone.now())


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'leagues/results.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(pub_date__lte=timezone.now())


def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(request, 'leagues/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('leagues:results', args=(question.id,)))
