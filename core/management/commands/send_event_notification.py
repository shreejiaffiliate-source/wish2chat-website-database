import os
import firebase_admin
from firebase_admin import messaging, credentials
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from core.models import SubCategory, FCMDevice

class Command(BaseCommand):
    help = 'Sends daily 8 AM event notifications'

    def handle(self, *args, **options):
        # 1. Firebase Initialize (Check if already initialized)
        if not firebase_admin._apps:
            try:
                # Root folder mein serviceAccountKey.json hona chahiye
                cred_path = os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self.stdout.write(self.style.SUCCESS("🔥 Firebase Initialized!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Firebase Init Error: {e}"))
                return

        # 2. Aaj ki date dhoondo (IST ke hisaab se)
        today = timezone.now().date()
        self.stdout.write(f"🔍 Checking for events on: {today}")

        # 3. Aaj ka event dhoondo
        event = SubCategory.objects.filter(date_event=today, is_active=True).first()

        if not event:
            self.stdout.write(self.style.WARNING("⚠️ No event found for today in Database."))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ Event Found: {event.name}"))

        # 4. Message Body Taiyaar karo
        msg_title = "Special Occasion! ✨"
        msg_body = f"On the Occasion of {event.name}, share beautiful messages to your loved ones!"

        # 5. Saare Tokens nikaalo
        devices = FCMDevice.objects.all()
        if not devices.exists():
            self.stdout.write(self.style.ERROR("📱 No devices found in FCMDevice table."))
            return

        self.stdout.write(f"🚀 Sending to {devices.count()} devices...")

        # 6. Notifications bhejo (Loop)
        success_count = 0
        failure_count = 0

        for device in devices:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=msg_title,
                    body=msg_body,
                ),
                # App ke andar handling ke liye data payload bhi bhej sakte hain
                data={
                    "event_name": event.name,
                    "sub_category_id": str(event.id),
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                token=device.fcm_token,
            )

            try:
                messaging.send(message)
                success_count += 1
            except Exception as e:
                failure_count += 1
                self.stdout.write(self.style.ERROR(f"❌ Failed for {device.user.username}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"🎯 Task Finished! Sent: {success_count}, Failed: {failure_count}"
        ))