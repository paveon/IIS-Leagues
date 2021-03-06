# Generated by Django 2.1.1 on 2018-11-27 14:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0039_auto_20181127_0951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='clan_pending',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='team_requests', to='leagues.Clan'),
        ),
    ]
