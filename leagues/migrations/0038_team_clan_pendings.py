# Generated by Django 2.1.1 on 2018-11-26 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0037_auto_20181126_1051'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='clan_pendings',
            field=models.ManyToManyField(related_name='team_requests', to='leagues.Clan'),
        ),
    ]