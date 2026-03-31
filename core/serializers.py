from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CategoryMaster, SubCategory, Content, UserProfile, UserDetailShareContent

# ✅ FIX 1: Add get_icon to ensure full URLs
class SubCategorySerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'icon', 'date_event']

    def get_icon(self, obj):
        request = self.context.get('request')
        if obj.icon:
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None

class CategoryMasterSerializer(serializers.ModelSerializer):
    # ✅ FIX 2: Use SerializerMethodField so it calls get_subcategories
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = CategoryMaster
        fields = ['id', 'name', 'slug', 'icon', 'subcategories']

    # ✅ FIX 3: Renamed to match field name (get_subcategories)
    def get_subcategories(self, obj):
        # Logic to check common related names
        if hasattr(obj, 'sub_categories'):
            active_items = obj.sub_categories.filter(is_active=True)
        elif hasattr(obj, 'subcategories'):
            active_items = obj.subcategories.filter(is_active=True)
        elif hasattr(obj, 'subcategory_set'):
            active_items = obj.subcategory_set.filter(is_active=True)
        else:
            return []
            
        # ✅ FIX 4: Pass 'context' so icons get the full URL
        return SubCategorySerializer(
            active_items, 
            many=True, 
            read_only=True,
            context=self.context 
        ).data

class ContentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    event_date = serializers.DateField(source='sub_category.date_event', read_only=True)

    class Meta:
        model = Content
        fields = ['id', 'sub_category', 'content_type', 'file_url', 'text_content', 'downloads', 'shares', 'event_date']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
# core/serializers.py

# core/serializers.py
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    mobileNumber = serializers.CharField(write_only=True, required=False)
    profile_picture = serializers.ImageField(required=False) # ✅ Added

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'mobileNumber', 'first_name', 'last_name', 'profile_picture']

    def create(self, validated_data):
        mobile = validated_data.pop('mobileNumber', '')
        f_name = validated_data.pop('first_name', '')
        l_name = validated_data.pop('last_name', '')
        profile_pic = validated_data.pop('profile_picture', None) # ✅ Get photo
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=f_name,
            last_name=l_name
        )

        # ✅ Photo ko UserProfile mein save karo
        UserProfile.objects.create(
            user=user, 
            mobile_number=mobile, 
            profile_picture=profile_pic
        )
        return user
    
class UserShareActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDetailShareContent
        fields = ['user', 'category', 'sub_category', 'share_type', 'activity_type', 'data']