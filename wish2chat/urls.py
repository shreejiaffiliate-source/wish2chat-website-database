from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from core import views
from core.views import (
    CategoryMasterViewSet, 
    LoginView, 
    SubCategoryViewSet, 
    ContentViewSet, 
    RegisterUserView, 
    UserShareActivityView, 
    get_user_stats,
    get_user_favorites,
    get_user_profile, 
    update_profile_details, # ✅ Import
    upload_profile_picture ,
     api_home # ✅ Import
)
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'masters', CategoryMasterViewSet)
router.register(r'sub-categories', SubCategoryViewSet)
router.register(r'contents', ContentViewSet)

urlpatterns = [
    path('', api_home, name='home'),
    path('admin/', admin.site.urls),
    path('api/register/', RegisterUserView.as_view(), name='register'),
    path('api/', include(router.urls)),
    path('ajax/load-subcategories/', views.load_subcategories, name='ajax_load_subcategories'),
    path('api/record-share/', UserShareActivityView.as_view(), name='record_share'),
    path('api/user-stats/', get_user_stats, name='user_stats'),
    path('api/favorites/', get_user_favorites, name='user_favorites'),
    path('api/profile/', get_user_profile, name='user_profile'),
    # ✅ NEW EDIT PROFILE ENDPOINTS
    path('api/profile/update-name/', update_profile_details, name='update_name'),
    path('api/profile/update-image/', upload_profile_picture, name='update_image'),
    path('api/login/', LoginView.as_view(), name='login'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
