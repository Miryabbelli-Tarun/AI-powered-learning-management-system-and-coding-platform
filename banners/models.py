from django.db import models

# Create your models here.
class Banner(models.Model):
    POSITION_CHOICES = [
        ("HOME", "Home"),
    ]

    banner_id=models.BigAutoField(primary_key=True)
    title=models.CharField(max_length=100)
    sub_title=models.CharField(max_length=250)
    title_caption=models.CharField(max_length=100,blank=True,null=True)
    image=models.ImageField(upload_to='banners/',blank=True,null=True)
    button_text=models.CharField(max_length=50,blank=True,null=True)
    button_url=models.CharField(max_length=100,blank=True,null=True)
    position=models.CharField(max_length=30,choices=POSITION_CHOICES,default='HOME')
    display_order=models.IntegerField(default=1)
    is_active=models.BooleanField(default=True)
    start_date=models.DateTimeField(blank=True,null=True)
    end_date=models.DateTimeField(blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)   

    def __str__(self):
        return self.title 

