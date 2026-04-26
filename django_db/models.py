from django.db import models

# Create your models here.
class User(models.Model):
    
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)
    email = models.EmailField(max_length=20, unique=True)
    password = models.CharField(max_length=255)

    # Indexing on email field
    class Meta:
        indexes = [models.Index(fields=['email'])]

    def __str__(self):
        return f"User(id={self.user_id}, name='{self.name}', email='{self.email}')"