from rest_framework import viewsets, filters, status
from django.shortcuts import render
import random
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailOTP
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token 
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.core.files.storage import default_storage 
from django.core.files.base import ContentFile       
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
from .models import CategoryMaster, SubCategory, Content, UserDetailShareContent, EmailOTP, FCMDevice, UserProfile
from .serializers import (
    CategoryMasterSerializer, 
    SubCategorySerializer, 
    ContentSerializer, 
    UserRegistrationSerializer,
    UserShareActivitySerializer
)

# 🔒 SECRET KEY FOR REMOTE UPLOADS
UPLOAD_SECRET_KEY = "MySuperSecretUploadPassword2026"

def api_home(request):
    # This tells Django to look for home.html inside your templates folder
    return render(request, 'home.html')

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

    # ✅ 1. Sahi jagah save karo: UserProfile model mein
    # get_or_create use kar rahe hain taaki agar profile na ho toh ban jaye
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Photo ko update karo
    profile.profile_picture = file
    profile.save()

    # ✅ 2. Full URL banao (Flutter ko poora path chahiye hota hai http://... ke saath)
    image_url = request.build_absolute_uri(profile.profile_picture.url)
    
    # 3. (Optional) Log rakhna hai toh purana wala code rehne do
    UserDetailShareContent.objects.create(
        user=user,
        share_type='image',
        activity_type='profile_picture', 
        data=image_url # Pura URL save karo
    )
    
    return Response({
        "message": "Profile picture updated successfully", 
        "url": image_url
    }, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    
    image_url = None
    # ✅ Check karo ki profile aur picture dono exist karte hain ya nahi
    if profile and profile.profile_picture:
        try:
            image_url = request.build_absolute_uri(profile.profile_picture.url)
        except ValueError:
            image_url = None

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_picture": image_url 
    })
    
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # 1. Check karo user exists or not
        from django.contrib.auth.models import User
        if not User.objects.filter(username=username).exists():
            return Response({"error": "Wrong Username"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Agar user hai, toh password verify karo
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name 
            }, status=status.HTTP_200_OK)
        
        # 3. Agar yahan tak aaya matlab password galat hai
        return Response({"error": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)

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
        
class SendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        username = request.data.get('username') # ✅ 1. Username field pakdo
        
        # Basic Validation
        if not email or not username:
            return Response({"error": "Email and Username are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ 2. Check if Email is already registered
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email is already registered"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ 3. Check if Username is already taken
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Save or Update OTP in Database
        EmailOTP.objects.update_or_create(email=email, defaults={'otp': otp})

        # Send Email
        try:
            send_mail(
                'Verify your Wish2Chat Account',
                f'Your verification code is: {otp}\n\nPlease enter this code in the app to complete your registration.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ✅ UPDATED API: Register User (Now Requires OTP)
class RegisterUserView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not otp:
            return Response({"error": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify OTP
        try:
            otp_record = EmailOTP.objects.get(email=email, otp=otp)
        except EmailOTP.DoesNotExist:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Proceed with Registration
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            
            # 3. Clean up OTP record so it can't be reused
            otp_record.delete() 
            
            return Response({
                "message": "User registered successfully", 
                "token": token.key,
                "user_id": user.id
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GoogleLoginView(APIView):
    def post(self, request):
        id_token_sent = request.data.get('id_token')
        try:
            idinfo = id_token.verify_oauth2_token(id_token_sent, requests.Request())
            email = idinfo['email']
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '') # Google ki profile photo

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0] + str(random.randint(10, 99)),
                    'first_name': name
                }
            )

            profile, p_created = UserProfile.objects.get_or_create(user=user)
            
            # Agar naya user hai toh Google wali photo save kar lo (Optional)
            # if p_created and picture:
            #    profile.remote_image_url = picture # Iske liye model mein field chahiye hogi

            drf_token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                "token": drf_token.key,
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_picture": picture # Google photo bhej do
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid Google Token"}, status=status.HTTP_400_BAD_REQUEST)

class SendResetOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not User.objects.filter(email=email).exists():
            return Response({"error": "No user found with this email"}, status=404)

        otp = str(random.randint(100000, 999999))
        EmailOTP.objects.update_or_create(email=email, defaults={'otp': otp})

        send_mail(
            'Password Reset OTP',
            f'Your OTP to reset password is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
        )
        return Response({"message": "OTP sent"})

class ResetPasswordConfirmView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        try:
            otp_record = EmailOTP.objects.get(email=email, otp=otp)
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            otp_record.delete()
            return Response({"message": "Password updated"})
        except EmailOTP.DoesNotExist:
            return Response({"error": "Invalid OTP"}, status=400)

class VerifyResetOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        # Check karo ki kya yeh email aur otp database mein match ho rahe hain
        if EmailOTP.objects.filter(email=email, otp=otp).exists():
            return Response({"message": "OTP is valid. Proceed to change password."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_fcm_token(request):
    token = request.data.get('fcm_token')
    if token:
        # ✅ Sahi Tarika: Pehle check karo agar ye token kisi aur ke paas toh nahi
        # Agar hai, toh usey wahan se hatao aur current user ko dedo
        FCMDevice.objects.filter(fcm_token=token).delete() 
        
        FCMDevice.objects.update_or_create(
            user=request.user, 
            defaults={'fcm_token': token}
        )
        return Response({"status": "Token saved"}, status=200)
    return Response({"error": "No token"}, status=400)