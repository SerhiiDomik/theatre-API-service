import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from theatre.models import Play, TheatreHall, Performance, Ticket, Reservation
from theatre.serializers import PerformanceListSerializer, PerformanceDetailSerializer
from datetime import datetime
from django.db.models import F, Count

PERFORMANCE_URL = reverse("theatre:performance-list")


def detail_url(performance_id):
    return reverse("theatre:performance-detail", args=[performance_id])


def sample_performance(**params):
    play = Play.objects.create(
        title=f"Sample-{uuid.uuid4()}", description="Sample description"
    )
    theatre_hall = TheatreHall.objects.create(
        name="Sample Hall", rows=10, seats_in_row=15
    )

    defaults = {
        "play": play,
        "theatre_hall": theatre_hall,
        "show_time": datetime.now(),
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def remove_key_from_dict_list(dict_list, key):
    for item in dict_list:
        if key in item:
            del item[key]


class UnauthenticatedPerformanceApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(PERFORMANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPerformanceApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_list_performances(self):
        sample_performance()
        sample_performance()

        response = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.all().order_by("show_time")
        serializer = PerformanceListSerializer(performances, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data["results"]
        remove_key_from_dict_list(response_data, "tickets_available")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data, serializer.data)

    def test_filter_performances_by_date(self):
        performance1 = sample_performance(show_time="2024-10-10T19:00:00")
        performance2 = sample_performance(show_time="2024-10-12T20:00:00")

        response = self.client.get(PERFORMANCE_URL, {"date": "2024-10-10"})

        serializer1 = PerformanceListSerializer(performance1)
        serializer2 = PerformanceListSerializer(performance2)

        response_data = response.data["results"]
        remove_key_from_dict_list(response_data, "tickets_available")

        self.assertIn(serializer1.data, response_data)
        self.assertNotIn(serializer2.data, response_data)

    def test_filter_performances_by_play(self):
        play1 = Play.objects.create(title="Play 1", description="Description 1")
        play2 = Play.objects.create(title="Play 2", description="Description 2")

        performance1 = sample_performance(play=play1)
        performance2 = sample_performance(play=play2)

        response = self.client.get(PERFORMANCE_URL, {"play": play1.id})

        serializer1 = PerformanceListSerializer(performance1)
        serializer2 = PerformanceListSerializer(performance2)

        response_data = response.data["results"]
        remove_key_from_dict_list(response_data, "tickets_available")

        self.assertIn(serializer1.data, response_data)
        self.assertNotIn(serializer2.data, response_data)

    def test_retrieve_performance_detail(self):
        performance = sample_performance()
        url = detail_url(performance.id)

        response = self.client.get(url)
        serializer = PerformanceDetailSerializer(performance)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_performance_forbidden(self):
        performance_payload = {
            "play": Play.objects.create(
                title="Test Play", description="Test description"
            ).id,
            "theatre_hall": TheatreHall.objects.create(
                name="Hall 1", rows=10, seats_in_row=20
            ).id,
            "show_time": datetime.now(),
        }

        response = self.client.post(PERFORMANCE_URL, performance_payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPerformanceApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

        self.theatre_hall = TheatreHall.objects.create(
            name="Sample Hall",
            rows=5,
            seats_in_row=5
        )

        self.play = Play.objects.create(
            title="Sample Play",
            description="Sample description"
        )

        self.performance = Performance.objects.create(
            show_time="2024-10-11T17:50:42",
            play=self.play,
            theatre_hall=self.theatre_hall
        )

    def test_admin_can_create_performance(self):
        play = Play.objects.create(title="Test Play", description="Test description")
        theatre_hall = TheatreHall.objects.create(
            name="Test Hall", rows=10, seats_in_row=20
        )
        payload = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": "2024-12-05 20:00:00",
        }

        response = self.client.post(PERFORMANCE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        performance = Performance.objects.get(id=response.data["id"])
        self.assertEqual(performance.play.id, payload["play"])
        self.assertEqual(performance.theatre_hall.id, payload["theatre_hall"])
        self.assertEqual(str(performance.show_time), payload["show_time"])

    def test_admin_can_update_performance(self):
        performance = sample_performance()
        new_play = Play.objects.create(
            title="Updated Play", description="Updated description"
        )
        new_theatre_hall = TheatreHall.objects.create(
            name="Updated Hall", rows=15, seats_in_row=25
        )
        payload = {
            "play": new_play.id,
            "theatre_hall": new_theatre_hall.id,
            "show_time": "2024-12-10 18:00:00",
        }

        url = detail_url(performance.id)
        response = self.client.put(url, payload)

        performance.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(performance.play.id, payload["play"])
        self.assertEqual(performance.theatre_hall.id, payload["theatre_hall"])
        self.assertEqual(str(performance.show_time), payload["show_time"])

    def test_tickets_available(self):

        reservation = Reservation.objects.create(user=self.admin_user)

        Ticket.objects.create(
            row=1,
            seat=1,
            performance=self.performance,
            reservation=reservation
        )
        Ticket.objects.create(
            row=2,
            seat=1,
            performance=self.performance,
            reservation=reservation
        )

        tickets_count = Ticket.objects.filter(performance=self.performance).count()
        expected_tickets_available = (
                self.theatre_hall.rows * self.theatre_hall.seats_in_row - tickets_count
        )

        response = self.client.get(PERFORMANCE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        performance_data = next(
            (item for item in response.data["results"] if item["id"] == self.performance.id)
        )

        self.assertEqual(performance_data["tickets_available"], expected_tickets_available)


