from django.db import models
from django.contrib.auth.models import User

# 1. Parent Category (e.g., Greetings, Festivals, Valentine Week)
class CategoryMaster(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to='master_icons/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Category Master"
        verbose_name_plural = "Category Masters"

# 2. Sub Category (e.g., Good Morning, Diwali, Rose Day)
class SubCategory(models.Model):
    parent = models.ForeignKey(CategoryMaster, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to='sub_icons/', null=True, blank=True)
    date_event = models.DateField(null=True, blank=True, help_text="Specific date for festivals")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.parent.name} -> {self.name}"
    
    class Meta:
        verbose_name = "Sub Category"
        verbose_name_plural = "Sub Categories"

# 3. Content (Linked to SubCategory now)
class Content(models.Model):
    CONTENT_TYPES = (
        ('IMAGE', 'Image'),
        ('GIF', 'GIF'),
        ('STICKER', 'Sticker'),
        ('QUOTE', 'Text Quote'),
        ('WRITE_NAME', 'Write Name'),
    )
    # Changed link from Category to SubCategory
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(choices=CONTENT_TYPES, max_length=10)
    file = models.FileField(upload_to='wishes/', null=True, blank=True)
    text_content = models.TextField(null=True, blank=True)
    downloads = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sub_category.name} - {self.content_type}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
class UserDetailShareContent(models.Model):
    # What kind of file was it?
    SHARE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('gif', 'GIF'),
        ('sticker', 'Sticker'),
        ('quotes', 'Quotes'),
        ('writename', 'Write Name'),
    ]
    
    # What did they do? (e.g., Shared, Downloaded, Viewed)
    ACTIVITY_TYPE_CHOICES = [
        ('shared', 'Shared'),
        ('downloaded', 'Downloaded'),
        ('viewed', 'Viewed'),
        ('favorited', 'Favorited'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey('CategoryMaster', on_delete=models.SET_NULL, null=True, blank=True)
    sub_category = models.ForeignKey('SubCategory', on_delete=models.SET_NULL, null=True, blank=True)
    
    # "Image", "GIF", etc.
    share_type = models.CharField(max_length=20, choices=SHARE_TYPE_CHOICES)
    
    # "Shared"
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES, default='shared')
    
    # "goodmorning.jpg"
    data = models.CharField(max_length=255, help_text="Filename or Content Data")
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} {self.share_type}"

    class Meta:
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Detail Share Content"

class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.otp}"

class FCMDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fcm_token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.fcm_token[:10]}"