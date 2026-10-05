
from django.urls import  path
from . import views
urlpatterns = [ 
    path('',views.all_courses,name='all_courses'),
    path('details/<slug:slug>/',views.course_details,name='course_details'),
    path('comment/<slug:slug>/',views.comment_view,name='comment'),
    path('wishlist/',views.wishlist_view,name='wishlist'),
    path('wishlist/toggle/<int:id>/',views.toggle_wishlist_item,name='toggle_wishlist'),
    path('my-learning/',views.my_learning,name='my_learning'),
    
]