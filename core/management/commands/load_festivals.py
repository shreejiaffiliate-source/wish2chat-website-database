import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
# ✅ FIX: Import from 'core', not 'api'
from core.models import CategoryMaster, SubCategory

class Command(BaseCommand):
    help = 'Load festivals from 2026.json into SubCategory model'

    def handle(self, *args, **kwargs):
        # 1. Path to your JSON file
        json_file_path = os.path.join(settings.BASE_DIR, '2026.json')

        if not os.path.exists(json_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_file_path}'))
            return

        # 2. Ensure "Festivals" Master Category exists
        master_cat, created = CategoryMaster.objects.get_or_create(
            name="Festivals",
            defaults={'slug': 'festivals', 'is_active': True}
        )

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 3. Loop through the JSON structure
        count = 0
        if "2026" in data:
            year_data = data["2026"]
            for month, days in year_data.items():
                for date_str, details in days.items():
                    try:
                        # Parse date: "January 14, 2026, Wednesday"
                        dt = datetime.strptime(date_str, "%B %d, %Y, %A").date()
                        
                        event_name = details.get('event')
                        
                        # Create or Update the SubCategory
                        obj, created = SubCategory.objects.get_or_create(
                            name=event_name,
                            parent=master_cat,
                            defaults={
                                'slug': f"{event_name.lower().replace(' ', '-')}-2026",
                                'date_event': dt,
                                'is_active': True,
                            }
                        )
                        
                        # Update date if it existed but was wrong
                        if not created:
                            obj.date_event = dt
                            obj.save()
                            
                        count += 1
                        self.stdout.write(f"Processed: {event_name} - {dt}")

                    except ValueError as e:
                        self.stdout.write(self.style.WARNING(f"Skipping date {date_str}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} festivals into Database!'))