# Generated by Django 5.2.3 on 2025-06-24 22:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0024_alter_user_custom_domain"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="contact",
        ),
    ]
