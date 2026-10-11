
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from .models import DoctorAvailability, Appointment
from .serializers import (
    DoctorAvailabilitySerializer,
    AppointmentSerializer,
)


@login_required
def availability_management_page(request):
    """Display the availability management page."""
    allowed_roles = {
        User.Role.DOCTOR,
        User.Role.RECEPTIONIST,
        User.Role.ADMIN,
    }

    if request.user.role not in allowed_roles:
        return render(
            request,
            "availability.html",
            {"access_denied": True},
            status=403,
        )

    return render(request, "availability.html")


class DoctorAvailabilityListView(generics.ListCreateAPIView):
    """
    GET: List available slots for booking.
    GET with ?manage=1: Let authorized staff manage open and closed slots.
    POST: Create an availability slot.
    """

    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = DoctorAvailability.objects.filter(
            doctor__role=User.Role.DOCTOR,
            doctor__is_active=True,
        )

        manage = self.request.query_params.get("manage") == "1"

        # Closed slots are visible only in authorized management requests.
        if not (
            manage
            and user.role in {
                User.Role.DOCTOR,
                User.Role.RECEPTIONIST,
                User.Role.ADMIN,
            }
        ):
            queryset = queryset.filter(is_available=True)

        # Doctors can see only their own slots.
        if user.role == User.Role.DOCTOR:
            queryset = queryset.filter(doctor=user)

        # Patients can browse available slots.
        elif user.role == User.Role.PATIENT:
            pass

        # Receptionists and admins can filter by doctor.
        elif user.role in {
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }:
            doctor_id = self.request.query_params.get("doctor_id")
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)

        else:
            return DoctorAvailability.objects.none()

        # Optional date filter: ?date=YYYY-MM-DD
        date = self.request.query_params.get("date")
        if date:
            queryset = queryset.filter(date=date)

        return queryset.order_by("date", "start_time")

    def create(self, request, *args, **kwargs):
        allowed_roles = {
            User.Role.DOCTOR,
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }

        if request.user.role not in allowed_roles:
            return Response(
                {"detail": "You are not allowed to create availability."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().create(request, *args, **kwargs)


class DoctorAvailabilityDetailView(generics.RetrieveUpdateAPIView):
    """
    GET: View one availability slot.
    PUT/PATCH: Update an availability slot.
    """

    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = DoctorAvailability.objects.filter(
            doctor__role=User.Role.DOCTOR,
            doctor__is_active=True,
        )

        if user.role == User.Role.DOCTOR:
            return queryset.filter(doctor=user)

        if user.role in {
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }:
            return queryset

        return DoctorAvailability.objects.none()

    def update(self, request, *args, **kwargs):
        allowed_roles = {
            User.Role.DOCTOR,
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }

        if request.user.role not in allowed_roles:
            return Response(
                {"detail": "You are not allowed to update availability."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET: List appointments according to the user's role.
    POST: Book an appointment.
    """

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            "patient",
            "doctor",
            "availability",
        )

        if user.role == User.Role.PATIENT:
            return queryset.filter(patient=user).order_by(
                "-appointment_date",
                "-start_time",
            )

        if user.role == User.Role.DOCTOR:
            return queryset.filter(doctor=user).order_by(
                "-appointment_date",
                "-start_time",
            )

        if user.role in {
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }:
            return queryset.order_by(
                "-appointment_date",
                "-start_time",
            )

        return Appointment.objects.none()

    def create(self, request, *args, **kwargs):
        allowed_roles = {
            User.Role.PATIENT,
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }

        if request.user.role not in allowed_roles:
            return Response(
                {"detail": "You are not allowed to book appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().create(request, *args, **kwargs)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, pk):
    """Cancel an appointment when the user has permission."""

    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response(
            {"detail": "Appointment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    user = request.user

    if user.role == User.Role.PATIENT:
        if appointment.patient_id != user.id:
            return Response(
                {"detail": "You can cancel only your own appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

    elif user.role == User.Role.DOCTOR:
        if appointment.doctor_id != user.id:
            return Response(
                {"detail": "You can cancel only your own patients' appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

    elif user.role not in {
        User.Role.RECEPTIONIST,
        User.Role.ADMIN,
    }:
        return Response(
            {"detail": "You are not allowed to cancel appointments."},
            status=status.HTTP_403_FORBIDDEN,
        )

    closed_statuses = {
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
        Appointment.Status.NO_SHOW,
    }

    if appointment.status in closed_statuses:
        return Response(
            {"detail": "This appointment can no longer be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status"])

    return Response(
        {
            "detail": "Appointment cancelled successfully.",
            "appointment_id": appointment.id,
            "status": appointment.status,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_appointment_status(request, pk):
    """Allow authorized staff to update an appointment's status."""

    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        return Response(
            {"detail": "Appointment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    user = request.user

    if user.role == User.Role.DOCTOR:
        if appointment.doctor_id != user.id:
            return Response(
                {"detail": "You can update only your own appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

    elif user.role not in {
        User.Role.RECEPTIONIST,
        User.Role.ADMIN,
    }:
        return Response(
            {"detail": "You are not allowed to update appointment status."},
            status=status.HTTP_403_FORBIDDEN,
        )

    new_status = request.data.get("status")

    valid_statuses = {
        choice[0]
        for choice in Appointment.Status.choices
    }

    if new_status not in valid_statuses:
        return Response(
            {"detail": "Please provide a valid appointment status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    closed_statuses = {
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
        Appointment.Status.NO_SHOW,
    }

    if appointment.status in closed_statuses:
        return Response(
            {"detail": "This appointment is already closed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    appointment.status = new_status
    appointment.save(update_fields=["status"])

    return Response(
        {
            "detail": "Appointment status updated successfully.",
            "appointment_id": appointment.id,
            "status": appointment.status,
        },
        status=status.HTTP_200_OK,
    )
