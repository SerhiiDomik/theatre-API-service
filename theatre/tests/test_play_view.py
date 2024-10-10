import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from theatre.models import Genre, Actor, Play
from theatre.serializers import PlaySerializer, PlayListSerializer, PlayDetailSerializer

PLAY_URL = reverse("theatre:play-list")


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


def sample_play(**params) -> Play:
    defaults = {
        "title": f"Sample-{uuid.uuid4()}",
        "description": "",
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


class UnauthenticatedPlayApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(PLAY_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedPlayApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@test.test",
            password="testpassword123"
        )
        self.client.force_authenticate(self.user)

        self.actor1 = Actor.objects.create(
            first_name="FirstName1",
            last_name="LastName1",
        )
        self.actor2 = Actor.objects.create(
            first_name="TestFirstName",
            last_name="TestLastName",
        )

        self.genre1 = Genre.objects.create(
            name="Genre11t12t"
        )
        self.genre2 = Genre.objects.create(
            name="TestGenre4214"
        )

    @staticmethod
    def serialize_list_play(play: Play) -> dict:
        return PlayListSerializer(play).data

    def test_plays_list(self):
        play_with_actors = sample_play()
        play_with_genres = sample_play()

        play_with_actors.actors.add(self.actor1, self.actor2)
        play_with_genres.genres.add(self.genre1, self.genre2)

        response = self.client.get(PLAY_URL)
        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_filter_plays_by_title(self):
        play_with_title_1 = sample_play(title="Inception")
        play_with_title_2 = sample_play(title="Interstellar")

        response = self.client.get(PLAY_URL, {"title": "Inception"})

        self.assertIn(PlayListSerializer(play_with_title_1).data, response.data["results"])
        self.assertNotIn(PlayListSerializer(play_with_title_2).data, response.data["results"])

    def test_filter_plays_by_genre(self):
        play_without_genre = sample_play()

        play_with_genre_1 = sample_play()
        play_with_genre_1.genres.add(self.genre1)

        play_with_genre_2 = sample_play()
        play_with_genre_2.genres.add(self.genre2)

        response = self.client.get(
            PLAY_URL,
            {"genres": f"{self.genre1.id},{self.genre2.id}"}
        )

        self.assertIn(self.serialize_list_play(play_with_genre_1), response.data["results"])
        self.assertIn(self.serialize_list_play(play_with_genre_2), response.data["results"])
        self.assertNotIn(self.serialize_list_play(play_without_genre), response.data["results"])

    def test_filter_plays_by_actor(self):
        play_without_actors = sample_play()

        play_with_actor_1 = sample_play()
        play_with_actor_1.actors.add(self.actor1)

        play_with_actor_2 = sample_play()
        play_with_actor_2.actors.add(self.actor2)

        response = self.client.get(
            PLAY_URL,
            {"actors": f"{self.actor1.id},{self.actor2.id}"}
        )

        self.assertIn(self.serialize_list_play(play_with_actor_1), response.data["results"])
        self.assertIn(self.serialize_list_play(play_with_actor_2), response.data["results"])
        self.assertNotIn(self.serialize_list_play(play_without_actors), response.data["results"])

    def test_retrieve_play_detail(self):
        play = sample_play()
        play.actors.add(self.actor1)
        play.genres.add(self.genre1)

        url = detail_url(play.id)

        response = self.client.get(url)

        serializer = PlayDetailSerializer(play)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_play_forbidden(self):
        play_payload = {
            "title": "Test title4sdf",
            "description": "Test description",
        }

        response = self.client.post(PLAY_URL, play_payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.actor1 = Actor.objects.create(
            first_name="FirstName1",
            last_name="LastName1",
        )
        self.actor2 = Actor.objects.create(
            first_name="TestFirstName",
            last_name="TestLastName",
        )

        self.genre1 = Genre.objects.create(
            name="Genre11t12t"
        )
        self.genre2 = Genre.objects.create(
            name="TestGenre4214"
        )

    def test_create_play(self):
        play_payload = {
            "title": "Test titleasd",
            "description": "Test description",
        }

        response = self.client.post(PLAY_URL, play_payload)
        print("response.data")
        print(response.data)
        play = Play.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in play_payload:
            self.assertEqual(play_payload[key], getattr(play, key))

    def test_create_play_with_actors_and_genres(self):
        play_payload = {
            "title": "Test title123",
            "description": "Test description",
            "actors": [self.actor1.id, self.actor2.id],
            "genres": [self.genre1.id, self.genre2.id],
        }

        response = self.client.post(PLAY_URL, play_payload)

        play = Play.objects.get(id=response.data["id"])

        actors = play.actors.all()
        genres = play.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(self.actor1, actors)
        self.assertIn(self.actor2, actors)
        self.assertEqual(actors.count(), 2)

        self.assertIn(self.genre1, genres)
        self.assertIn(self.genre2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_play_not_allowed(self):
        play = sample_play()

        url = detail_url(play.pk)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
