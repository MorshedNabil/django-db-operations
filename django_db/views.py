from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.utils import datetime_from_epoch
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .serializer import UserSerializer, LoginSerializer
from .database import UserDB
from .authentication import RawSQLJWTAuthentication
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render

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

# ================= API Views =================
# The API views will handle the actual logic for user management and authentication.
# To protect the API endpoints, we will use a custom JWT authentication class (RawSQLJWTAuthentication) 
# that checks the validity of the access token against the database records. As RawSQLJWTAuthentication does not rely on Django's ORM, it can be used seamlessly with our raw SQL-based UserDB class.
# The RawSQLJWTAuthentication class will be responsible for validating the JWT tokens and ensuring that only authenticated users can access the protected API endpoints.


# serializer is used to validate and serialize/deserialize data for the User model, 
# while the UserDB class provides static methods for performing CRUD operations on the user table in the database.
@api_view(['GET'])
def home(request):
    return Response({"message": "Welcome to the User API!"})

@api_view(['GET', 'POST'])
def users(request):
    """FOR ADMIN ONLY: List all users or create a new user"""
    if request.method == "GET":
        users = UserDB.get_all_users()
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
    """FOR ADMIN ONLY: Retrieve, update, or delete a user by ID"""
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

            result = UserDB.update_user(user_id, name, email, password)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == "DELETE":
        result = UserDB.delete_user(user_id)
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

        user = UserDB.get_user_by_email(email)
        #print(user)

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

            return Response({
                "message": "Login successful!",
                "access_token": str(access_token),
                "refresh_token": str(refresh_token)
                },status=status.HTTP_200_OK
            )

        return Response({"message": "Invalid email or password!"}, status=status.HTTP_401_UNAUTHORIZED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def logout(request):
    try:
        refresh_token = request.data["refresh_token"]

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"message": "Logout successful!"}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"message": "Logout failed!"}, status=status.HTTP_400_BAD_REQUEST)
