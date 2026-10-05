from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser,PermissionsMixin

from accounts.manager import UserManager

class User(AbstractUser,PermissionsMixin):
    ROLE_CHOICES = [
        ("STUDENT", "Student"),
        ("TEACHER", "Teacher"),
        ("ADMIN", "Admin"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("SUSPENDED", "Suspended"),
    ]

    username = None
    
    user_id=models.BigAutoField(primary_key=True)
    first_name=models.CharField(max_length=100,blank=True,null=True)
    last_name=models.CharField(max_length=100,blank=True,null=True)
    email=models.EmailField(max_length=100,unique=True)
    phone=models.CharField(max_length=20,blank=True,null=True,unique=True)
    role=models.CharField(max_length=20,choices=ROLE_CHOICES,default='STUDENT')
    profile_image=models.ImageField(upload_to='profiles',blank=True,null=True)
    status=models.CharField(max_length=30,choices=STATUS_CHOICES,default='ACTIVE')
    is_active=models.BooleanField(default=True)
    is_staff=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    objects=UserManager()
    USERNAME_FIELD='email'
    REQUIRED_FIELDS=[]

    def __str__(self):
        return self.email