# Generated by Django 5.2 on 2025-06-11 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0006_memberjoinrequest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cumulativepoints',
            name='CurrentBalance',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='cumulativepoints',
            name='LifetimeEarnedPoints',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='cumulativepoints',
            name='LifetimeRedeemedPoints',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='cumulativepoints',
            name='TotalPurchaseAmount',
            field=models.FloatField(),
        ),
    ]
