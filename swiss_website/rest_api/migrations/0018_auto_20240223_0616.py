# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2024-02-23 06:16
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rest_api', '0017_auto_20240223_0553'),
    ]

    operations = [
        migrations.RunSQL('CREATE INDEX rest_api_bet_id_idx ON rest_api_bet (id, auction_id, auction_end_date DESC);'),
        migrations.RunSQL('CREATE INDEX rest_api_bet_auction_id_idx ON rest_api_bet (auction_id, price DESC);'),
        migrations.RunSQL('CREATE INDEX rest_api_bet_user_id_idx ON rest_api_bet (user_id);'),
        migrations.RunSQL('CREATE INDEX rest_api_bet_user_priv_id_idx ON rest_api_bet (user_priv_id);'),
        migrations.RunSQL('CREATE INDEX rest_api_bet_auction_end_date_idx ON rest_api_bet (auction_end_date);'),
        migrations.RunSQL('CREATE INDEX rest_api_bet_color_idx ON rest_api_bet (color);'),
    ]
