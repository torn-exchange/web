from django.db import migrations


def populate_effective_price(apps, schema_editor):
    Listing = apps.get_model('main', 'Listing')
    for listing in Listing.objects.select_related('owner__settings', 'item').iterator():
        listing.effective_price = _calculate(listing)
        try:
            listing.save(update_fields=['effective_price'])
        except Exception:
            pass


def _calculate(listing):
    import numpy as np

    price = listing.price
    discount = listing.discount

    if discount is None and price is None:
        return None

    if discount is None and price is not None:
        return round(price)

    try:
        global_fee = listing.owner.settings.trade_global_fee or 0
    except Exception:
        global_fee = 0

    # custom items (Sets/Properties): no global fee
    try:
        item_id = listing.item.item_id
    except Exception:
        item_id = 0
    if item_id and item_id > 9000:
        global_fee = 0

    total_discount = (discount or 0) + global_fee
    discount_fraction = (100.0 - total_discount) / 100.0
    discount_price = discount_fraction * round(listing.item.TE_value or 0)

    if price is None:
        return round(discount_price or 0)

    return round(np.nan_to_num(np.nanmin([discount_price, price])))


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0049_populate_effective_price'),
    ]

    operations = [
        migrations.RunPython(populate_effective_price, migrations.RunPython.noop),
    ]
