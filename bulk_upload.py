import os
import django
from django.core.files import File

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

# 1. Target Categories
MASTER_CATEGORY_NAME = "Daily Wishes"
SUB_CATEGORY_NAME = "Good Evening"

# 2. What are we uploading? (Write exactly as seen in Admin Panel)
# Options seen in your screenshot: 'Image', 'GIF', 'Sticker', 'Text Quote', 'Write Name'
TARGET_LABEL = 'Write Name' 

# 3. Path to your folder
SOURCE_FOLDER = r"C:\Users\pkuma\Downloads\Master Category\Daily Wishes\Good Evening\Write Name"

# ==========================================
# 🚀 SMART UPLOAD SCRIPT
# ==========================================

def run_upload():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content

    # --- DIAGNOSTIC: FIND CORRECT CONTENT TYPE KEY ---
    print("🔍 Inspecting Database Model for Content Types...")
    content_field = Content._meta.get_field('content_type')
    choices = content_field.choices # Returns list like [('IMAGE', 'Image'), ('GIF', 'GIF')...]
    
    valid_key = None
    
    # Try to find the correct database key for your target label
    if choices:
        print(f"   ℹ️ Valid choices found in DB: {choices}")
        for key, label in choices:
            if label.lower() == TARGET_LABEL.lower() or key.lower() == TARGET_LABEL.lower():
                valid_key = key
                print(f"   ✅ Match Found! You wrote '{TARGET_LABEL}', Database needs '{valid_key}'.")
                break
    else:
        # Fallback if no choices defined
        print("   ⚠️ No choices defined in model. Using raw string.")
        valid_key = TARGET_LABEL

    if not valid_key:
        print(f"❌ Error: Could not find a valid Content Type for '{TARGET_LABEL}'.")
        print(f"   Available options: {[label for key, label in choices]}")
        return

    # --- CATEGORY SETUP ---
    try:
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
    except Exception as e:
        print(f"❌ Category Error: {e}")
        return

    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Folder not found: {SOURCE_FOLDER}")
        return

    # --- UPLOAD LOOP ---
    print(f"\n🚀 Starting Upload to '{sub_cat.name}' as type '{valid_key}'...")
    count = 0
    files = os.listdir(SOURCE_FOLDER)

    for filename in files:
        if filename.startswith('.'): continue
        
        file_path = os.path.join(SOURCE_FOLDER, filename)
        
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'rb') as f:
                    new_content = Content()
                    new_content.sub_category = sub_cat
                    
                    # ✅ USE THE CORRECT KEY WE FOUND
                    new_content.content_type = valid_key
                    new_content.is_premium = False
                    
                    # ✅ SAVE=FALSE prevents saving before fields are ready
                    new_content.file.save(filename, File(f), save=False)
                    
                    # ✅ FINAL SAVE
                    new_content.save()
                    
                    print(f"   [OK] {filename}")
                    count += 1
            except Exception as e:
                print(f"   [FAIL] {filename}: {e}")

    print("-" * 40)
    print(f"🎉 Uploaded {count} items.")

if __name__ == '__main__':
    run_upload()