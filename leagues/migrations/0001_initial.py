# Generated by Django 2.1.1 on 2018-10-04 09:35

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import leagues.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Assist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('HEALING', 'Damage'), ('DAMAGE', 'Healing')], max_length=20, verbose_name='Type of assistance')),
            ],
        ),
        migrations.CreateModel(
            name='Clan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('founded', models.DateField(default=datetime.date.today, verbose_name='foundation date')),
                ('country', models.CharField(blank=True, max_length=200, verbose_name='country of origin')),
            ],
        ),
        migrations.CreateModel(
            name='Death',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('match_time', models.TimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('type', models.CharField(choices=[('KEYBOARD', 'Keyboard'), ('MOUSE', 'Mouse'), ('MONITOR', 'Monitor'), ('MOUSE_PAD', 'Mouse pad'), ('HEADSET', 'Headset')], max_length=20, verbose_name='Kind of equipment')),
                ('manufacturer', models.CharField(blank=True, max_length=200, verbose_name='Equipment manufacturer')),
                ('brand', models.CharField(blank=True, max_length=200, verbose_name='Brand of equipment')),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='name of the game')),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('release_date', models.DateField(blank=True, null=True, verbose_name='release date of the game')),
                ('image_url', models.URLField(blank=True, max_length=500, verbose_name='game image url')),
                ('publisher', models.CharField(blank=True, max_length=200, verbose_name='game publisher')),
                ('description', models.TextField(blank=True, help_text='Description of game', verbose_name='description')),
            ],
        ),
        migrations.CreateModel(
            name='GameMode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the game mode', max_length=100, unique=True)),
                ('team_player_count', models.PositiveSmallIntegerField(blank=True, default=5, help_text='Number of players in one team', null=True)),
                ('description', models.TextField(blank=True, help_text='Description of game mode', verbose_name='description')),
            ],
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the genre of a game', max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('acronym', models.CharField(blank=True, help_text='Game genre acronym', max_length=10)),
                ('description', models.TextField(blank=True, help_text='Description of genre', verbose_name='description')),
            ],
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('beginning', models.DateTimeField(default=django.utils.timezone.now, verbose_name='beginning of the match')),
                ('duration', models.DurationField(verbose_name='duration of the match')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Game', verbose_name='related game')),
                ('game_mode', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.GameMode', verbose_name='game mode of the match')),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=50, unique=True)),
                ('slug', models.SlugField()),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('country', models.CharField(blank=True, max_length=200, verbose_name='country of birth')),
                ('birth_date', models.DateField(blank=True, null=True, verbose_name='date of birth')),
                ('image_url', models.URLField(blank=True, max_length=500, verbose_name='profile image url')),
                ('description', models.TextField(blank=True, help_text='Description of player', verbose_name='description')),
                ('clans', models.ManyToManyField(to='leagues.Clan', verbose_name='Clan memberships')),
                ('equipment', models.ManyToManyField(to='leagues.Equipment', verbose_name='Equipment used by player')),
                ('games', models.ManyToManyField(to='leagues.Game', verbose_name='Games focused by the player')),
                ('matches', models.ManyToManyField(to='leagues.Match', verbose_name='Played matches')),
            ],
        ),
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Sponsorship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('MAIN', 'Main'), ('SIDE', 'Side')], default=('MAIN', 'Main'), max_length=4, verbose_name='sponsorship type')),
                ('amount', models.PositiveIntegerField(blank=True, null=True, verbose_name='donation amount')),
                ('sponsor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Sponsor')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('founded', models.DateField(default=datetime.date.today, verbose_name='foundation date')),
                ('active', models.BooleanField(default=True, verbose_name='activity status')),
                ('clan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leagues.Clan', verbose_name='Related clan')),
                ('game', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leagues.Game', verbose_name='Game focused by the team')),
                ('leader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leagues.Player', verbose_name='Leader of the team')),
            ],
        ),
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='tournament name')),
                ('prize', models.PositiveIntegerField(blank=True, help_text='prize pool in dollars', null=True, verbose_name='tournament prize')),
                ('opening_date', models.DateField(default=datetime.date.today, verbose_name='date of the tournament start')),
                ('end_date', models.DateField(default=leagues.models.end_date_default, verbose_name='date of the tournament end')),
                ('sponsors', models.ManyToManyField(through='leagues.Sponsorship', to='leagues.Sponsor')),
            ],
        ),
        migrations.AddField(
            model_name='sponsorship',
            name='tournament',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Tournament'),
        ),
        migrations.AddField(
            model_name='player',
            name='teams',
            field=models.ManyToManyField(to='leagues.Team', verbose_name='Team memberships'),
        ),
        migrations.AddField(
            model_name='player',
            name='user',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='match',
            name='team_1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matches_a', to='leagues.Team', verbose_name='first participating team'),
        ),
        migrations.AddField(
            model_name='match',
            name='team_2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matches_b', to='leagues.Team', verbose_name='second participating team'),
        ),
        migrations.AddField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='leagues.Tournament', verbose_name='related tournament'),
        ),
        migrations.AddField(
            model_name='match',
            name='winner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matches_won', to='leagues.Team', verbose_name='winning team'),
        ),
        migrations.AddField(
            model_name='game',
            name='game_modes',
            field=models.ManyToManyField(blank=True, to='leagues.GameMode', verbose_name='available game modes'),
        ),
        migrations.AddField(
            model_name='game',
            name='genre',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leagues.Genre', verbose_name='genre of the game'),
        ),
        migrations.AddField(
            model_name='death',
            name='killer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='kills', to='leagues.Player', verbose_name='Killer'),
        ),
        migrations.AddField(
            model_name='death',
            name='match',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Match', verbose_name='Related match'),
        ),
        migrations.AddField(
            model_name='death',
            name='victim',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='deaths', to='leagues.Player', verbose_name='Killed player'),
        ),
        migrations.AddField(
            model_name='clan',
            name='games',
            field=models.ManyToManyField(to='leagues.Game', verbose_name='Games focused by the clan'),
        ),
        migrations.AddField(
            model_name='clan',
            name='leader',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leagues.Player', verbose_name='Leader of the clan'),
        ),
        migrations.AddField(
            model_name='assist',
            name='death',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Death', verbose_name='Related death'),
        ),
        migrations.AddField(
            model_name='assist',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leagues.Player', verbose_name='Assisting player'),
        ),
    ]
