from django.db.models import QuerySet, Count
from main.models import ChangeLog
from users.models import Profile
from django.utils import timezone
from datetime import timedelta
from .models import TradeReceipt
from typing import Tuple

def get_all_time_leaderboard() -> QuerySet:
    return Profile.objects.order_by('-vote_score')[:50]

def get_active_traders() -> QuerySet:
    return Profile.objects.filter(active_trader=True).order_by('-vote_score')[:30]

def get_most_trades() -> QuerySet:
    one_month_ago = timezone.now() - timedelta(days=30)
    counts = TradeReceipt.objects.filter(
        created_at__gte=one_month_ago
    ).values('owner_id').annotate(
        id_count=Count('owner_id')
        ).order_by('-id_count')[:30]
    
    most_receipts = []
    for item in counts:
        user = Profile.objects.get(id=item['owner_id'])
        most_receipts.append({
            "trader_name": user.name,
            "trade_count": item['id_count'],
        })
        
    return most_receipts

def get_changelog() -> Tuple[str, str, str]:
    created_today = Profile.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=30)).count()
    changes_this_week = ChangeLog.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=365)).order_by('-created_at')
    changes_this_month = ChangeLog.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=30)).order_by('-created_at')
    
    return created_today, changes_this_week, changes_this_month
