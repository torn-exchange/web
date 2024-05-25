import requests
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Profile, Settings
from main.models import Listing, Company
from datetime import datetime
from django.db.models import Q
import traceback
import numpy as np


class Command(BaseCommand):
    def _update(self):
        print('Updating company data')
        update_companies()
        print('Updating activity status of all profiles')
        active_traders = set(
            [a.owner.user for a in Listing.objects.filter().distinct('owner')])
        other_advertisers = set([a.user for a in Profile.objects.filter(settings__job_seeking=True) |
                                 Profile.objects.filter(settings__selling_losses=True) |
                                 Profile.objects.filter(settings__selling_revives=True) |
                                 Profile.objects.filter(
                                     settings__selling_company=True)
                                 ])
        users_to_be_checked = active_traders.union(other_advertisers)

        for profile in Profile.objects.filter(user__in=users_to_be_checked):
            if profile.api_key != '':
                req = requests.get(
                    f'https://api.torn.com/user/?selections=profile&key={profile.api_key}')
                data = json.loads(req.content)
                try:
                    status = data['last_action']['status']
                    time_stamp = data['last_action']['timestamp']
                    date_time = datetime.fromtimestamp(time_stamp)
                    naive_datetime = date_time
                    aware_datetime = timezone.make_aware(naive_datetime)
                    if profile.settings.job_seeking == True:
                        update_workstats_data(profile)
                    # if (profile.settings.selling_company == True) or (profile.settings.company_looking_to_hire == True):
                    #    update_company_sale_data(profile)
                    profile.activity_status = status
                    profile.last_active = aware_datetime
                    profile.save()
                except KeyError as e:
                    if data.get('error').get('error') == 'Incorrect key':
                        print(f'{profile.name} API key stale, cleaning from DB!')
                        profile.api_key = ''
                        profile.activity_status = 'Offline'
                        profile.save()
                        traceback.print_exc()
                    pass
        print('Done')

    def handle(self, *args, **options):
        self._update()
        # update_company_sale_data(Profile.objects.get(torn_id=2500210))


def update_companies():
    profiles_to_update = [obj.owner for obj in Settings.objects.filter(
        Q(company_looking_to_hire=True) | Q(selling_company=True))]
    for profile in profiles_to_update:
        update_company_sale_data(profile)
        profile.save()


def update_workstats_data(profile):
    work_data = json.loads(requests.get(
        f'https://api.torn.com/user/?selections=workstats&key={profile.api_key}').content)
    work_end = work_data.get('endurance')
    work_man = work_data.get('manual_labor')
    work_int = work_data.get('intelligence')
    profile.work_stats_int = work_int
    profile.work_stats_man = work_man
    profile.work_stats_end = work_end
    print(profile.name, work_int, work_man, work_end)


def update_company_sale_data(profile):
    print(f"Updating company stats of {profile.name}")
    try:
        name, company_id, company_type, rating, days_old, weekly_income, weekly_customers, employees_hired, employees_capacity, popularity, efficiency, average_employee_efficiency, average_employee_tenure = get_company_info(
            profile.api_key)
        print('Sucess')
    except Exception as e:
        # Could not find company under this users name from the API
        # If there is a company in our database with this profile as the owner, we should delete the company.
        print("Unable to fetch company data from API")
        print(e)
        company_model = Company.objects.filter(owner=profile).first()
        if company_model is not None:
            company_model.delete()
        return None
    # Assuming here we got valid data from the API we can update or create our company

    Company.objects.update_or_create(

        owner=profile,
        name=name,

        defaults=dict(
            company_id=company_id,
            company_type=company_type,
            rating=rating,
            days_old=days_old,
            weekly_income=weekly_income,
            weekly_customers=weekly_customers,
            employees_hired=employees_hired,
            employees_capacity=employees_capacity,
            popularity=popularity,
            efficiency=efficiency,
            average_employee_tenure=average_employee_tenure,
            average_employee_efficiency=average_employee_efficiency,
            negotiable=profile.settings.selling_company_price_negotiable,
            asking_price=profile.settings.selling_company_asking_price,
            description=profile.settings.selling_company_description,
        ),
    )


def get_company_info(api_key):
    company_dict = {
        "1": "Hair Salon",
        "2": "Law Firm",
        "3": "Flower Shop",
        "4": "Car Dealership",
        "5": "Clothing Store",
        "6": "Gun Shop",
        "7": "Game Shop",
        "8": "Candle Shop",
        "9": "Toy Shop",
        "10": "Adult Novelties",
        "11": "Cyber Cafe",
        "12": "Grocery Store",
        "13": "Threatre",
        "14": "Sweet Shop",
        "15": "Cruise Line",
        "16": "Television Network",
        "18": "Zoo",
        "19": "Firework Stand",
        "20": "Property Broker",
        "21": "Furniture Store",
        "22": "Gas Station",
        "23": "Music Store",
        "24": "Nightclub",
        "25": "Pub",
        "26": "Gents Strip Club",
        "27": "Restaurant",
        "28": "Oil Rig",
        "29": "Fitness Centre",
        "30": "Mechanic Shop",
        "31": "Amusement Park",
        "32": "Lingerie Store",
        "33": "Meat Warehouse",
        "34": "Farm",
        "35": "Software Corporation",
        "36": "Ladies Strip Club",
        "37": "Private Security Firm",
        "38": "Mining Corporation",
        "39": "Detective Agency",
        "40": "Logistics Management",
    }
    req = requests.get(
        f'https://api.torn.com/company/?selections=detailed,profile,employees&key={api_key}')
    data = json.loads(req.content)
    if data.get('error') is not None:
        return None
    else:

        name = data['company']['name']
        company_id = data['company']['ID']
        company_type = company_dict.get(str(data['company']['company_type']))
        rating = data['company']['rating']
        days_old = data['company']['days_old']
        weekly_income = data['company']['weekly_income']
        weekly_customers = data['company']['weekly_customers']
        employees_hired = data['company']['employees_hired']
        employees_capacity = data['company']['employees_capacity']
        popularity = data['company_detailed']['popularity']
        efficiency = data['company_detailed']['efficiency']
        average_employee_tenure = int(np.round(np.mean(
            [data['company_employees'][a]['days_in_company'] for a in data['company_employees']])))
        average_employee_efficiency = int(np.round(np.mean(
            [data['company_employees'][a]['effectiveness']['working_stats'] for a in data['company_employees']])))

        return name, company_id, company_type, rating, days_old, weekly_income, weekly_customers, employees_hired, employees_capacity, popularity, efficiency, average_employee_efficiency, average_employee_tenure
