import os
import django
from django.db.models import Q

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

# ✅ Double Check your Category Names in Admin Panel
MASTER_CATEGORY_NAME = "National & Social"
SUB_CATEGORY_NAME = "Tulsidas Jayanti"

# ✅ Double Check this Folder Path (Ensure it matches where you uploaded from)
BASE_FOLDER_PATH = r"C:\Users\pkuma\Downloads\Master Category\Nation & Social\Tulsidas Jayanti"

FOLDER_MAPPING = {
    'Image': 'Image',
    'GIF': 'GIF',
    'Sticker': 'Sticker',
    'Write Name': 'Write Name',
    'Quote': 'Text Quote'
}

# ==========================================
# 🧹 DEDUPLICATION SCRIPT (Keep 1, Remove Extras)
# ==========================================

def run_deduplicate():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content

    print(f"🚀 STARTING DEDUPLICATION")
    print(f"   Target: {MASTER_CATEGORY_NAME} > {SUB_CATEGORY_NAME}")
    print("=" * 50)

    try:
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Category not found. {e}")
        return

    total_cleaned = 0

    for folder_name, admin_label in FOLDER_MAPPING.items():
        folder_path = os.path.join(BASE_FOLDER_PATH, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        print(f"\n📂 Scanning '{folder_name}' for duplicates...")

        if admin_label == 'Text Quote':
            total_cleaned += clean_text_quotes(folder_path, sub_cat)
        else:
            total_cleaned += clean_media_files(folder_path, sub_cat)

    print("=" * 50)
    print(f"🎉 DONE! Removed {total_cleaned} duplicate items.")
    print("👉 NOTE: If you still see duplicates in the app, please clear App Data or Reinstall to refresh the cache.")


def clean_media_files(folder_path, sub_cat):
    from core.models import Content
    
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if filename.startswith('.'): continue
        
        normalized_name = filename.replace(' ', '_')
        
        # Find ALL records matching this filename
        matches = Content.objects.filter(
            sub_category=sub_cat
        ).filter(
            Q(file__icontains=filename) | Q(file__icontains=normalized_name)
        ).order_by('id') # Oldest first
        
        # ✅ THE FIX: If we have more than 1, delete the extras
        if matches.count() > 1:
            # Keep the first one (matches[0]), delete the rest (matches[1:])
            duplicates = matches[1:] 
            
            print(f"   ⚠️ Found {matches.count()} copies of {filename}. Keeping 1, deleting {len(duplicates)}.")
            
            for dup in duplicates:
                dup.delete()
                count += 1
                
    return count

def clean_text_quotes(folder_path, sub_cat):
    from core.models import Content
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if not filename.endswith('.txt'): continue
        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    text = line.strip()
                    if not text: continue

                    matches = Content.objects.filter(
                        sub_category=sub_cat,
                        text_content__iexact=text
                    ).order_by('id')
                    
                    # ✅ THE FIX: Delete duplicates, keep 1
                    if matches.count() > 1:
                        duplicates = matches[1:]
                        print(f"   ⚠️ Found {matches.count()} copies of quote '{text[:15]}...'. Deleting {len(duplicates)}.")
                        
                        for dup in duplicates:
                            dup.delete()
                            count += 1
                            
        except Exception as e:
            print(f"   ❌ Error reading file {filename}: {e}")

    return count

if __name__ == '__main__':
    run_deduplicate()