from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.utils import datetime_from_epoch
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .serializer import UserSerializer, LoginSerializer, SetPassSerializer
from .database import UserDB
from .authentication import RawSQLJWTAuthentication
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render
from django.core.cache import cache

# ================= Web Views =================
# To protect the web pages like dashboard, we will check for the presence of a valid access token in the cookies.

# Login and signup page views
def login_view(request):
    return render(request, 'login.html')

def signup_view(request):
    return render(request, 'signup.html')

# User Dashboard
def dashboard(request):
    token = request.COOKIES.get('access_token')

    if not token:
        return render(request, 'login.html')
    
    return render(request, 'dashboard.html')

# Change Password Page
def change_password_view(request):
    return render(request, 'change_password.html')

# ================= API Views =================
# The API views will handle the actual logic for user management and authentication.
# To protect the API endpoints, we will use a custom JWT authentication class (RawSQLJWTAuthentication) 
# that checks the validity of the access token against the database records. As RawSQLJWTAuthentication does not rely on Django's ORM, it can be used seamlessly with our raw SQL-based UserDB class.
# The RawSQLJWTAuthentication class will be responsible for validating the JWT tokens and ensuring that only authenticated users can access the protected API endpoints.


# Serializer is used to validate and serialize/deserialize data for the User model, 
# while the UserDB class provides static methods for performing CRUD operations on the user table in the database.
@api_view(['GET'])
@permission_classes([AllowAny])
def home(request):
    return Response({"message": "Welcome to the User API!"})

@api_view(['GET', 'POST'])
def users(request):
    """FOR ADMIN ONLY: List all users or create a new user"""
    if request.method == "GET":
        # Redis cache is applied for faster read 
        cache_key = 'users'
        
        cached_users = cache.get('users') # if data already in cache(cache hit) then return from the cache

        if cached_users is not None:
            print("Data coming from cache")
            return Response(cache.get('users'))
        
        # if data is not in cache then fetch from database and store it in cache for later use
        users = UserDB.get_all_users()
        cache.set(cache_key, users, timeout= 60*5) # data will be stored in cache for 5 min

        return Response(users)
    
    elif request.method == "POST":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            result = UserDB.create_user(name, email, password)
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, user_id):
    """FOR ADMIN ONLY: Retrieve, update, or delete a user by email"""
    if request.method == "GET":
        user = UserDB.get_user_by_id(user_id)
        if user:
            return Response(user)
        return Response({"message": "User not found!"}, status=status.HTTP_404_NOT_FOUND)
    
    elif request.method == "PUT":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            email = serializer.validated_data['email']
            password = make_password(serializer.validated_data['password'])

            result = UserDB.update_user(email, name, email, password)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == "DELETE":
        result = UserDB.delete_user(email)
        return Response(result, status=status.HTTP_200_OK)
    
    
# The signup and login views will handle user registration and authentication, respectively. 
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """Handle user signup"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        name = serializer.validated_data['name']
        email = serializer.validated_data['email']
        password = make_password(serializer.validated_data['password']) # Hash the password before storing it in the database

        result = UserDB.create_user(name, email, password)
        return Response(result, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# We generate tokens manually without for_user() to avoid the Django ORM User requirement.

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Handle user login and return JWT tokens"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        cache_key = f"user_{email}"
        
        user = UserDB.get_user_by_email(email)

        if user and check_password(password, user['password']):
            # Build token manually — cannot use for_user() because it requires
            # a real Django ORM User to save the OutstandingToken record.
            refresh_token = RefreshToken()
            refresh_token[jwt_settings.USER_ID_CLAIM] = user['user_id']
            access_token = refresh_token.access_token

            # Manually save to OutstandingToken so logout blacklisting works.
            # user=None is allowed (field is nullable in simplejwt migrations).
            OutstandingToken.objects.create(
                user=None,
                jti=refresh_token[jwt_settings.JTI_CLAIM],
                token=str(refresh_token),
                created_at=refresh_token.current_time,
                expires_at=datetime_from_epoch(refresh_token.payload['exp']),
            )
            # store the authentic user in cache
            cache.set(cache_key, user, timeout=60*5)
            print("cached the user")
            return Response({
                "message": "Login successful!",
                "access_token": str(access_token),
                "refresh_token": str(refresh_token)
                },status=status.HTTP_200_OK
            )

        return Response({"message": "Invalid email or password!"}, status=status.HTTP_401_UNAUTHORIZED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'GET'])
def logout(request):
    try:
        response = Response({"message": "Logout successful!"}, status=status.HTTP_200_OK)
        
        # Delete cache for the user
        email = request.user.email   # request.user populated because default is IsAuthenticated
        cache_key = f"user_{email}"
        cache.delete(cache_key)

        # Clear the access token cookie
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        # Try to blacklist the refresh token if provided
        refresh_token = request.data.get('refresh_token') if request.method == 'POST' else request.COOKIES.get('refresh_token')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except:
                pass  # Token blacklist failed, but logout still proceeds
        
        return response
    
    except Exception as e:
        return Response({"message": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    

# =============== User Change Password ==================
@api_view(['POST'])
def change_password(request):
    """Handle password change for a user"""
    try:
        serializer = SetPassSerializer(data=request.data) 

        if serializer.is_valid():
            email = serializer.validated_data['email']
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            
            # SECURITY CHECK: Verify user is changing their own password
            if request.user.email != email:
                return Response(
                    {"message": "You can only change your own password!"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user = request.user.data # request.user.data have all the data of the logged in user. check authentication.py for clarification

            # Verify current password
            if not check_password(current_password, user['password']):
                return Response(
                    {"message": "Current password is incorrect!"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Hash the new password
            hashed_new_password = make_password(new_password)

            # Update password in database
            msg = UserDB.update_password(email, hashed_new_password)
            
            # Clear cache so new password is fetched on next login
            cache_key = f"user_{email}"
            cache.delete(cache_key)

            return Response(
                {"message": msg}, 
                status=status.HTTP_200_OK
            )
        
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


    except Exception as e:
        return Response(
            {"message": f"Password change failed: {str(e)}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
