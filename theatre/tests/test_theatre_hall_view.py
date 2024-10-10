from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from theatre.models import TheatreHall
from theatre.serializers import TheatreHallSerializer

THEATRE_HALL_URL = reverse("theatre:theatrehall-list")


class UnauthenticatedTheatreHallApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(THEATRE_HALL_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedTheatreHallApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword2321"
        )
        self.client.force_authenticate(self.user)

    def test_create_theatre_hall_forbidden(self):
        theatre_hall = {
            "name": "testnamehall",
            "rows": 10,
            "seats_in_row": 10,
        }

        response = self.client.post(THEATRE_HALL_URL, theatre_hall)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_theatre_hall_list(self):
        TheatreHall.objects.create(
            name="Testname",
            rows=10,
            seats_in_row=10,
        )
        TheatreHall.objects.create(
            name="Testname13",
            rows=20,
            seats_in_row=20,
        )

        response = self.client.get(THEATRE_HALL_URL)
        theatre_hall = TheatreHall.objects.all()
        serializer = TheatreHallSerializer(theatre_hall, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)


class AdminTheatreHallApiTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword1523",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_theatre_hall(self):
        theatre_hall_payload = {
            "name": "Testname13",
            "rows": 10,
            "seats_in_row": 10,
        }

        response = self.client.post(THEATRE_HALL_URL, theatre_hall_payload)

        theatre_hall = TheatreHall.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(theatre_hall.name, theatre_hall_payload["name"])
        self.assertEqual(theatre_hall.rows, theatre_hall_payload["rows"])
        self.assertEqual(
            theatre_hall.seats_in_row, theatre_hall_payload["seats_in_row"]
        )
        self.assertEqual(
            theatre_hall.capacity,
            theatre_hall_payload["rows"] * theatre_hall_payload["seats_in_row"]
        )
