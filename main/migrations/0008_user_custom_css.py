# Generated by Django 5.1.4 on 2024-12-28 20:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0007_remove_user_home_page_user_home"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="custom_css",
            field=models.TextField(blank=True, null=True),
        ),
    ]
