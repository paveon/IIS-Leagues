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
    prize = models.PositiveIntegerField('tournament prize', null=True, blank=True,
                                        help_text='prize pool in dollars')
    opening_date = models.DateField('date of the tournament start', default=datetime.date.today)
    end_date = models.DateField('date of the tournament end', default=end_date_default)
    sponsors = models.ManyToManyField(Sponsor, through='Sponsorship', blank=True)
    description = models.TextField('description', blank=True, help_text="Description of tournament")

    def __str__(self):
        return self.name


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
                               verbose_name="Leader of the clan")
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
    leader = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="Leader of the team")
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Game focused by the team')
    clan = models.ForeignKey(Clan, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Related clan')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Team, self).save(*args, **kwargs)


class Match(models.Model):
    beginning = models.DateTimeField('beginning of the match', default=timezone.now)
    duration = models.DurationField('duration of the match')
    game = models.ForeignKey(Game, on_delete=models.PROTECT, verbose_name='related game')
    game_mode = models.ForeignKey(GameMode, on_delete=models.PROTECT, verbose_name='game mode of the match')
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT, null=True, blank=True,
                                   verbose_name='related tournament')
    team_1 = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_a',
                               verbose_name='first participating team')
    team_2 = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_b',
                               verbose_name='second participating team')
    winner = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='matches_won', verbose_name='winning team')

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
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    country = CountryField('country of birth', blank=True)
    birth_date = models.DateField('date of birth', null=True, blank=True)
    image_url = models.URLField('profile image url', max_length=500, blank=True)
    description = models.TextField('description', blank=True, help_text="Description of player")
    equipment = models.ManyToManyField(Equipment, verbose_name='Equipment used by player')
    games = models.ManyToManyField(Game, verbose_name='Games focused by the player')
    teams = models.ManyToManyField(Team, verbose_name='Team memberships')
    clans = models.ManyToManyField(Clan, verbose_name='Clan memberships')
    matches = models.ManyToManyField(Match, verbose_name='Played matches')

    @property
    def full_name(self):
        return "%s %s".format(self.first_name, self.last_name)

    def __str__(self):
        return self.nickname

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nickname)
        super(Player, self).save(*args, **kwargs)


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