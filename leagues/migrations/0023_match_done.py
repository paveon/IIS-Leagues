# Generated by Django 2.1.1 on 2018-11-18 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0022_auto_20181118_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='done',
            field=models.BooleanField(default=False, verbose_name='team making completed'),
        ),
    ]
