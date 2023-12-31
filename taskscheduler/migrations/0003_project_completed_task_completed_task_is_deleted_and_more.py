# Generated by Django 4.1 on 2023-07-15 17:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("taskscheduler", "0002_project_created_date_project_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="completed",
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="completed",
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="is_deleted",
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="man_days",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
