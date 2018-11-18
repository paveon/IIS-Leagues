import datetime
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.template.defaultfilters import slugify
from django_countries.fields import CountryField
import re


def strip_spaces(string):
    return re.sub(r'\s+', ' ', string)


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Name of the genre of a game")
    slug = models.SlugField(max_length=100, unique=True)
    acronym = models.CharField(max_length=10, blank=True, help_text="Game genre acronym")
    description = models.TextField('description', blank=True, help_text="Description of genre")

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        self.name = strip_spaces(self.name)
        super(Genre, self).save(*args, **kwargs)

    def __str__(self):
        return self.acronym if self.acronym else self.name


class GameMode(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Name of the game mode")
    team_player_count = models.PositiveSmallIntegerField(default=5, null=True, blank=True,
                                                         help_text="Number of players in one team")
    description = models.TextField('description', blank=True, help_text="Description of game mode")

    def __str__(self):
        return self.name


class Game(models.Model):
    name = models.CharField('name of the game', max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name='genre of the game')
    release_date = models.DateField('release date of the game', null=True, blank=True)
    image_url = models.URLField('game image url', max_length=500, blank=True)
    publisher = models.CharField('game publisher', max_length=200, blank=True)
    description = models.TextField('description', blank=True, help_text="Description of game")
    game_modes = models.ManyToManyField(GameMode, blank=True, verbose_name='available game modes')

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        self.name = strip_spaces(self.name)
        super(Game, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Sponsor(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


def end_date_default():
        end_date = datetime.date.today() + datetime.timedelta(days=7)
        return end_date


class Tournament(models.Model):
    name = models.CharField('tournament name', max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    prize = models.PositiveIntegerField('tournament prize', null=True, blank=True,
                                        help_text='prize pool in dollars')
    opening_date = models.DateField('date of the tournament start', default=datetime.date.today)
    end_date = models.DateField('date of the tournament end', default=end_date_default)
    sponsors = models.ManyToManyField(Sponsor, through='Sponsorship', blank=True)
    description = models.TextField('description', blank=True, help_text="Description of tournament")
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    game_mode = models.ForeignKey(GameMode, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Tournament, self).save(*args, **kwargs)


class Sponsorship(models.Model):
    SPONSORSHIP_TYPES = (
        ('MAIN', 'Main'),
        ('SIDE', 'Side'),
    )
    sponsor = models.ForeignKey(Sponsor, on_delete=models.PROTECT)
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT)
    type = models.CharField('sponsorship type', max_length=4, choices=SPONSORSHIP_TYPES, default=SPONSORSHIP_TYPES[0])
    amount = models.PositiveIntegerField('donation amount', null=True, blank=True)

    class Meta:
        unique_together = ('sponsor', 'tournament')


class Clan(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    founded = models.DateField('foundation date', default=datetime.date.today)
    country = CountryField('country of origin', blank=True)
    description = models.TextField('description', blank=True, help_text="Description of clan")
    leader = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="Leader of the clan", related_name="clan_leader")
    games = models.ManyToManyField(Game, verbose_name='Games focused by the clan')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Clan, self).save(*args, **kwargs)


class Team(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    founded = models.DateField('foundation date', default=datetime.date.today)
    description = models.TextField('description', blank=True, help_text="Description of team")
    active = models.BooleanField('active', default=True)
    tournaments = models.ManyToManyField(Tournament, through='RegisteredTeams', verbose_name='Registered tournaments')
    leader = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="Leader of the team")
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Game focused by the team')
    clan = models.ForeignKey(Clan, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Related clan')

    @property
    def all_matches(self):
        return self.matches_a.all().union(self.matches_b.all())

    @property
    def win_ratio(self):
        matches_total = self.all_matches.count()
        if not matches_total:
            return None

        matches_won = self.matches_won.count()
        return (str(round((matches_won / matches_total) * 100, 2)) + " %")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        if not self.leader and self.active:
            self.active = False
        super(Team, self).save(*args, **kwargs)


class Match(models.Model):
    beginning = models.DateTimeField('beginning of the match', default=timezone.now)
    duration = models.DurationField('duration of the match', null=True, blank=True,)
    game = models.ForeignKey(Game, on_delete=models.PROTECT, verbose_name='related game', null=True, blank=True,)
    game_mode = models.ForeignKey(GameMode, on_delete=models.PROTECT, verbose_name='game mode of the match', null=True, blank=True,)
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT, null=True, blank=True,
                                   verbose_name='related tournament')
    team_1 = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_a',
                               verbose_name='first participating team', null=True, blank=True,)
    team_2 = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_b',
                               verbose_name='second participating team', null=True, blank=True,)
    winner = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_won', verbose_name='winning team', null=True, blank=True,)
    done = models.BooleanField(verbose_name='team making completed', default=False)

    @property
    def duration_fmt(self):
        beginning = self.beginning
        seconds = int(self.duration.total_seconds())
        minutes = seconds // 60
        seconds = seconds % 60
        return '{0}m {1}s'.format(minutes, seconds)

    def __str__(self):
        return "Match ({0}): {1} vs {2}".format(self.id, self.team_1, self.team_2)


