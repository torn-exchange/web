
from typing import TypedDict
from django.shortcuts import render
from .models import Profile, ItemTrade, TradeReceipt
import pandas as pd
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count


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


"""Return profile stats
Returns all data needed for tables and charts on Analytics pages

Parameters:
- profile(Profile): user model of the logged in user
"""
def return_profile_stats(profile: Profile):
    trades = ItemTrade.objects.filter(owner=profile).all()
    receipts = TradeReceipt.objects.filter(owner=profile).all().order_by('-created_at')

    total_ranking = [a.name for a in Profile.objects.order_by('-vote_score')]
    your_rank = total_ranking.index(profile.name)+1
    out_of = len(total_ranking)
    hit_counts = profile.hit_count.hits
    has_data = has_data_func(profile)

    if has_data:
        total_profit = sum([obj.profit for obj in trades])
        total_quantity = sum([obj.quantity for obj in trades])
        average_profit = round(total_profit/len(receipts))

        data_trades_dict = [
        {
            'seller': a.seller,
            'created_at': pd.to_datetime(a.last_updated).strftime('%Y-%m-%d'),
            'price': a.price,
            'profit': a.profit,
            'quantity': a.quantity
        } for a in trades]

        data_receipts_dict = [
        {
            'seller': a.seller,
            'created_at': pd.to_datetime(a.created_at).strftime('%Y-%m-%d'),
            'tmp': 42,
            'last_traded': pd.to_datetime(a.created_at).strftime('%Y-%m-%d')
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

        def get_total_profit(name):
            return (df_data_trades[df_data_trades['seller'] == name]['profit'].sum())

        top_profits = {name: get_total_profit(name) for name in all_sellers.keys()}

        data_graph_2(df_data_trades)

        number_of_sellers = len(df_data_receipts['seller'].unique())
    else:
        total_profit = 0
        average_profit = 0
        count_last_week = 0
        last_week_days = []
        last_week_profits = []
        all_sellers = []
        top_profits = []
        number_of_sellers = 0
        total_quantity = 0
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
        'number_of_trades': len(receipts),
        'number_of_sellers': number_of_sellers,
        'number_of_items_bought': total_quantity,
        'your_rank': your_rank,
        'out_of': out_of,
        'data_graph_1': data_graph_1(df_data_receipts),
        'data_graph_2': data_graph_2(df_data_trades)
    }

    return context


def has_data_func(profile):
    if (TradeReceipt.objects.filter(owner=profile).count() == 0) or (ItemTrade.objects.filter(owner=profile).count() == 0):
        return False
    else:
        return True
