
from django.contrib import admin

from .models import Appointment, DoctorAvailability


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "date",
        "start_time",
        "end_time",
        "slot_duration",
        "is_available",
    )
    list_filter = ("date", "is_available")
    search_fields = ("doctor__username",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "doctor",
        "appointment_date",
        "start_time",
        "status",
    )
    list_filter = ("status", "appointment_date")
    search_fields = (
        "patient__username",
        "doctor__username",
    )
