from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic, View
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout

from .models import Question, Choice
from .forms import *


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('polls:games'))


class SignupView(View):
    template_name = "polls/signup.html"

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return HttpResponseRedirect(reverse('polls:index'))
        else:
            return render(request, self.template_name, {'form': form})

    def get(self, request):
        form = UserCreationForm()
        return render(request, self.template_name, {'form': form})


class GamesView(generic.TemplateView):
    template_name = "polls/games.html"


class IndexView(generic.ListView):
    template_name = 'polls/index.html'

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
            return HttpResponseRedirect(reverse('polls:index'))
        return render(request, self.template_name)


class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(pub_date__lte=timezone.now())


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'polls/results.html'

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
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))
