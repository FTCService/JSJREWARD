# Generated by Django 5.2 on 2025-05-31 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('survey', '0004_alter_surveysubmission_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='surveysubmission',
            name='questions',
            field=models.JSONField(default=dict),
        ),
        migrations.DeleteModel(
            name='SurveyAnswer',
        ),
    ]
