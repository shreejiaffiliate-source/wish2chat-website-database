import os
import django
from django.core.files import File

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

# 1. Target Categories
MASTER_CATEGORY_NAME = "National & Social"
SUB_CATEGORY_NAME = "Maharaja Agrasen Jayanti"

# 2. Content Type Label (As seen in Admin Panel dropdown)
# Likely 'Text Quote' or 'Quote'
TARGET_LABEL = 'Text Quote' 

# 3. Path to your .txt file containing quotes
# Make sure this file exists!
TXT_FILE_PATH = r"C:\Users\pkuma\Downloads\Master Category\Nation & Social\Maharaja Agrasen Jayanti\Quote\maharaja_agrasen_jayanti.txt"

# ==========================================
# 🚀 QUOTE UPLOAD SCRIPT
# ==========================================

def run_upload():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content

    # --- 1. FIND CORRECT CONTENT TYPE KEY ---
    print("🔍 Checking Content Type...")
    content_field = Content._meta.get_field('content_type')
    choices = content_field.choices
    
    valid_key = None
    if choices:
        for key, label in choices:
            if label.lower() == TARGET_LABEL.lower() or key.lower() == TARGET_LABEL.lower():
                valid_key = key
                break
    else:
        valid_key = TARGET_LABEL # Fallback

    if not valid_key:
        print(f"❌ Error: Could not find Content Type for '{TARGET_LABEL}'")
        return

    # --- 2. FIND CATEGORIES ---
    try:
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
    except Exception as e:
        print(f"❌ Category Error: {e}")
        return

    if not os.path.exists(TXT_FILE_PATH):
        print(f"❌ File not found: {TXT_FILE_PATH}")
        return

    # --- 3. READ & UPLOAD LOOP ---
    print(f"\n🚀 Reading quotes from: {TXT_FILE_PATH}")
    print(f"   Target: {master_cat.name} > {sub_cat.name} ({valid_key})")
    print("-" * 40)

    count = 0
    
    try:
        with open(TXT_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line in lines:
                quote_text = line.strip() # Remove spaces/newlines
                
                # Skip empty lines
                if not quote_text:
                    continue

                try:
                    # Create Content Object
                    new_content = Content()
                    new_content.sub_category = sub_cat
                    new_content.content_type = valid_key
                    new_content.is_premium = False
                    
                    # ✅ SAVE TEXT CONTENT
                    new_content.text_content = quote_text
                    
                    # Save object
                    new_content.save()
                    
                    # Print first 50 chars to show progress
                    print(f"   [OK] {quote_text[:50]}...")
                    count += 1
                    
                except Exception as e:
                    print(f"   [FAIL] Error saving quote: {e}")

    except Exception as e:
        print(f"❌ Error reading file: {e}")

    print("-" * 40)
    print(f"🎉 Success! Uploaded {count} quotes.")

if __name__ == '__main__':
    run_upload()