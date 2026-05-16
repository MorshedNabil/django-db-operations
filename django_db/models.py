from django.db import models

# Create your models here.
class User(models.Model):
    
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    # Indexing on email field
    class Meta:
        indexes = [models.Index(fields=['email'])]

    def __str__(self):
        return f"User(id={self.user_id}, name='{self.name}', email='{self.email}')"
    
class Reservation(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ]
    reservation_id = models.AutoField(primary_key=True)
    room_number = models.IntegerField(max_length=11)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.ForeignKey(User, on_delete= models.CASCADE, related_name= 'reservations' )