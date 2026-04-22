
from .models import Profile, ItemTrade, TradeReceipt
import pandas as pd
from django.db.models import Sum, F, ExpressionWrapper, BigIntegerField


def data_graph_1(df_data_receipts):
    try:
        summary = (df_data_receipts.groupby("created_at")['seller']
                   .count()
                   .reset_index()
                   .rename(columns={'created_at': 'x', 'seller': 'y'}))
        return summary.to_dict('records')
    except:
        return []


def data_graph_2(df_data_trades):
    try:
        summary = (df_data_trades.groupby("created_at")['profit']
                   .sum()
                   .reset_index()
                   .rename(columns={'created_at': 'x', 'profit': 'y'}))
        return summary.to_dict('records')
    except:
        return []


"""Return profile stats
Returns all data needed for tables and charts on Analytics pages

Parameters:
- profile(Profile): user model of the logged in user
"""
def return_profile_stats(profile: Profile):
    trades = ItemTrade.objects.filter(owner=profile).all()
    receipts = TradeReceipt.objects.filter(owner=profile).order_by('-created_at')

    your_rank = Profile.objects.filter(vote_score__gt=profile.vote_score).count() + 1
    out_of = Profile.objects.count()
    hit_counts = profile.hit_count.hits
    has_data = trades.exists() and receipts.exists()

    if has_data:
        profit_expr = ExpressionWrapper(
            (F('TE_value_at_save') - F('price')) * F('quantity'),
            output_field=BigIntegerField()
        )
        agg = trades.aggregate(
            total_profit=Sum(profit_expr),
            total_quantity=Sum('quantity')
        )
        total_profit = agg['total_profit'] or 0
        total_quantity = agg['total_quantity'] or 0
        receipt_count = receipts.count()
        average_profit = round(total_profit / receipt_count) if receipt_count else 0

        data_trades_dict = [
        {
            'seller': a.seller,
            'created_at': a.last_updated.strftime('%Y-%m-%d'),
            'price': a.price,
            'profit': a.profit,
            'quantity': a.quantity
        } for a in trades]

        data_receipts_dict = [
        {
            'seller': a.seller,
            'created_at': a.created_at.strftime('%Y-%m-%d'),
            'tmp': 42,
            'last_traded': a.created_at.strftime('%Y-%m-%d')
        } for a in receipts]

        df_data_receipts = pd.DataFrame(data_receipts_dict)
        df_data_trades = pd.DataFrame(data_trades_dict)
        
        # create trade_count and last_traded columns
        all_sellers = (
            df_data_receipts.groupby('seller')
            .agg(
                trade_count=('tmp', 'count'),  # Count of trades for each seller
                last_traded=('last_traded', 'max')  # The latest trade date for each seller
            )
            .sort_values(by='trade_count', ascending=False)  # Sort by number of trades
            .to_dict(orient='index')  # Convert to dict with seller as the key
        )

        top_profits = df_data_trades.groupby('seller')['profit'].sum().to_dict()

        number_of_sellers = len(df_data_receipts['seller'].unique())
    else:
        total_profit = 0
        average_profit = 0
        all_sellers = []
        top_profits = []
        number_of_sellers = 0
        total_quantity = 0
        receipt_count = 0
        df_data_receipts = pd.DataFrame()
        df_data_trades = pd.DataFrame()

    context = {
        'page_title': 'Analytics - Torn Exchange',
        'has_data': has_data,
        'profile': profile,
        'trades': trades,
        'total_profit': total_profit,
        'average_profit': average_profit,
        'receipts': receipts,
        'hits': hit_counts,
        'sellers': all_sellers,
        'top_profits': top_profits,
        'number_of_trades': receipt_count,
        'number_of_sellers': number_of_sellers,
        'number_of_items_bought': total_quantity,
        'your_rank': your_rank,
        'out_of': out_of,
        'data_graph_1': data_graph_1(df_data_receipts),
        'data_graph_2': data_graph_2(df_data_trades)
    }

    return context
