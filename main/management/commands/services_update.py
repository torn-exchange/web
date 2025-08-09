from django.core.management.base import BaseCommand
from main.models import Service, ServiceCategories


class Command(BaseCommand):

    def updateServices(self):
        Service.objects.create(
            name = "Selling Trains",
            description = "Company directors are usually selling trains in order to increase their money supply",
            category = ServiceCategories.Other
        )
        
        Service.objects.create(
            name = "Leasing Properties",
            description = "Owning properties and leasing them to others",
            category = ServiceCategories.Other
        )
        
        Service.objects.filter(name="Graphics").update(
            category = ServiceCategories.Other
        )
        
        Service.objects.filter(name="RW Armor").update(
            category = ServiceCategories.Other
        )
        
        Service.objects.filter(name="RW Weapons").update(
            category = ServiceCategories.Other
        )

    def handle(self, *args, **options):
        self.updateServices()
