from django.urls import path

from . import views
app_name = 'menus'
urlpatterns = [
    path("menu", views.menu, name="menu")
    
]

