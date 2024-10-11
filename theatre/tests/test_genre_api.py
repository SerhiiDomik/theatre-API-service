from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from theatre.models import Genre
from theatre.serializers import GenreSerializer


GENRE_URL = reverse("theatre:genre-list")


class UnauthenticatedGenreApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(GENRE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedGenreApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@test.test", password="testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_create_genre_forbidden(self):
        genre_payload = {
            "name": "Test Name",
        }
        response = self.client.post(GENRE_URL, genre_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_genre_list(self):
        Genre.objects.create(name="Test1")
        Genre.objects.create(name="Test2")

        response = self.client.get(GENRE_URL)
        genres = Genre.objects.all()
        serializer = GenreSerializer(genres, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)


class AdminGenreApiTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_genre(self):
        genre_payload = {
            "name": "test1",
        }

        response = self.client.post(GENRE_URL, genre_payload)

        genre = Genre.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(genre.name, genre_payload["name"])
