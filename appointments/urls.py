
from django.urls import path
from .views import (
    availability_management_page,
    DoctorAvailabilityListView,
    DoctorAvailabilityDetailView,
    AppointmentListCreateView,
    cancel_appointment,
    update_appointment_status,
)

urlpatterns = [
    path(
        "availability/manage/",
        availability_management_page,
        name="availability-management",
    ),
    path(
        "availability/",
        DoctorAvailabilityListView.as_view(),
        name="doctor-availability-list",
    ),
    path(
        "availability/<int:pk>/",
        DoctorAvailabilityDetailView.as_view(),
        name="doctor-availability-detail",
    ),
    path(
        "appointments/",
        AppointmentListCreateView.as_view(),
        name="appointment-list-create",
    ),
    path(
        "appointments/<int:pk>/cancel/",
        cancel_appointment,
        name="appointment-cancel",
    ),
    path(
        "appointments/<int:pk>/status/",
        update_appointment_status,
        name="appointment-status-update",
    ),
]
