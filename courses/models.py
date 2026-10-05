from django.db import models

from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid

User=get_user_model()

# Create your models here.

class Category(models.Model):
    category_id=models.BigAutoField(primary_key=True)
    name=models.CharField(max_length=100)
    description=models.TextField(blank=True,null=True)
    status=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ("BEGINNER", "Beginner"),
        ("INTERMEDIATE", "Intermediate"),
        ("ADVANCED", "Advanced"),
        ("ALL", "All Levels"),
    ]

    COURSE_TYPE_CHOICES = [
        ("FREE", "Free"),
        ("PAID", "Paid"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ]

    course_id=models.BigAutoField(primary_key=True)
    instructor=models.ForeignKey(User,on_delete=models.SET_NULL,blank=True,null=True,related_name='instructor_course')
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name='category_course')
    title=models.CharField(max_length=100)
    slug=models.SlugField(max_length=200,unique=True,blank=True,null=True)
    description=models.TextField(blank=True,null=True)
    level=models.CharField(max_length=100,choices=LEVEL_CHOICES,default="ALL")
    course_type=models.CharField(max_length=100,choices=COURSE_TYPE_CHOICES)
    price=models.DecimalField(max_digits=20,decimal_places=2,default=0.0)
    discounted_price=models.DecimalField(max_digits=20,decimal_places=2,default=0.0)
    thumbnail=models.ImageField(upload_to='thumbnails',null=True,blank=True)
    duration_minutes=models.DecimalField(max_digits=6,decimal_places=2)
    status=models.CharField(max_length=100,choices=STATUS_CHOICES,default='DRAFT')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self,*args,**kwargs):
        if not self.course_id:
            short_uuid = str(uuid.uuid4())[:8]
            self.slug=f"{slugify(self.title)}-{short_uuid}"
        super().save(*args,**kwargs)



class Module(models.Model):
    module_id=models.BigAutoField(primary_key=True)
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='modules')
    title=models.CharField(max_length=200)
    description=models.TextField(blank=True,null=True)
    order_number=models.PositiveIntegerField(default=1)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    LESSON_TYPE_CHOICES = [
        ("VIDEO", "Video"),
        ("TEXT", "Text")
    ]
    lesson_id=models.BigAutoField(primary_key=True)
    module=models.ForeignKey(Module,on_delete=models.CASCADE,related_name='lessons')
    title=models.CharField(max_length=100)
    description=models.TextField(blank=True,null=True)
    lesson_type = models.CharField(max_length=20,choices=LESSON_TYPE_CHOICES,default="VIDEO")
    video=models.FileField(upload_to='videos/',blank=True,null=True)
    video_url=models.CharField(max_length=300,blank=True,null=True)
    content=models.TextField(blank=True,null=True)
    duration_minutes=models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    lesson_order=models.PositiveIntegerField(default=1)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Study_material(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ("PDF", "PDF"),
        ("DOCUMENT", "Document"),
        ("ZIP", "ZIP"),
        ("OTHER", "Other"),
    ]
    material_id=models.BigAutoField(primary_key=True)
    lesson=models.ForeignKey(Lesson,on_delete=models.CASCADE,related_name='study_materials')
    title=models.CharField(max_length=100)
    file_url=models.CharField(max_length=300,blank=True,null=True)
    material_type=models.CharField(max_length=100,choices=MATERIAL_TYPE_CHOICES,default='PDF')
    material=models.FileField(upload_to='materials/',blank=True,null=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



class CourseRating(models.Model):
    rating_id=models.BigAutoField(primary_key=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='CourseRating')
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='CourseRating')
    rating=models.SmallIntegerField()
    comment=models.CharField(max_length=300,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_rating"
            )
        ]

    def __str__(self):
        return f"{self.user}-{self.course}"


class Wishlist(models.Model):
    wishlist_id=models.BigAutoField(primary_key=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='wishlist')
    course=models.ForeignKey(Course,on_delete=models.CASCADE)
    added_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_wishlist"
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

class Cart(models.Model):
    cart_id=models.BigAutoField(primary_key=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='cart')
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='cart')
    added_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_cart"
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"


