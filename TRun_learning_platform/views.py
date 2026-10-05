from django.shortcuts import render

from banners.models import Banner
from django.db.models import Q
from django.utils import timezone

from courses.models import Category, Course, Wishlist


def home(request):

    #get the banner details
    now=timezone.now()
    banners=Banner.objects.filter(is_active=True,position='Home').filter(Q(start_date__isnull=True) |Q(start_date__lte=now)).filter(Q(end_date__isnull=True) |Q(end_date__gte=now)).order_by('display_order')

    #get the categories
    categories=Category.objects.all()

    #get courses
    courses=Course.objects.filter(status='PUBLISHED').order_by('created_at')
    recomended_courses=courses.order_by('?')[0:4]

    #get the wishlist items
    
    wishlist_courses=Wishlist.objects.filter(user_id=request.user.user_id)
    wishlist_ids=wishlist_courses.values_list('course_id', flat=True)

    context={
        'banners':banners,
        'categories':categories[0:10],
        'top_categories':categories[0:6],
        'courses':courses[0:10],
        'recomended_courses':recomended_courses,
        'wishlist_course':wishlist_courses,
        'wishlist_ids':wishlist_ids
    }
    return render(request,'home.html',context)