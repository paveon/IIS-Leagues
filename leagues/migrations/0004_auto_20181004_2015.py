# Generated by Django 2.1.1 on 2018-10-04 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leagues', '0003_auto_20181004_1328'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='active',
            field=models.BooleanField(default=True, verbose_name='active'),
        ),
    ]
