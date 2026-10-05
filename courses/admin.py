from django.contrib import admin

from courses.models import Cart, Category, Course, CourseRating, Lesson, Module, Study_material, Wishlist

# Register your models here.
admin.site.register(Category)
admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Wishlist)
admin.site.register(Study_material)
admin.site.register(CourseRating)
admin.site.register(Cart)