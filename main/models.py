from django.db import models
from users.models import Profile
import numpy as np
from django.utils.crypto import get_random_string


def generate_url_string():
    # while True:
    string = get_random_string(10)
    #    if not TradeReceipt.objects.filter(receipt_url_string=string).exists():
    return string


class ChangeLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.description


class Company(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    company_id = models.IntegerField()

    company_type = models.CharField(max_length=250)
    rating = models.IntegerField()
    days_old = models.IntegerField()
    weekly_income = models.BigIntegerField()
    weekly_customers = models.BigIntegerField()
    employees_hired = models.IntegerField()
    employees_capacity = models.IntegerField()
    popularity = models.IntegerField()
    efficiency = models.IntegerField()
    average_employee_tenure = models.IntegerField()
    average_employee_efficiency = models.IntegerField()

    company_looking_to_hire_message = models.CharField(
        max_length=140, null=True, blank=True)
    negotiable = models.BooleanField(default=True)
    asking_price = models.BigIntegerField()
    description = models.CharField(max_length=140, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.owner.name}"


class Item(models.Model):
    name = models.CharField(max_length=250, )
    description = models.TextField()
    requirement = models.TextField()
    item_type = models.CharField(max_length=250)
    weapon_type = models.CharField(max_length=250, null=True)
    buy_price = models.BigIntegerField()
    sell_price = models.BigIntegerField()
    market_value = models.BigIntegerField()
    circulation = models.BigIntegerField()
    image_url = models.CharField(max_length=250)
    last_updated = models.DateTimeField(auto_now=True)
    TE_value = models.BigIntegerField(null=True)
    item_id = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        for listing in Listing.objects.filter(item=self):
            listing.save()
            # print('saving listings')
        super().save(*args, **kwargs)


class Listing(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    price = models.BigIntegerField(null=True)
    last_updated = models.DateTimeField(auto_now=True)
    discount = models.FloatField(null=True)

    @property
    def effective_price(self):
        if (self.discount is None) and (self.price is None):
            #print('ITEM DELETED BY CONMDITION ON SAVE METHOD OF LISTING')
            #print(f"""
                #Item name {self.item.name}, value: {self.item.TE_value}, set price: {self.price}, discount: {self.discount}, Effective Price:{self.effective_price} 
                #""")
            #self.delete()
            return None

        if (self.discount is None) and (self.price is not None):
            effective_price = round(self.price)

        if (self.discount is not None) and (self.price is None):
            discount_fraction = (100.0-(self.discount))/100.0
            discount_price = discount_fraction*round(self.item.TE_value or 0)
            effective_price = round(discount_price or 0)

        if (self.discount is not None) and (self.price is not None):
            discount_fraction = (100.0-(self.discount))/100.0
            discount_price = discount_fraction*round(self.item.TE_value or 0)
            effective_price = round(np.nan_to_num(
                np.nanmin([discount_price, self.price])))
        return effective_price

    class Meta:
        unique_together = (("owner", "item"),)

    def __str__(self):
        return f"{self.item} - ${self.effective_price}"
      # Call the "real" save() method.

    @property
    def profit_per_item(self):
        profit = (self.item.TE_value)-(self.effective_price)
        # print(profit)
        return profit


class ItemTrade(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE)
    seller = models.CharField(null=True, max_length=600)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    price = models.BigIntegerField(null=False)
    quantity = models.IntegerField(null=False)
    last_updated = models.DateTimeField(auto_now=True)
    TE_value_at_save = models.BigIntegerField(null=False)

    def save(self, *args, **kwargs):
        self.TE_value_at_save = self.item.TE_value

        super().save(*args, **kwargs)  # Call the "real" save() method.

    def __str__(self):
        return f"{self.owner}- {self.item} x {self.quantity} - {self.seller} - ${self.price}"

    def is_valid(self):
        if (self.seller is None):
            return 'Make sure to include the name of the person you\'re trading with in the trade paste'
        if (self.owner is None):
            return 'Receipt must have an owner'
        if (self.price < 0):
            return f'{self.item} must have a valid price'
        if (self.quantity <= 0):
            return f'{self.item} must have a valid quantity'
        else:
            return 'valid'

    @property
    def sub_total(self):
        return self.price * self.quantity

    @property
    def profit(self):
        profit = (self.TE_value_at_save*self.quantity) - \
            (self.price * self.quantity)
        # print(profit)
        return profit


class TradeReceipt(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE)
    seller = models.CharField(null=True, max_length=250)
    items_trades = models.ManyToManyField(ItemTrade)
    created_at = models.DateTimeField(auto_now_add=True)
    receipt_url_string = models.CharField(
        max_length=10, null=False, default=generate_url_string, unique=True)

    def __str__(self):
        return f"{self.owner}- {self.seller} - ${self.total}"

    @property
    def total(self):
        return sum([a.sub_total for a in self.items_trades.all()])

    @property
    def profit(self):
        return sum([a.profit for a in self.items_trades.all()])
