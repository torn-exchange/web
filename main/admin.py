from django.contrib import admin
from .models import Listing, Item, TradeReceipt, ItemTrade, ChangeLog, Company
# Register your models here.


admin.site.register(Listing)
admin.site.register(Item)
admin.site.register(TradeReceipt)
admin.site.register(ItemTrade)
admin.site.register(Company)
admin.site.register(ChangeLog)