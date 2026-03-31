import os
import django
from django.core.files import File

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wish2chat.settings')

# 1. Target Categories
MASTER_CATEGORY_NAME = "Valentine"
SUB_CATEGORY_NAME = "Chocolate Day"

# 2. Path to the PARENT folder containing your sub-folders
# (e.g., The folder that holds 'Image', 'Quote', 'GIF', etc.)
BASE_FOLDER_PATH = r"C:\Users\pkuma\Downloads\Master Category\Addition\Chocolate"

# 3. Folder Name to Content Type Mapping
# keys = exact folder names on your PC
# values = exact labels in your Admin Panel dropdown
FOLDER_MAPPING = {
    'Image': 'Image',
    'GIF': 'GIF',
    'Sticker': 'Sticker',
    'Write Name': 'Write Name',
    'Quote': 'Text Quote'  # Special handling for text files
}

# ==========================================
# 🚀 UNIVERSAL UPLOAD SCRIPT
# ==========================================

def run_upload():
    django.setup()
    from core.models import CategoryMaster, SubCategory, Content

    print(f"🚀 STARTING UNIVERSAL UPLOAD")
    print(f"   Target: {MASTER_CATEGORY_NAME} > {SUB_CATEGORY_NAME}")
    print(f"   Source: {BASE_FOLDER_PATH}")
    print("=" * 50)

    # --- 1. FIND CATEGORIES ---
    try:
        master_cat = CategoryMaster.objects.get(name__iexact=MASTER_CATEGORY_NAME)
        sub_cat = SubCategory.objects.get(name__iexact=SUB_CATEGORY_NAME, parent=master_cat)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Category not found. {e}")
        return

    # --- 2. CACHE CONTENT TYPE KEYS ---
    # We build a map of {Label: DB_Key} (e.g., {'Text Quote': 'TEXT_QUOTE'})
    content_field = Content._meta.get_field('content_type')
    db_choices = dict((label.lower(), key) for key, label in content_field.choices)
    
    # Fallback if choices are empty
    if not db_choices:
        print("⚠️ Warning: No choices defined in model. Using raw strings.")

    # --- 3. PROCESS EACH FOLDER ---
    total_uploaded = 0

    for folder_name, admin_label in FOLDER_MAPPING.items():
        folder_path = os.path.join(BASE_FOLDER_PATH, folder_name)
        
        # skip if folder doesn't exist
        if not os.path.exists(folder_path):
            print(f"⚠️ Skipping '{folder_name}': Folder not found.")
            continue

        # Get correct DB key
        db_key = db_choices.get(admin_label.lower(), admin_label)
        
        print(f"\n📂 Processing '{folder_name}' -> Type: {admin_label} ({db_key})")
        
        if admin_label == 'Text Quote':
            total_uploaded += process_text_quotes(folder_path, sub_cat, db_key)
        else:
            total_uploaded += process_media_files(folder_path, sub_cat, db_key)

    print("=" * 50)
    print(f"🎉 GRAND TOTAL: Uploaded {total_uploaded} items across all types.")


def process_media_files(folder_path, sub_cat, content_type_key):
    """Handles Image, GIF, Sticker, Write Name"""
    from core.models import Content
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if filename.startswith('.'): continue
        file_full_path = os.path.join(folder_path, filename)

        if os.path.isfile(file_full_path):
            try:
                with open(file_full_path, 'rb') as f:
                    new_content = Content()
                    new_content.sub_category = sub_cat
                    new_content.content_type = content_type_key
                    new_content.is_premium = False
                    
                    # Save file with save=False first
                    new_content.file.save(filename, File(f), save=False)
                    new_content.save()
                    
                    print(f"   [OK] File: {filename}")
                    count += 1
            except Exception as e:
                print(f"   [FAIL] {filename}: {e}")
    return count


def process_text_quotes(folder_path, sub_cat, content_type_key):
    """Handles Text Quotes (.txt files)"""
    from core.models import Content
    count = 0
    files = os.listdir(folder_path)

    for filename in files:
        if not filename.endswith('.txt'): continue
        
        file_full_path = os.path.join(folder_path, filename)
        print(f"   📄 Reading quote file: {filename}")

        try:
            with open(file_full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    text = line.strip()
                    if not text: continue

                    try:
                        new_content = Content()
                        new_content.sub_category = sub_cat
                        new_content.content_type = content_type_key
                        new_content.is_premium = False
                        new_content.text_content = text
                        new_content.save()
                        
                        print(f"      [OK] Quote: {text[:30]}...")
                        count += 1
                    except Exception as e:
                        print(f"      [FAIL] Error saving quote: {e}")
        except Exception as e:
            print(f"   ❌ Error opening file {filename}: {e}")
            
    return count

if __name__ == '__main__':
    run_upload()