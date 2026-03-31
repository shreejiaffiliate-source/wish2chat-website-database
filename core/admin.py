from django.contrib import admin
from django import forms
from .models import CategoryMaster, SubCategory, Content, UserProfile, UserDetailShareContent, FCMDevice

@admin.register(CategoryMaster)
class CategoryMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

class SubCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = '__all__'
        labels = {
            'name': 'Sub Category',
        }

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    form = SubCategoryAdminForm
    
    fields = ('name', 'slug', 'parent', 'icon', 'date_event', 'is_active')

    # ✅ Update list_display to use the custom method for ID
    list_display = ('id', 'name', 'get_master_category_id', 'date_event', 'is_active')
    list_filter = ('parent', 'is_active')
      
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    # --- Custom Method to show ID instead of Name ---
    def get_master_category_id(self, obj):
        # Returns the raw ID of the parent category
        return obj.parent_id
    
    # ✅ Sets the column header name to "Category Master"
    get_master_category_id.short_description = 'Category Master'
    
    # Allows sorting by this column
    get_master_category_id.admin_order_field = 'parent'

# ✅ 1. Define the Custom Form
class ContentAdminForm(forms.ModelForm):
    # Virtual field for Master Category
    master_category = forms.ModelChoiceField(
        queryset=CategoryMaster.objects.filter(is_active=True),
        required=True,
        label="Master Category"
    )

    class Meta:
        model = Content
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Logic to populate fields when editing an existing object
        if self.instance.pk and self.instance.sub_category:
            # Set initial Master Category based on the saved Sub Category's parent
            self.fields['master_category'].initial = self.instance.sub_category.parent
            
            # Filter Sub Category dropdown to only show relevant items
            self.fields['sub_category'].queryset = SubCategory.objects.filter(
                parent=self.instance.sub_category.parent
            )
        
        # Logic to handle form submission (POST data)
        elif 'master_category' in self.data:
            try:
                master_id = int(self.data.get('master_category'))
                self.fields['sub_category'].queryset = SubCategory.objects.filter(parent_id=master_id)
            except (ValueError, TypeError):
                pass
        
        # Default state for new form (empty sub-category list)
        else:
            self.fields['sub_category'].queryset = SubCategory.objects.none()

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    form = ContentAdminForm
    
    # ✅ 1. Define the columns: ID, Master ID, Sub ID, Type, Date
    list_display = ('id', 'get_master_category_id', 'get_sub_category_id', 'content_type', 'created_at')
    
    # Filters sidebar
    list_filter = ('sub_category__parent', 'sub_category', 'content_type')
    
    # Optimize database queries (fetches related IDs in one go)
    list_select_related = ('sub_category', 'sub_category__parent')

    # JavaScript for the dependent dropdown
    class Media:
        js = ('admin/js/content_filter.js',)

    # Form fields order
    fields = ('master_category', 'sub_category', 'content_type', 'file', 'text_content', 'is_premium')

    # --- Custom Methods to get IDs (MOVED HERE) ---

    # Method to get Master Category ID
    def get_master_category_id(self, obj):
        # Access the parent ID through the sub_category relationship
        if obj.sub_category and obj.sub_category.parent_id:
            return obj.sub_category.parent_id
        return "-"
    get_master_category_id.short_description = 'Master Category'     # Column Header Name
    get_master_category_id.admin_order_field = 'sub_category__parent'  # Allow sorting by Master

    # Method to get Sub Category ID
    def get_sub_category_id(self, obj):
        # Return the direct foreign key ID
        return obj.sub_category_id
    get_sub_category_id.short_description = 'Sub Category'       # Column Header Name
    get_sub_category_id.admin_order_field = 'sub_category'     # Allow sorting by Sub Cat

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # ✅ CHANGED: Removed 'id' and replaced with 'get_user_id'
    list_display = ('get_user_id', 'get_first_name', 'get_last_name', 'get_username', 'get_password', 'get_email', 'mobile_number')
    
    # Optional: Add search capability
    search_fields = ('user__username', 'user__first_name', 'user__last_name' 'user__email', 'mobile_number')

    # --- Helper Methods to fetch data from the related User table ---

    # ✅ NEW METHOD: Gets the actual User ID (e.g., 7) instead of Profile ID (e.g., 4)
    def get_user_id(self, obj):
        return obj.user.id
    get_user_id.short_description = 'ID' # Column Header
    get_user_id.admin_order_field = 'user__id' # Sort by User ID

    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'First Name'  # Column Header

    def get_last_name(self,obj):
        return obj.user.last_name
    get_last_name.short_description = 'Last Name'

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'      # Column Header

    def get_password(self, obj):
        return obj.user.password
    get_password.short_description = 'Password (Hash)'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Gmail'            # Column Header

@admin.register(UserDetailShareContent)
class UserShareActivityAdmin(admin.ModelAdmin):
    # ✅ UPDATED: Using 'get_category_name' to fix the "-" issue
    list_display = ('id', 'get_user_id', 'get_category_name', 'get_subcategory', 'share_type', 'activity_type', 'data', 'created_at')
    
    # Filter by what happened and when
    list_filter = ('activity_type', 'share_type', 'category', 'created_at')
    
    # Search by User ID or Filename
    search_fields = ('user__username', 'data', 'sub_category__name')

    # Since this is a log, it's good practice to make it read-only so admins don't accidentally change history
    readonly_fields = ('user', 'category', 'sub_category', 'share_type', 'activity_type', 'data', 'created_at')

    # --- Helper Methods for Display ---

    def get_user_id(self, obj):
        return obj.user.id  # Shows the actual Numeric ID (e.g., 24)
    get_user_id.short_description = 'User ID'

    # ✅ FIXED LOGIC: Finds category even if field is empty
    def get_category_name(self, obj):
        # 1. If direct category exists, show it
        if obj.category:
            return obj.category.name
        # 2. If missing, check the sub-category's parent
        if obj.sub_category and obj.sub_category.parent:
            return obj.sub_category.parent.name
        return "-"
    get_category_name.short_description = 'Master Category'

    def get_subcategory(self, obj):
        return obj.sub_category.name if obj.sub_category else "-"
    get_subcategory.short_description = 'Sub Category'

@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'fcm_token', 'created_at')
    search_fields = ('user__username', 'fcm_token')