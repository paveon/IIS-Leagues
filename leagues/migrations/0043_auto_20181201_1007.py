# Generated by Django 2.1.1 on 2018-12-01 10:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0042_auto_20181128_1050'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='player',
            name='equipment',
        ),
        migrations.DeleteModel(
            name='Equipment',
        ),
    ]