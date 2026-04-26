from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),

    # Web interface endpoints
    path("login/", views.login_view, name="login-page-view"),  # GET login page
    path("signup/", views.signup_view, name="signup-page-view"),  # GET signup page
    
    # Authentication endpoints
    path("auth/signup/", views.signup, name="signup"), # POST signup
    path("auth/login/", views.login, name="login"), # POST login
    path("auth/logout/", views.logout, name="logout"), # POST logout

    # User dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Admin user management endpoints
    path("users/", views.users, name="users"),             # GET all users or POST create user
    path("users/<str:user_id>/", views.user_detail, name="user-detail"),  # GET, PUT, DELETE by ID
]
