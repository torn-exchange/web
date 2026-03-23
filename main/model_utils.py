from django.db.models import QuerySet, Count
from main.models import ChangeLog
from users.models import Profile
from django.utils import timezone
from datetime import timedelta
from .models import TradeReceipt
from typing import Tuple

def get_all_time_leaderboard() -> QuerySet:
    return Profile.objects.order_by('-vote_score')[:50]

def get_top_active_traders() -> QuerySet:
    return Profile.objects.filter(active_trader=True).order_by('-vote_score')[:30]

def get_active_traders_count() -> int:
    return Profile.objects.filter(active_trader=True).count()

def get_most_trades() -> QuerySet:
    one_month_ago = timezone.now() - timedelta(days=30)
    counts = TradeReceipt.objects.filter(
        created_at__gte=one_month_ago
    ).values('owner_id').annotate(
        id_count=Count('owner_id')
        ).order_by('-id_count')[:100]
    
    most_receipts = []
    for item in counts:
        user = Profile.objects.get(id=item['owner_id'])
        most_receipts.append({
            "trader_name": user.name,
            "trade_count": min_of_two(item['id_count'], user.monthly_trades),
            "te_receipts": item['id_count'],
            "torn_trades": user.monthly_trades,
        })
        
    # we took top 100 traders by number of receipts, but we want to show only top 30, 
    # so we need to sort them by the minimum of number of receipts and number of trades 
    # in the last month, because some traders can have a lot of receipts but not many trades
    most_receipts.sort(key=lambda x: x['trade_count'], reverse=True)
    most_receipts = most_receipts[:30]
    return most_receipts

def get_changelog() -> Tuple[str, str, str]:
    created_today = Profile.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=30)).count()
    changes_this_week = ChangeLog.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=365)).order_by('-created_at')
    changes_this_month = ChangeLog.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=30)).order_by('-created_at')
    
    return created_today, changes_this_week, changes_this_month

def min_of_two(a, b):
    if a is None and b is None:
        return 0
    if a is None:
        return b
    if b is None:
        return a
    return a if a < b else b
