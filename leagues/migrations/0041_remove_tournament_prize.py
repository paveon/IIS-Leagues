# Generated by Django 2.1.1 on 2018-11-27 21:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0040_auto_20181127_1434'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tournament',
            name='prize',
        ),
    ]
