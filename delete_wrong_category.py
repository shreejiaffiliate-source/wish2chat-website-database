import os
import django

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

MASTER_CATEGORY_NAME = "Daily Wishes"
SUB_CATEGORY_NAME = "Good Evening"
BASE_FOLDER_PATH = r"C:\Users\pkuma\Downloads\Master Category\Daily Wishes Copy\Good Evening"

FOLDER_MAPPING = {
    'Image': 'Image',
    'GIF': 'GIF',
    'Sticker': 'Sticker',
    'Write Name': 'Write Name',
    'Quote': 'Text Quote'
}

# ==========================================
# 🗑️ SMART UNDO SCRIPT
# ==========================================

def run_undo():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content
    from django.db.models import Q

    print(f"🚀 STARTING SMART UNDO")
    print(f"   Target: {MASTER_CATEGORY_NAME} > {SUB_CATEGORY_NAME}")
    print("=" * 50)

    try:
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Category not found. {e}")
        return

    total_deleted = 0

    for folder_name, admin_label in FOLDER_MAPPING.items():
        folder_path = os.path.join(BASE_FOLDER_PATH, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        print(f"\n📂 Checking '{folder_name}'...")

        if admin_label == 'Text Quote':
            total_deleted += delete_text_quotes(folder_path, sub_cat)
        else:
            total_deleted += delete_media_files(folder_path, sub_cat)

    print("=" * 50)
    print(f"🎉 DONE! Deleted {total_deleted} items.")


def delete_media_files(folder_path, sub_cat):
    from core.models import Content
    from django.db.models import Q
    
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if filename.startswith('.'): continue # Skip hidden files
        
        # 1. Django replaces spaces with underscores. We must check that version too.
        normalized_name = filename.replace(' ', '_')
        
        # 2. Build a robust query:
        # Check if DB file path contains "Original Name" OR "Underscored Name"
        matches = Content.objects.filter(
            sub_category=sub_cat
        ).filter(
            Q(file__icontains=filename) | Q(file__icontains=normalized_name)
        )
        
        if matches.exists():
            deleted_count, _ = matches.delete()
            print(f"   🗑️ [DELETED] {filename} (Matches: {deleted_count})")
            count += deleted_count
        # else:
            # print(f"   ⚠️ [NOT FOUND] {filename}") 
            
    return count

def delete_text_quotes(folder_path, sub_cat):
    from core.models import Content
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if not filename.endswith('.txt'): continue
        file_full_path = os.path.join(folder_path, filename)

        try:
            with open(file_full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    text = line.strip()
                    if not text: continue

                    matches = Content.objects.filter(
                        sub_category=sub_cat,
                        text_content__iexact=text # Case-insensitive match for text
                    )
                    
                    if matches.exists():
                        deleted_count, _ = matches.delete()
                        print(f"   🗑️ [DELETED] Quote: {text[:20]}...")
                        count += deleted_count
        except Exception as e:
            print(f"   ❌ Error reading file {filename}: {e}")

    return count

if __name__ == '__main__':
    run_undo()