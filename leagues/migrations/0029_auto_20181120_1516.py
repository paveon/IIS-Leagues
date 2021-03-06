# Generated by Django 2.1.1 on 2018-11-20 14:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0028_auto_20181119_2222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assist',
            name='type',
            field=models.CharField(choices=[('HEALING', 'Healing'), ('DAMAGE', 'Damage')], max_length=20, verbose_name='Type of assistance'),
        ),
        migrations.AlterField(
            model_name='gamemode',
            name='team_player_count',
            field=models.PositiveSmallIntegerField(default=5, help_text='Number of players in one team'),
        ),
    ]
