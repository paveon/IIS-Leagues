# Generated by Django 2.1.1 on 2018-11-25 14:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0034_remove_clan_games'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='clan_1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clan_matches_a', to='leagues.Clan', verbose_name='clan of first team'),
        ),
        migrations.AddField(
            model_name='match',
            name='clan_2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clan_matches_b', to='leagues.Clan', verbose_name='clan of second team'),
        ),
    ]
