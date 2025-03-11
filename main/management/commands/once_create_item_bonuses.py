from django.core.management.base import BaseCommand
from main.models import ItemBonus

class Command(BaseCommand):
    help = 'Populates ItemBonus table with predefined bonus titles'

    def handle(self, *args, **options):
        bonus_titles = [
            'Achilles', 'Assassinate', 'Backstab', 'Berserk', 'Bleed', 
            'Blindfire', 'Blindside', 'Bloodlust', 'Burn', 'Comeback', 
            'Conserve', 'Cripple', 'Crusher', 'Cupid', 'Deadeye', 'Deadly', 
            'Demoralize', 'Disarm', 'Double-edged', 'Double Tap', 'Emasculate', 
            'Empower', 'Eviscerate', 'Execute', 'Expose', 'Finale', 'Focus', 
            'Freeze', 'Frenzy', 'Fury', 'Grace', 'Hazardous', 'Home run', 
            'Irradiate', 'Lacerate', 'Motivation', 'Paralyze', 'Parry', 
            'Penetrate', 'Plunder', 'Poison', 'Powerful', 'Proficience', 
            'Puncture', 'Quicken', 'Rage', 'Revitalize', 'Roshambo', 'Shock', 
            'Sleep', 'Slow', 'Smash', 'Smurf', 'Specialist', 'Spray', 'Storage', 
            'Stricken', 'Stun', 'Suppress', 'Sure Shot', 'Throttle', 'Toxin', 
            'Warlord', 'Weaken', 'Wind-up', 'Wither'
        ]

        created_count = 0
        skipped_count = 0

        for title in bonus_titles:
            # Use get_or_create to avoid duplicates
            bonus, created = ItemBonus.objects.get_or_create(title=title)
            if created:
                created_count += 1
            else:
                skipped_count += 1
            
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully added {created_count} new bonuses '
                f'(skipped {skipped_count} existing)'
            )
        )