class Equipment(models.Model):
    EQUIPMENT_TYPES = (
        ('KEYBOARD', 'Keyboard'),
        ('MOUSE', 'Mouse'),
        ('MONITOR', 'Monitor'),
        ('MOUSE_PAD', 'Mouse pad'),
        ('HEADSET', 'Headset'),
    )
    name = models.CharField(max_length=200, unique=True)
    type = models.CharField('Kind of equipment', max_length=20, choices=EQUIPMENT_TYPES)
    manufacturer = models.CharField('Equipment manufacturer', max_length=200, blank=True)
    brand = models.CharField('Brand of equipment', max_length=200, blank=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    nickname = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    country = CountryField('country of birth', blank=True)
    birth_date = models.DateField('date of birth')
    image_url = models.URLField('profile image url', max_length=500, blank=True)
    description = models.TextField('description', blank=True, help_text="Description of player")
    equipment = models.ManyToManyField(Equipment, verbose_name='Equipment used by player')
    games = models.ManyToManyField(Game, verbose_name='Games focused by the player')
    teams = models.ManyToManyField(Team, verbose_name='Team memberships', related_name='team_members')
    clan = models.ForeignKey(Clan, on_delete=models.PROTECT, verbose_name='Clan membership',
                             related_name='clan_members', null=True, blank=True,)
    team_pendings = models.ManyToManyField(Team, related_name='team_pendings')
    clan_pendings = models.ManyToManyField(Clan, related_name='clan_pendings')
    matches = models.ManyToManyField(Match, through='PlayedMatch', verbose_name='Played matches')

    @property
    def win_ratio(self):
        games_total = self.matches.count()
        if not games_total:
            return None
        games_won = self.matches.filter(playedmatch__team=models.F('playedmatch__match_winner')).count()
        return str(round((games_won / games_total) * 100, 2)) + " %"

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)

    @property
    def age(self):
        born = self.birth_date
        if born:
            today = datetime.date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return None

    def __str__(self):
        return self.nickname

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nickname)
        super(Player, self).save(*args, **kwargs)


class PlayedMatch(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    match = models.ForeignKey(Match, on_delete=models.PROTECT)
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    clan = models.ForeignKey(Clan, on_delete=models.PROTECT)
    # game_won = models.BooleanField('game won')

    @property
    def game_won(self):
        return self.match.winner.id == self.team.id

    class Meta:
        unique_together = ('player', 'match')


class RegisteredTeams(models.Model):
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT)


class Death(models.Model):
    match = models.ForeignKey(Match, on_delete=models.PROTECT, verbose_name='Related match')
    match_time = models.TimeField(default=timezone.now)
    victim = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='deaths', verbose_name='Killed player')
    killer = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='kills', null=True, blank=True,
                               verbose_name='Killer')


class Assist(models.Model):
    ASSISTANCE_TYPE = (
        ('HEALING', 'Damage'),
        ('DAMAGE', 'Healing'),
    )
    death = models.ForeignKey(Death, on_delete=models.PROTECT, verbose_name='Related death')
    player = models.ForeignKey(Player, on_delete=models.PROTECT, verbose_name='Assisting player')
    type = models.CharField('Type of assistance', max_length=20, choices=ASSISTANCE_TYPE)