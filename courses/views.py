from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Category, Course, CourseRating, Wishlist
from payments.models import Enrollment
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# Create your views here.
def all_courses(request):
    courses=Course.objects.filter(status='PUBLISHED')
    categories=Category.objects.all()
    wishlist_ids=Wishlist.objects.filter(user_id=request.user.user_id).values_list('course_id', flat=True)

    #filter using search bar
    search_key=request.GET.get('search_box','')
    selected_category=request.GET.getlist('category','')
    # print(selected_category)
    selected_price=request.GET.getlist('price','')
    selected_level=request.GET.getlist('level','')
    select_created=request.GET.get('created','')
    selected_duration=request.GET.get('duration','')
    if search_key:       
        courses=courses.filter(Q(title__icontains=search_key) | Q(description__icontains=search_key))
    if selected_category:
        courses=courses.filter(category__name__in=selected_category)
    if selected_price:
        courses=courses.filter(course_type__in=selected_price)
    if selected_level:
        courses=courses.filter(level__in=selected_level)
    if select_created:
        if select_created=='newest':
            courses=courses.order_by('-created_at')
        else:
            courses=courses.order_by('created_at')
    if selected_duration:
        if selected_duration=='1-60':
            courses=courses.filter(duration_minutes__lte=60)
        elif selected_duration=='60-180':
            courses=courses.filter(duration_minutes__gt=60,duration_minutes__lte=180)
        elif selected_duration=='180-360':
            courses=courses.filter(duration_minutes__gt=180,duration_minutes__gte=360)
        elif selected_duration=='360-plus':
            courses=courses.filter(duration_minutes__gt=360)

    #filter by using side bar in courses
    selected_filter=request.GET.get('selected_filter','newest')
    # print(selected_filter)
    if selected_filter:
        if selected_filter=='newest':
            courses=courses.order_by('-created_at')
        elif selected_filter=='oldest':
            courses=courses.order_by('created_at')
        elif selected_filter=='low_to_high':
            courses=courses.order_by('discounted_price')
        elif selected_filter=='high_to_low':
            courses=courses.order_by('-discounted_price')

    context={
        'courses':courses,
        'categories':categories,
        'search_key':search_key,
        'selected_category':selected_category,
        'selected_price':selected_price,
        'selected_level':selected_level,
        'select_created':select_created,
        'selected_duration':selected_duration,
        'selected_filter':selected_filter,
        'wishlist_ids':wishlist_ids,
    }
    return render(request,'courses/courses.html',context)

def course_details(request,slug):
    course=Course.objects.get(slug=slug)
    enroll=False
    if request.user.is_authenticated:
        enroll=Enrollment.objects.filter(student=request.user,course=course,status__in=['ACTIVE','COMPLETED']).exists()
    context={
        'course':course,
        'enroll':enroll
    }
    return render(request,'courses/course_details.html',context)

def comment_view(request,slug):
    course=get_object_or_404(Course,slug=slug)
    if request.method=='POST':
        com=CourseRating.objects.filter(user=request.user,course=course)
        if com.exists():
            return redirect('course_details', slug=slug) 
        comment=request.POST.get('comment')
        rating=request.POST.get('rating')
        # print(comment,rating)
        CourseRating.objects.create(
            user=request.user,
            course=course,
            comment=comment,
            rating=rating
        )
        return redirect('course_details',slug=slug)
    return redirect('course_details', slug=slug)

@login_required(login_url='login')
def wishlist_view(request):
    wishlist_courses=Wishlist.objects.filter(user_id=request.user.user_id)
    selected_filter=request.GET.get('filter_wishlist')
    if selected_filter:
        if selected_filter=='latest_added':
            wishlist_courses=wishlist_courses.order_by('added_at')
        elif selected_filter=='asc_name':
            wishlist_courses=wishlist_courses.order_by('course_id__title')
        elif selected_filter=='low_to_high':
            wishlist_courses=wishlist_courses.order_by('course_id__discounted_price')
        elif selected_filter=='high_to_low':
            wishlist_courses=wishlist_courses.order_by('-course_id__discounted_price')

        
    context={
        'wishlist_courses':wishlist_courses,
        'selected_filter':selected_filter
    }
    return render(request,'courses/wishlist.html',context)

def toggle_wishlist_item(request,id):
    wishlist=Wishlist.objects.filter(user_id=request.user,course_id=id)
    course=get_object_or_404(Course,course_id=id)
    if wishlist.exists():
        wishlist.delete()
    else:
        Wishlist.objects.create(user_id=request.user.user_id,course_id=course.course_id)
    return redirect('wishlist')



def my_learning(request):
    if not request.user:
        return redirect('login')
    enrollments=Enrollment.objects.filter(student_id=request.user.user_id)
    active_count=enrollments.filter(status='ACTIVE').count()
    completed_count=enrollments.filter(status='COMPLETED').count()
    context={
        'enrollments':enrollments,
        'active_count':active_count,
        'completed_count':completed_count
    }
    return render(request,'my_learning.html',context)