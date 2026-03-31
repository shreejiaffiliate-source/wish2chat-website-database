import os
import django

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

# 🎯 Target Category to WIPE CLEAN
MASTER_CATEGORY_NAME = "National & Social"
SUB_CATEGORY_NAME = "Hindi Diwas"

# ==========================================
# 🗑️ DELETE ALL SCRIPT
# ==========================================

def run_wipe_clean():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content

    print(f"🚀 STARTING COMPLETE WIPE")
    print(f"   Target: {MASTER_CATEGORY_NAME} > {SUB_CATEGORY_NAME}")
    print("=" * 50)

    try:
        # 1. Find the Categories
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
        
        print(f"✅ Found Category: {sub_cat.name} (ID: {sub_cat.id})")

        # 2. Count items before deleting
        items_to_delete = Content.objects.filter(sub_category=sub_cat)
        count = items_to_delete.count()

        if count == 0:
            print("⚠️ The folder is already empty.")
            return

        # 3. Confirm (Optional safety pause)
        print(f"⚠️ WARNING: This will delete ALL {count} items in '{SUB_CATEGORY_NAME}'.")
        confirm = input("👉 Type 'yes' to confirm: ")
        
        if confirm.lower() != 'yes':
            print("❌ Operation cancelled.")
            return

        # 4. DELETE EVERYTHING
        deleted_count, _ = items_to_delete.delete()
        
        print("=" * 50)
        print(f"🎉 SUCCESS! Deleted {deleted_count} items.")
        print(f"🧹 '{SUB_CATEGORY_NAME}' is now completely empty.")

    except CategoryMaster.DoesNotExist:
        print(f"❌ Error: Master Category '{MASTER_CATEGORY_NAME}' not found.")
    except SubCategory.DoesNotExist:
        print(f"❌ Error: Sub Category '{SUB_CATEGORY_NAME}' not found.")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == '__main__':
    run_wipe_clean()