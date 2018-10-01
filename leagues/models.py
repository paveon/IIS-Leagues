import datetime
from django.db import models
from django.utils import timezone
from django.conf import settings


class Genre(models.Model):
    name = models.CharField(max_length=100, primary_key=True, help_text="Name of the genre of a game")
    acronym = models.CharField(max_length=10, blank=True, help_text="Game genre acronym")
    description = models.CharField(max_length=500, blank=True, help_text="Description of genre")

    def __str__(self):
        return "{0} ({1})".format(self.acronym, self.name)


class GameModeType(models.Model):
    name = models.CharField(max_length=100, primary_key=True, help_text="Name of game mode type")

    def __str__(self):
        return self.name


class GameMode(models.Model):
    name = models.CharField(max_length=100, primary_key=True, help_text="Name of the game mode")
    type = models.ForeignKey(GameModeType, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="General type of game mode")
    team_player_count = models.PositiveSmallIntegerField(default=5, null=True, blank=True,
                                                         help_text="Number of players in one team")

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
    game_modes = models.ManyToManyField(GameMode, blank=True, verbose_name='available game modes')

    def save(self, *args, **kwargs):
        self.slug = self.name.replace(" ", "-")
        super(Game, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Sponsor(models.Model):
    name = models.CharField(max_length=200, primary_key=True)

    def __str__(self):
        return self.name


class Tournament(models.Model):
    def end_date_default(self):
        return datetime.date.today() + datetime.timedelta(days=7)

    name = models.CharField('tournament name', max_length=200, primary_key=True)
    prize = models.PositiveIntegerField('tournament prize', null=True, blank=True,
                                        help_text='prize pool in dollars')
    opening_date = models.DateField('date of the tournament start', default=datetime.date.today)
    end_date = models.DateField('date of the tournament end', default=end_date_default)
    sponsors = models.ManyToManyField(Sponsor, through='Sponsorship')

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


class Clan(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    founded = models.DateField('foundation date', default=datetime.date.today)
    country = models.CharField('country of origin', max_length=200, blank=True)
    games = models.ManyToManyField(Game, verbose_name='Games focused by the clan')

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=200, primary_key=True)
    founded = models.DateField('foundation date', default=datetime.date.today)
    active = models.BooleanField('activity status', default=True)
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Game focused by the team')
    clan = models.ForeignKey(Clan, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name='Related clan')

    def __str__(self):
        return self.name


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
    name = models.CharField(max_length=200, primary_key=True)
    type = models.CharField('Kind of equipment', max_length=20, choices=EQUIPMENT_TYPES)
    manufacturer = models.CharField('Equipment manufacturer', max_length=200, blank=True)
    brand = models.CharField('Brand of equipment', max_length=200, blank=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    nickname = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    country = models.CharField('country of birth', max_length=200, blank=True)
    birth_date = models.DateField('date of birth', null=True, blank=True)
    equipment = models.ManyToManyField(Equipment, verbose_name='Equipment used by player')
    games = models.ManyToManyField(Game, verbose_name='Games focused by the player')
    teams = models.ManyToManyField(Team, verbose_name='Team memberships')
    clans = models.ManyToManyField(Clan, verbose_name='Clan memberships')
    matches = models.ManyToManyField(Match, verbose_name='Played matches')

    @property
    def full_name(self):
        return "%s %s".format(self.first_name, self.last_name)

    def __str__(self):
        return "{0} ({1})".format(self.nickname, self.full_name)


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


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.question_text

    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now

    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text

