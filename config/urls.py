"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""





from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

from appointments.views import availability_management_page


def home(request):
    return render(request, "home.html")


urlpatterns = [
    # Home page
    path("", home, name="home"),

    # Django admin
    path("admin/", admin.site.urls),

    # Appointment and availability APIs
    path("api/", include("appointments.urls")),

    # Registration, login, logout, and dashboard
    path("accounts/", include("users.urls")),

    # Doctor availability management page
    path(
        "availability/manage/",
        availability_management_page,
        name="availability-management",
    ),
]



