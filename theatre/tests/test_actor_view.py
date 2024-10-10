from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from theatre.models import Actor
from theatre.serializers import ActorSerializer

ACTOR_URL = reverse("theatre:actor-list")


class UnauthenticatedActorApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ACTOR_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedActorApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword23"
        )
        self.client.force_authenticate(self.user)

    def test_create_actor_forbidden(self):
        actor_payload = {
            "first_name": "Test Name",
            "last_name": "Test Last Name",
        }

        response = self.client.post(ACTOR_URL, actor_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_actor_list(self):
        Actor.objects.create(first_name="Test1", last_name="Test11")
        Actor.objects.create(first_name="Test2", last_name="Test22")

        response = self.client.get(ACTOR_URL)
        actors = Actor.objects.all()
        serializer = ActorSerializer(actors, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)


class AdminActorApiTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword1223",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_actor(self):
        actor_payload = {
            "first_name": "TestName1",
            "last_name": "TestLastName1",
        }

        response = self.client.post(ACTOR_URL, actor_payload)

        actor = Actor.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actor.first_name, actor_payload["first_name"])
        self.assertEqual(actor.last_name, actor_payload["last_name"])
        self.assertEqual(
            actor.full_name, f"{actor_payload['first_name']} "
                             f"{actor_payload['last_name']}"
        )
