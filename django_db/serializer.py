from rest_framework import serializers
from .models import User
from .database import UserDB

# The UserSerializer class is a serializer for the User model, 
# which defines how to convert User instances to and from JSON format. 
# It includes all fields of the User model and specifies that the password field should be write-only
# write_only=True means that the password field will not be included in the serialized output when retrieving user data,
class UserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['user_id', 'name', 'email', 'password', 'confirm_password'] # Include all fields of the User model
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        
        if value != self.initial_data.get('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        
        return value.strip()  # Remove leading/trailing whitespace


    def validate_email(self, value):
        user_email = UserDB.get_user_by_email(value)

        if user_email:
            raise serializers.ValidationError("Email already exists.")
        return value.lower()  # Normalize email to lowercase for consistency


# Separate serializer for login — only needs email and password.
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()               
    password = serializers.CharField(write_only=True)  