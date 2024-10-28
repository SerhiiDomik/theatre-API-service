import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from theatre.models import Play, TheatreHall, Performance, Ticket, Reservation
from theatre.serializers import PerformanceListSerializer, PerformanceDetailSerializer
from datetime import datetime
from django.db.models import F, Count

RESERVATION_URL = reverse("theatre:reservation-list")


# def detail_url(performance_id):
#     return reverse("theatre:performance-detail", args=[performance_id])


# def sample_performance(**params):
#     play = Play.objects.create(
#         title=f"Sample-{uuid.uuid4()}", description="Sample description"
#     )
#     theatre_hall = TheatreHall.objects.create(
#         name="Sample Hall", rows=10, seats_in_row=15
#     )
#
#     defaults = {
#         "play": play,
#         "theatre_hall": theatre_hall,
#         "show_time": datetime.now(),
#     }
#     defaults.update(params)
#
#     return Performance.objects.create(**defaults)


# def remove_key_from_dict_list(dict_list, key):
#     for item in dict_list:
#         if key in item:
#             del item[key]


class UnauthenticatedReservationApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(RESERVATION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedReservationApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(self.user)

        self.theatre_hall = TheatreHall.objects.create(name="Main Hall", rows=5, seats_in_row=5)
        self.play = Play.objects.create(title="Sample Play", description="Description of sample play")
        self.performance = Performance.objects.create(
            show_time="2024-10-12T20:00:00",
            play=self.play,
            theatre_hall=self.theatre_hall
        )

    def test_create_reservation_successful(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": self.performance.id},
                {"row": 2, "seat": 2, "performance": self.performance.id},
            ]
        }
        response = self.client.post(RESERVATION_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertEqual(Ticket.objects.count(), 2)
        tickets = Ticket.objects.filter(reservation__id=response.data["id"])
        self.assertEqual(tickets[0].row, payload["tickets"][0]["row"])
        self.assertEqual(tickets[0].seat, payload["tickets"][0]["seat"])

    def test_list_reservations_only_for_authenticated_user(self):
        other_user = get_user_model().objects.create_user(
            email="otheruser@test.com",
            password="password123"
        )
        Reservation.objects.create(user=other_user)
        Reservation.objects.create(user=self.user)

        response = self.client.get(RESERVATION_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_reservation_with_invalid_ticket_seat_row(self):
        payload = {
            "tickets": [
                {"row": 6, "seat": 1, "performance": self.performance.id},
                {"row": 2, "seat": 6, "performance": self.performance.id},
            ]
        }
        response = self.client.post(RESERVATION_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("row", response.data["tickets"][0])
        self.assertIn("seat", response.data["tickets"][1])

    def test_create_reservation_with_duplicate_tickets(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": self.performance.id},
                {"row": 1, "seat": 1, "performance": self.performance.id},
            ]
        }

        try:
            self.client.post(RESERVATION_URL, payload, format="json")
        except IntegrityError as e:
            return f"Database IntegrityError encountered: {e}"
