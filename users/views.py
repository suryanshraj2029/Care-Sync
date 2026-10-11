
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import User
from appointments.models import Appointment


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get(
            "confirm_password",
            request.POST.get("password2", "")
        )

        if not username or not password or not confirm_password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "register.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html")

        if len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )
            return render(request, "register.html")

        User.objects.create_user(
            username=username,
            password=password,
            role=User.Role.PATIENT
        )

        messages.success(
            request,
            "Registration successful! Please log in."
        )
        return redirect("login")

    return render(request, "register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard_view(request):
    user = request.user

    active_statuses = [
        Appointment.Status.BOOKED,
        Appointment.Status.CONFIRMED,
        Appointment.Status.ARRIVED,
        Appointment.Status.IN_CONSULTATION,
    ]

    if user.role == User.Role.PATIENT:
        dashboard_type = "patient"
        appointments = Appointment.objects.filter(
            patient=user
        ).select_related(
            "doctor"
        ).order_by(
            "appointment_date", "start_time"
        )

    elif user.role == User.Role.DOCTOR:
        dashboard_type = "doctor"
        appointments = Appointment.objects.filter(
            doctor=user
        ).select_related(
            "patient"
        ).order_by(
            "appointment_date", "start_time"
        )

    elif user.role == User.Role.RECEPTIONIST:
        dashboard_type = "receptionist"
        appointments = Appointment.objects.all().select_related(
            "patient", "doctor"
        ).order_by(
            "appointment_date", "start_time"
        )

    elif user.role == User.Role.ADMIN:
        dashboard_type = "admin"
        appointments = Appointment.objects.all().select_related(
            "patient", "doctor"
        ).order_by(
            "appointment_date", "start_time"
        )

    else:
        dashboard_type = "unknown"
        appointments = Appointment.objects.none()

    active_appointments_count = appointments.filter(
        status__in=active_statuses
    ).count()

    return render(
        request,
        "dashboard.html",
        {
            "dashboard_type": dashboard_type,
            "appointments": appointments,
            "active_appointments_count": active_appointments_count,
        }
    )
