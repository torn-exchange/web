
from .models import Profile, ItemTrade, TradeReceipt
import json
import pandas as pd
from datetime import timedelta
from django.utils import timezone


def data_graph_1(df_data_receipts):
    try:
        summary = df_data_receipts.groupby("created_at").count()
        data = [{
            'x': item.name,
            'y': item.seller} for i, item in summary.iterrows()]
        return data
    except:
        return []


def data_graph_2(df_data_trades):
    try:
        summary = df_data_trades.groupby("created_at").sum()
        data = [{
            'x': item.name,
            'y': item.profit} for i, item in summary.iterrows()]
        return data
    except:
        return []


def return_profile_stats(profile):
    trades = ItemTrade.objects.filter(owner=profile).all()
    receipts = TradeReceipt.objects.filter(
        owner=profile).all().order_by('-created_at')

    total_ranking = [a.name for a in Profile.objects.order_by('-vote_score')]
    your_rank = total_ranking.index(profile.name)+1
    out_of = len(total_ranking)
    hit_counts = profile.hit_count.hits
    has_data = has_data_func(profile)

    if has_data:

        total_profit = sum([obj.profit for obj in trades])
        total_quantity = sum([obj.quantity for obj in trades])
        average_profit = round(total_profit/len(receipts))
        last_week_trades = ItemTrade.objects.filter(
            owner=profile, last_updated__gte=timezone.now()-timedelta(days=7))
        last_week_receipts = TradeReceipt.objects.filter(
            owner=profile, created_at__gte=timezone.now()-timedelta(days=7))

        data_trades_last_week_dict = [{
            'created_at': pd.to_datetime(a.last_updated).strftime('%Y-%m-%d'),
            'price': a.price,
            'profit': a.profit,
            'quantity': a.quantity} for a in trades]

        data_receipts_last_week_dict = [{
            'seller': a.seller,
            'created_at': pd.to_datetime(a.created_at).strftime('%Y-%m-%d'),
            'tmp': 42
        } for a in receipts]

        df_data_trades_last_week = pd.DataFrame(data_trades_last_week_dict)
        df_data_receipts_last_week = pd.DataFrame(data_receipts_last_week_dict)

        data_trades_dict = [{
            'seller': a.seller,
            'created_at': pd.to_datetime(a.last_updated).strftime('%Y-%m-%d'),
            'price': a.price,
            'profit': a.profit,
            'quantity': a.quantity} for a in trades]

        data_receipts_dict = [{
            'seller': a.seller,
            'created_at': pd.to_datetime(a.created_at).strftime('%Y-%m-%d'),
            'tmp': 42} for a in receipts]

        df_data_receipts = pd.DataFrame(data_receipts_dict)
        df_data_trades = pd.DataFrame(data_trades_dict)

        top_sellers = df_data_receipts.groupby('seller').count(
        )['tmp'].sort_values(ascending=False).to_dict()

        def get_total_profit(name):
            return (df_data_trades[df_data_trades['seller'] == name]['profit'].sum())

        top_profits = {name: get_total_profit(
            name) for name in top_sellers.keys()}

        data_graph_2(df_data_trades)
        try:
            last_week_days = df_data_trades_last_week.groupby(
                'created_at').count().index.values.tolist()
        except:
            last_week_days = []
        count_last_week = df_data_receipts_last_week.groupby('created_at').count()[
            'tmp'].values.tolist()

        last_week_profits = df_data_trades_last_week.groupby(
            'created_at').sum()['profit'].values.tolist()

        number_of_sellers = len(df_data_receipts['seller'].unique())
    else:
        total_profit = 0
        average_profit = 0
        count_last_week = 0
        last_week_days = []
        last_week_profits = []
        top_sellers = []
        top_profits = []
        number_of_sellers = 0
        total_quantity = 0
        df_data_receipts = pd.DataFrame()
        df_data_trades = pd.DataFrame()

    context = {
        'has_data': has_data,
        'profile': profile,
        'trades': trades,
        'total_profit': total_profit,
        'average_profit': average_profit,
        'count_last_week': json.dumps(count_last_week),
        'last_week_days': json.dumps(last_week_days),
        'last_week_profits': json.dumps(last_week_profits),
        'receipts': receipts,
        'hits': hit_counts,
        'top_sellers': top_sellers,
        'top_profits': top_profits,
        'number_of_sellers': number_of_sellers,
        'number_of_items_bought': total_quantity,
        'your_rank': your_rank,
        'out_of': out_of,
        'data_graph_1': data_graph_1(df_data_receipts),
        'data_graph_2': data_graph_2(df_data_trades),

    }

    return context


def has_data_func(profile):
    if (TradeReceipt.objects.filter(owner=profile).count() == 0) or (ItemTrade.objects.filter(owner=profile).count() == 0):
        return False
    else:
        return True
