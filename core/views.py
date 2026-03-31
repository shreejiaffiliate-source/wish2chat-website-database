from django.shortcuts import render
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token 
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.core.files.storage import default_storage 
from django.core.files.base import ContentFile       
from datetime import timedelta
from .models import CategoryMaster, SubCategory, Content, UserDetailShareContent
from .serializers import (
    CategoryMasterSerializer, 
    SubCategorySerializer, 
    ContentSerializer, 
    UserRegistrationSerializer,
    UserShareActivitySerializer
)

# 🔒 SECRET KEY FOR REMOTE UPLOADS
UPLOAD_SECRET_KEY = "MySuperSecretUploadPassword2026"

class CategoryMasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryMaster.objects.filter(is_active=True)
    serializer_class = CategoryMasterSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['slug']

class SubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    # This filters out inactive items AND inactive parents
    queryset = SubCategory.objects.filter(is_active=True, parent__is_active=True)
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['parent', 'slug']
    search_fields = ['name']

    def list(self, request, *args, **kwargs):
        # 🛠️ DEBUG PRINT: Check your terminal when you reload the App
        print("🚀 API HIT: SubCategoryViewSet is fetching data...") 
        return super().list(request, *args, **kwargs)

class ContentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Content.objects.all().order_by('-created_at')
    serializer_class = ContentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sub_category', 'sub_category__parent', 'content_type', 'is_premium']
    search_fields = ['text_content', 'sub_category__name']

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        upcoming_content = Content.objects.filter(
            sub_category__date_event__gte=today,
            sub_category__date_event__lte=thirty_days_later,
            sub_category__is_active=True
        ).order_by('sub_category__date_event')
        serializer = self.get_serializer(upcoming_content, many=True)
        return Response(serializer.data)

class UserShareActivityView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request):
        print(f"📥 Log Share: {request.data}") 
        data = request.data.copy()
        data['user'] = request.user.id
        
        if data.get('category') == 0 or data.get('category') == '0':
            data['category'] = None
        if data.get('sub_category') == 0 or data.get('sub_category') == '0':
            data['sub_category'] = None
        
        serializer = UserShareActivitySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Activity Recorded"}, status=status.HTTP_201_CREATED)
        
        print(f"❌ Log Failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        activity_type = request.data.get('activity_type')
        data_content = request.data.get('data')

        if not activity_type or not data_content:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = UserDetailShareContent.objects.filter(
            user=request.user,
            activity_type=activity_type,
            data=data_content
        ).delete()

        if deleted_count > 0:
            return Response({"message": "Activity Removed"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No record found to delete"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats(request):
    user = request.user
    stats = UserDetailShareContent.objects.filter(user=user).aggregate(
        wishes=Count('id', filter=Q(activity_type='shared')),
        downloads=Count('id', filter=Q(activity_type='downloaded')),
        favorites=Count('id', filter=Q(activity_type='favorited'))
    )
    return Response({
        "wishes": stats['wishes'] or 0,
        "downloads": stats['downloads'] or 0,
        "favorites": stats['favorites'] or 0
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_favorites(request):
    fav_logs = UserDetailShareContent.objects.filter(
        user=request.user, 
        activity_type='favorited'
    ).order_by('-created_at')

    results = []
    for log in fav_logs:
        stype = str(log.share_type).strip().lower()
        is_image = stype in ['image', 'gif', 'sticker']

        if not is_image and log.data:
            data_str = str(log.data).lower()
            if data_str.startswith('http') or data_str.endswith('.jpg') or data_str.endswith('.png'):
                is_image = True

        file_val = log.data if is_image else None
        text_val = log.data if not is_image else None

        content_obj = {
            "id": log.id,
            "master_category": log.category.id if log.category else None,
            "sub_category": log.sub_category.id if log.sub_category else None,
            "content_type": log.share_type.upper(), 
            "file": file_val,       
            "file_url": file_val,   
            "text_content": text_val,
            "is_premium": False,
            "created_at": log.created_at
        }
        results.append(content_obj)

    return Response(results)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile_details(request):
    user = request.user
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    
    user.save()
    return Response({"message": "Profile updated successfully"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    user = request.user
    file = request.FILES.get('file')
    
    if not file:
        return Response({"error": "No file uploaded"}, status=400)

    file_path = default_storage.save(f"profiles/{user.id}_{file.name}", ContentFile(file.read()))
    file_url = f"/media/{file_path}" 
    
    UserDetailShareContent.objects.create(
        user=user,
        category=None, 
        sub_category=None,
        share_type='image',
        activity_type='profile_picture', 
        data=file_url 
    )
    
    return Response({"message": "Profile picture updated", "url": file_url})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    latest_pic_log = UserDetailShareContent.objects.filter(
        user=user, 
        activity_type='profile_picture'
    ).order_by('-created_at').first()
    
    image_url = latest_pic_log.data if latest_pic_log else None

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_picture": image_url 
    })

class RegisterUserView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "User registered successfully", 
                "token": token.key,
                "user_id": user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name 
            }, status=status.HTTP_200_OK)
        return Response({"error": "Invalid Username or Password"}, status=status.HTTP_400_BAD_REQUEST)

def load_subcategories(request):
    master_id = request.GET.get('master_id')
    print(f"🚀 AJAX HIT: Loading subcategories for Master ID: {master_id}")
    
    if not master_id:
        return JsonResponse([], safe=False)
    try:
        # Filter by Active Status AND Parent Active Status
        subcategories = SubCategory.objects.filter(
            parent_id=master_id, 
            is_active=True,          # SubCategory must be active
            parent__is_active=True   # MasterCategory must ALSO be active
        ).values('id', 'name').order_by('name')
        
        return JsonResponse(list(subcategories), safe=False)
    except Exception as e:
        print(f"Error loading subcategories: {e}")
        return JsonResponse([], safe=False)

# ✅ SECURE BULK UPLOAD API (Added back from previous steps)
class BulkUploadAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Upload-Secret') != UPLOAD_SECRET_KEY:
            return Response({"error": "Unauthorized"}, status=403)

        master_name = request.data.get('master_category')
        sub_name = request.data.get('sub_category')
        content_type = request.data.get('content_type')
        text_content = request.data.get('text_content')
        file_obj = request.FILES.get('file')

        try:
            master = CategoryMaster.objects.get(name__iexact=master_name)
            sub = SubCategory.objects.get(name__iexact=sub_name, parent=master)

            content = Content(
                sub_category=sub,
                content_type=content_type,
                is_premium=False,
                text_content=text_content if content_type == 'TEXT_QUOTE' else None
            )
            
            if file_obj:
                content.file = file_obj
            
            content.save()
            return Response({"status": "success", "id": content.id})

        except CategoryMaster.DoesNotExist:
            return Response({"error": f"Master Category '{master_name}' not found"}, status=404)
        except SubCategory.DoesNotExist:
            return Response({"error": f"Sub Category '{sub_name}' not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
def api_home(request):
    # This tells Django to look for home.html inside your templates folder
    return render(request, 'home.html')
