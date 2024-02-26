import re
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from rest_api.models import Auction, AuctionPhoto

from django.conf import settings
from rest_api.models import Auction, Bet, UserPrivate
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
import json


class Command(BaseCommand):
    help = 'Fix bets table'

    def handle(self, *args, **options):
        bets = Bet.objects.all().select_related('auction')
        for bet in bets:
            if not bet.user:
                print(bet.id, ":no user")
                continue
            try:
                user = UserPrivate.objects.get(user=bet.user)
            except UserPrivate.DoesNotExist as e:
                print(bet.id, ":invalid user")
                continue
            print(bet.id, ":find user: ", bet.auction.end_date)
            bet.user_priv = user
            bet.auction_end_date = bet.auction.end_date
            bet.save()
