# Generated by Django 2.1.1 on 2018-11-15 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0014_auto_20181115_1000'),
    ]

    operations = [
        migrations.AddField(
            model_name='playedmatch',
            name='clan',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.PROTECT, to='leagues.Clan'),
            preserve_default=False,
        ),
    ]
