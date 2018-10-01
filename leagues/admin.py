from django.contrib import admin
from .models import Question, Choice


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'pub_date', 'was_published_recently')
    fields = ['pub_date', 'question_text']
    inlines = [ChoiceInline]
    list_filter = ['pub_date']
    search_fields = ['question_text']


# Register your models here.
admin.site.register(Question, QuestionAdmin)
