import django_filters

from .models import Listing, Company
from django_filters import CharFilter, TypedChoiceFilter, OrderingFilter, RangeFilter
from django_filters.widgets import RangeWidget

from django.db.models import F, Case, When, Value, FloatField, IntegerField, ExpressionWrapper
from django.db.models.functions import Coalesce, Least, Round


class ListingFilter(django_filters.FilterSet):
    def __init__(self, data, *args, **kwargs):
        data = data.copy()
        data.setdefault('order', '-traders_price')
        super().__init__(data, *args, **kwargs)

    order_by = OrderingFilter(
        label='Sort By', 
        choices=(
            ('-traders_price', 'Price (Highest to Lowest'),
            ('traders_price', 'Price (Lowest to Highest)'),
            ('-owner__vote_score', 'Rating (Highest to Lowest'),
            ('owner__vote_score', 'Rating (Lowest to Highest)'),
        )
    )
    
    @property
    def qs(self):
        # Annotate the queryset with the computed effective_price
        queryset = super().qs.annotate(
            # cannot reuse calculate_effective_price() method here
            # because this is done on DB level so it needs special SQL-Django ORM mojo
            traders_price = ExpressionWrapper(
                Round(
                    Case(
                        # If both discount and price are None, return None
                        When(discount__isnull=True, price__isnull=True, then=Value(None, output_field=IntegerField())),
                        
                        # If discount is None and price is not None, use the price
                        When(discount__isnull=True, then=F('price')),
                        
                        # If price is None and discount is not None, calculate the discount price
                        When(price__isnull=True, then=Round(
                            (100.0 - F('discount')) / 100.0 * Coalesce(Round(F('item__TE_value')), Value(0)),
                            output_field=FloatField()
                        )),
                        
                        # If both discount and price are not None, calculate the minimum of discount price and price
                        default=Round(
                            Least(
                                (100.0 - F('discount')) / 100.0 * Coalesce(Round(F('item__TE_value')), Value(0)),
                                F('price')
                            ),
                            output_field=FloatField()
                        ),
                        output_field=FloatField()
                    )
                ),
                output_field=IntegerField()  # Final output as Integer
            )   
        )
        return queryset
    
    status_choices = (
        ('', 'Any'),
        ('Online', 'Online'),
        ('Idle', 'Idle'),
        ('Offline', 'Offline'),
    )
    model_name_contains = CharFilter(
        label='Item Name', field_name='item__name', lookup_expr='icontains')
    status = TypedChoiceFilter(
        label='Status', field_name='owner__activity_status', choices=status_choices)

    class Meta:
        model = Listing
        fields = [('model_name_contains')]


class CompanyListingFilter(django_filters.FilterSet):
    def __init__(self, data, *args, **kwargs):
        data = data.copy()
        data.setdefault('order', '-rating')
        super().__init__(data, *args, **kwargs)
    order_by = OrderingFilter(label='Sort By', choices=(
        ('-asking_price', 'Price (Highest to Lowest'),
        ('asking_price', 'Price (Lowest to Highest)'),
        ('popularity', 'Popularity (Highest to Lowest)'),
        ('-popularity', 'Popularity (Lowest to Highest)'),
        ('rating', 'Rating (Highest to Lowest)'),
        ('-rating', 'Rating (Lowest to Highest)'),
        ('average_employee_efficiency', 'Company Efficiency(Highest to Lowest)'),
        ('-average_employee_efficiency', 'Company Efficiency(Lowest to Highest)')
    )
    )

    company_type_choices = (
        ('', 'Any'),
        ('Adult Novelties', 'Adult Novelties'),
        ('Amusement Park', 'Amusement Park'),
        ('Candle Shop', 'Candle Shop'),
        ('Car Dealership', 'Car Dealership'),
        ('Clothing Store', 'Clothing Store'),
        ('Cruise Line', 'Cruise Line'),
        ('Cyber Cafe', 'Cyber Cafe'),
        ('Detective Agency', 'Detective Agency'),
        ('Farm', 'Farm'),
        ('Firework Stand', 'Firework Stand'),
        ('Fitness Centre', 'Fitness Centre'),
        ('Flower Shop', 'Flower Shop'),
        ('Furniture Store', 'Furniture Store'),
        ('Game Shop', 'Game Shop'),
        ('Gas Station', 'Gas Station'),
        ('Gents Strip Club', 'Gents Strip Club'),
        ('Grocery Store', 'Grocery Store'),
        ('Gun Shop', 'Gun Shop'),
        ('Hair Salon', 'Hair Salon'),
        ('Ladies Strip Club', 'Ladies Strip Club'),
        ('Law Firm', 'Law Firm'),
        ('Lingerie Store', 'Lingerie Store'),
        ('Logistics Management', 'Logistics Management'),
        ('Meat Warehouse', 'Meat Warehouse'),
        ('Mechanic Shop', 'Mechanic Shop'),
        ('Mining Corporation', 'Mining Corporation'),
        ('Music Store', 'Music Store'),
        ('Nightclub', 'Nightclub'),
        ('Oil Rig', 'Oil Rig'),
        ('Private Security Firm', 'Private Security Firm'),
        ('Property Broker', 'Property Broker'),
        ('Pub', 'Pub'),
        ('Restaurant', 'Restaurant'),
        ('Software Corporation', 'Software Corporation'),
        ('Sweet Shop', 'Sweet Shop'),
        ('Television Network', 'Television Network'),
        ('Threatre', 'Threatre'),
        ('Toy Shop', 'Toy Shop'),
        ('Zoo', 'Zoo')
    )
    company_name_contains = CharFilter(
        label='Company Name', field_name='name', lookup_expr='icontains')
    company_type_choice = TypedChoiceFilter(
        label='Company Type', field_name='company_type', choices=company_type_choices)

    class Meta:
        model = Company
        fields = [('company_name_contains')]


class EmployeeListingFilter(django_filters.FilterSet):
    def __init__(self, data, *args, **kwargs):
        data = data.copy()
        data.setdefault('order', '-last_active')
        super().__init__(data, *args, **kwargs)

    order_by = OrderingFilter(label='Sort By', choices=(
        ('-work_stats_total', 'Total Work Stats (Highest to Lowest)'),
        ('work_stats_total', 'Total Work Stats (Lowest to Highest)'),
        ('-settings__job_post_start_date', 'Added (Newest to oldest)'),
        ('settings__job_post_start_date', 'Added (Oldest to newest)')
    )
    )
    status_choices = (
        ('', 'Any'),
        ('Online', 'Online'),
    )

    man_range = RangeFilter(widget=RangeWidget(attrs={
                            "placeholder": "", "class": "offset-1 col-5 form-control"}), label='Manual Labor', field_name='work_stats_man', lookup_expr='range')
    int_range = RangeFilter(widget=RangeWidget(attrs={
                            "placeholder": "", "class": "offset-1 col-5 form-control"}), label='Intelligence', field_name='work_stats_int', lookup_expr='range')
    end_range = RangeFilter(widget=RangeWidget(attrs={
                            "placeholder": "", "class": "offset-1 col-5 form-control"}), label='Endurance', field_name='work_stats_end', lookup_expr='range')

    model_name_contains = CharFilter(
        label='Player Name', field_name='name', lookup_expr='icontains')
    status = TypedChoiceFilter(
        label='Status', field_name='activity_status', choices=status_choices)

    class Meta:
        model = Listing
        fields = [('model_name_contains'), ('status'), ('order_by'),
                  ('man_range'), ('int_range'), ('end_range')]
