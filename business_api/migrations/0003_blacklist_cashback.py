# Generated by Django 5.0 on 2024-05-10 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_api', '0002_mtntransaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='Blacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='CashBack',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=200)),
                ('user_number', models.CharField(max_length=200)),
                ('amount', models.FloatField(default=0)),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
