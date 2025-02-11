
from .models import Profile, ItemTrade, TradeReceipt
from django.db.models import Sum, Count, F, ExpressionWrapper, IntegerField, Max
from django.db.models.functions import TruncDate


def data_graph_1(receipts_queryset):
    """Returns all-time daily trade count"""
    try:
        summary = (receipts_queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date'))
        
        return [{'x': item['date'].strftime('%Y-%m-%d'), 
                'y': item['count']} for item in summary]
    except Exception as e:
        print(f"Error in data_graph_1: {e}")
        return []

def data_graph_2(trades_queryset):
    """Returns all-time daily profits"""
    try:
        summary = (trades_queryset
            .annotate(date=TruncDate('last_updated'))
            .values('date')
            .annotate(
                daily_profit=Sum(
                    ExpressionWrapper(
                        (F('TE_value_at_save') * F('quantity')) - 
                        (F('price') * F('quantity')),
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('date'))
        
        return [{'x': item['date'].strftime('%Y-%m-%d'), 
                'y': item['daily_profit'] or 0} for item in summary]
    except Exception as e:
        print(f"Error in data_graph_2: {e}")
        return []


"""Return profile stats
Returns all data needed for tables and charts on Analytics pages

Parameters:
- profile(Profile): user model of the logged in user
"""
def return_profile_stats(profile: Profile):
    # Get all trades and receipts for graphs (no limit)
    all_trades = (ItemTrade.objects
        .filter(owner=profile))
    
    all_receipts = (TradeReceipt.objects
        .filter(owner=profile))
    
    # Get trades summary data
    trades_data = all_trades.aggregate(
        total_profit=Sum(
            ExpressionWrapper(
                (F('TE_value_at_save') * F('quantity')) - 
                (F('price') * F('quantity')),
                output_field=IntegerField()
            )
        ),
        total_quantity=Sum('quantity')
    )
    
    # Get receipts with related data
    receipts = (TradeReceipt.objects
        .filter(owner=profile)
        .select_related('owner')  # Eager load owner
        .prefetch_related('items_trades')
        .order_by('-created_at')
        .annotate(
            trade_date=TruncDate('created_at')
        ))
    
    # Get ranking data efficiently
    ranking_position = (Profile.objects
        .filter(vote_score__gt=profile.vote_score)
        .count() + 1)
    total_profiles = Profile.objects.count()
    
    has_data = bool(receipts.exists() and trades_data['total_profit'])
    
    if has_data:
        # Process trades data
        total_profit = trades_data['total_profit'] or 0
        total_quantity = trades_data['total_quantity'] or 0
        average_profit = round(total_profit / receipts.count()) if receipts else 0
        
        # Get seller statistics in a single query
        seller_stats = (TradeReceipt.objects
            .filter(owner=profile)
            .prefetch_related('items_trades')
            .values('seller')
            .annotate(
                trade_count=Count('id'),
                last_traded=Max('created_at'),
                total_profit=Sum(
                    ExpressionWrapper(
                        (F('items_trades__TE_value_at_save') * F('items_trades__quantity')) - 
                        (F('items_trades__price') * F('items_trades__quantity')),
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('-trade_count'))
        
        # Convert to required format
        all_sellers = {
            item['seller']: {
                'trade_count': item['trade_count'],
                'last_traded': item['last_traded'].strftime('%Y-%m-%d'),
            }
            for item in seller_stats
        }
        
        top_profits = {
            item['seller']: item['total_profit']
            for item in seller_stats
        }
        
        number_of_sellers = len(all_sellers)
        
    else:
        total_profit = average_profit = total_quantity = number_of_sellers = 0
        all_sellers = top_profits = {}
    
    context = {
        'page_title': 'Analytics - Torn Exchange',
        'has_data': has_data,
        'profile': profile,
        'total_profit': total_profit,
        'average_profit': average_profit,
        'receipts': receipts,
        'hits': profile.hit_count.hits,
        'sellers': all_sellers,
        'top_profits': top_profits,
        'number_of_trades': receipts.count(),
        'number_of_sellers': number_of_sellers,
        'number_of_items_bought': total_quantity,
        'your_rank': ranking_position,
        'out_of': total_profiles,
    }
    
    if has_data:
        # Add graph data only if we have data
        context.update({
            'data_graph_1': data_graph_1(all_receipts),  # Use unlimited queryset
            'data_graph_2': data_graph_2(all_trades)     # Use trades queryset, not summary dict
        })
    
    return context


def has_data_func(profile):
    if (TradeReceipt.objects.filter(owner=profile).count() == 0) or (ItemTrade.objects.filter(owner=profile).count() == 0):
        return False
    else:
        return True
