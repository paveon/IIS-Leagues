# Generated by Django 2.1.1 on 2018-10-06 11:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0005_auto_20181005_1005'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='sponsorship',
            unique_together={('sponsor', 'tournament')},
        ),
    ]
