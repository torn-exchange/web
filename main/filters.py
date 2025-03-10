from django import forms
import django_filters

from main.te_utils import service_categories, service_names

from .models import Listing, Company, Services, Item, ItemVariation, ItemVariationBonuses, ItemBonus
from django_filters import CharFilter, TypedChoiceFilter, OrderingFilter, RangeFilter, NumberFilter
from django_filters.widgets import RangeWidget

from django.db.models import F, Case, When, Value, FloatField, IntegerField, ExpressionWrapper
from django.db.models.functions import Cast, Coalesce, Least, Round


class ListingFilter(django_filters.FilterSet):
    def __init__(self, data, *args, **kwargs):
        data = data.copy()
        data.setdefault('order', '-traders_price')
        super().__init__(data, *args, **kwargs)

    order_by = OrderingFilter(
        label='Sort By', 
        choices=(
            ('-traders_price', 'Price (Highest to Lowest)'),
            ('traders_price', 'Price (Lowest to Highest)'),
            ('-owner__vote_score', 'Rating (Highest to Lowest)'),
            ('owner__vote_score', 'Rating (Lowest to Highest)'),
        )
    )
    
    def filter_queryset(self, queryset):
        queryset = queryset.select_related('owner__settings', 'item')
        
        # Annotate the queryset with the computed effective_price
        queryset = queryset.annotate(
            total_discount=Cast(
                Coalesce(F('discount'), Value(0)) + 
                Cast(Coalesce(F('owner__settings__trade_global_fee'), Value(0)), FloatField()),
                FloatField()
            ),
   
        traders_price=ExpressionWrapper(
            Round(
                Case(
                    When(discount__isnull=True, price__isnull=True, 
                         then=Value(None, output_field=FloatField())),
                    When(discount__isnull=True, 
                         then=Cast(F('price'), FloatField())),
                    
                    # Calculate discount price including item market (global) fee
                    When(price__isnull=True, 
                         then=Round(
                             Cast(
                                 (100.0 - F('total_discount')) / 100.0 * 
                                 Cast(Coalesce(F('item__TE_value'), Value(0)), FloatField()),
                                 FloatField()
                             )
                         )),
                    
                    # Default case
                    default=Round(
                        Cast(
                            Least(
                                (100.0 - F('total_discount')) / 100.0 * 
                                Cast(Coalesce(F('item__TE_value'), Value(0)), FloatField()),
                                Cast(F('price'), FloatField())
                            ),
                            FloatField()
                        )
                    ),
                    output_field=FloatField()
                )
            ),
            output_field=IntegerField()  # Final conversion to Integer
        )
        )
        
        # Exclude rows where traders_price is 0 or None
        queryset = queryset.exclude(traders_price=0).exclude(traders_price__isnull=True)
    
        # Ensure the annotated field is used correctly in the queryset
        if 'order' in self.data:
            order = self.data['order']
            if order in ['-traders_price', 'traders_price']:
                queryset = queryset.order_by(order)
        
        return super().filter_queryset(queryset)
    
    @property
    def qs(self):
        return self.filter_queryset(super().qs)
    
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


