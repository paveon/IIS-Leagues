# Generated by Django 2.1.1 on 2018-11-28 10:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0041_remove_tournament_prize'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='player',
            name='last_name',
        ),
    ]