class ItemVariationFilter(django_filters.FilterSet):
    items = Item.objects.filter(item_type__in=['Melee', 'Primary', 'Secondary'])
    item_choices = [(item.id, item.name) for item in items]

    item__name = TypedChoiceFilter(field_name='item__name', choices=item_choices, label='Item')
    accuracy = NumberFilter(field_name='accuracy', lookup_expr='gte', label='Min Accuracy')
    damage = NumberFilter(field_name='damage', lookup_expr='gte', label='Min Damage')
    # armor = NumberFilter(field_name='armor', lookup_expr='gte', label='Min Armor')
    quality = NumberFilter(field_name='quality', lookup_expr='gte', label='Min Quality')
    rarity = TypedChoiceFilter(field_name='rarity', choices=ItemVariation.RARITY_CHOICES, label='Rarity')
    price = NumberFilter(field_name='price', lookup_expr='gte', label='Min Price')

    item_bonus_title_1 = TypedChoiceFilter(
        field_name='item_bonus__title',
        choices=[(bonus.title, bonus.title) for bonus in ItemBonus.objects.all()],
        label="Bonus 1"
    )
    bonus_value_1 = NumberFilter(field_name='itemvariationbonuses__value', lookup_expr='exact', label="Bonus 1 Value")

    item_bonus_title_2 = TypedChoiceFilter(
        field_name='item_bonus__title',
        choices=[(bonus.title, bonus.title) for bonus in ItemBonus.objects.all()],
        label="Bonus 2"
    )
    bonus_value_2 = NumberFilter(field_name='itemvariationbonuses__value', lookup_expr='exact', label="Bonus 2 Value")

    order_by = OrderingFilter(
        fields=(
            ('accuracy', 'accuracy'),
            ('damage', 'damage'),
            # ('armor', 'armor'),
            ('quality', 'quality'),
            ('price', 'price'),
            ('rarity', 'rarity'),
            ('bonus_value_1', 'bonus_value_1'),
            ('bonus_value_2', 'bonus_value_2'),
            ('owner__vote_score'),
        ),
        label='Order by',
    )

    def filter_queryset(self, queryset):
        queryset = queryset.filter(is_saleable=True)

        # Apply additional filters
        title_1 = self.data.get('item_bonus_title_1', None)
        bonus_value_1 = self.data.get('bonus_value_1', None)
        title_2 = self.data.get('item_bonus_title_2', None)
        bonus_value_2 = self.data.get('bonus_value_2', None)

        if title_1 and bonus_value_1:
            queryset = queryset.filter(itemvariationbonuses__bonus__title=title_1,
                                       itemvariationbonuses__value=bonus_value_1)
        if title_2 and bonus_value_2:
            queryset = queryset.filter(itemvariationbonuses__bonus__title=title_2,
                                       itemvariationbonuses__value=bonus_value_2)

        return queryset

    class Meta:
        model = ItemVariation
        fields = [
            'item__name',
            'accuracy',
            'damage',
            # 'armor',
            'quality',
            'rarity',
            'price',
            'item_bonus_title_1',
            'bonus_value_1',
            'item_bonus_title_2',
            'bonus_value_2'
        ]


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
                            "placeholder": "", "class": "col-5 form-control"}), label='Manual Labor', field_name='work_stats_man', lookup_expr='range')
    int_range = RangeFilter(widget=RangeWidget(attrs={
                            "placeholder": "", "class": "col-5 form-control"}), label='Intelligence', field_name='work_stats_int', lookup_expr='range')
    end_range = RangeFilter(widget=RangeWidget(attrs={
                            "placeholder": "", "class": "col-5 form-control"}), label='Endurance', field_name='work_stats_end', lookup_expr='range')

    model_name_contains = CharFilter(
        label='Player Name', field_name='name', lookup_expr='icontains')
    status = TypedChoiceFilter(
        label='Status', field_name='activity_status', choices=status_choices)

    class Meta:
        model = Listing
        fields = [('model_name_contains'), ('status'), ('order_by'),
                  ('man_range'), ('int_range'), ('end_range')]


class ServicesFilter(django_filters.FilterSet):
    def __init__(self, data, *args, **kwargs):
        data = data.copy()
        data.setdefault('order', '-owner__vote_score')
        super().__init__(data, *args, **kwargs)

    order_by = OrderingFilter(
        label='Sort By', 
        choices=(
            ('-owner__vote_score', 'Rating (Highest to Lowest)'),
            ('owner__vote_score', 'Rating (Lowest to Highest)'),
        )
    )
    
    list_of_services = service_names()
    
    services_choices = tuple((service, service) for service in list_of_services)
    
    service = django_filters.MultipleChoiceFilter(
        label="Select multiple services",
        choices=services_choices,
        field_name='service__name', 
        widget=forms.CheckboxSelectMultiple
    )
