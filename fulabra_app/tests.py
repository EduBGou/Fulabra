from django.test import TestCase, Client
from django.urls import reverse

from fulabra_app.utils import lobby_is_full
from .consumers import *
from .models import *


def make_user(username="testuser", password="password!1234"):
    user = User.objects.create_user(
        username=username,
        password=password,
        email=f"{username}@test.com",
    )
    return user


def make_lobby(leader: Player) -> LobbyGroup:
    lobby = LobbyGroup.objects.create(leader=leader)
    LobbyPlayer.objects.create(lobby=lobby, player=leader)
    return lobby


def make_category_with_words(*labels) -> Category:
    category = Category.objects.create(name="Test Category")
    for label in labels:
        Word.objects.create(label=label, category=category)
    return category


class ScoringTest(TestCase):
    """
    Rule: if exactly 2 players submit the same word, both earn +1 point.
    """

    def setUp(self):
        self.user1 = make_user("user1", "password!1234")
        self.user2 = make_user("user2", "password!1234")
        self.user3 = make_user("user3", "password!1234")

        self.p1 = self.user1.player
        self.p2 = self.user2.player
        self.p3 = self.user3.player

        self.category = make_category_with_words("apple", "banana", "coco")
        self.word_a = Word.objects.get(label="apple")
        self.word_b = Word.objects.get(label="banana")
        self.word_c = Word.objects.get(label="coco")

        self.lobby = make_lobby(self.p1)
        LobbyPlayer.objects.create(lobby=self.lobby, player=self.p2)
        LobbyPlayer.objects.create(lobby=self.lobby, player=self.p3)

        self.game = Game.objects.create(
            lobby=self.lobby,
            category=self.category,
            status=Game.GameStatus.CHOOSING,
        )

        self.gp1 = GamePlayer.objects.create(game=self.game, player=self.p1, score=2)
        self.gp2 = GamePlayer.objects.create(game=self.game, player=self.p2, score=2)
        self.gp3 = GamePlayer.objects.create(game=self.game, player=self.p3, score=2)

        self.current_round = GameRound.objects.create(game=self.game, round_number=4)

    def test_zero_matching_perform_scoring(self):
        # p1 submits "apple"; p2 submits "banana"; p3 submits "coco"
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p1, word=self.word_a
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p2, word=self.word_b
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p3, word=self.word_c
        )

        submissions = get_submissions(self.current_round)

        results: List[RoundResultElement] = sorted(
            perform_scoring(self.game, submissions), key=lambda r: r.player.nickname
        )

        expected: List[RoundResultElement] = sorted(
            [
                RoundResultElement(self.p1, self.word_a, 2),
                RoundResultElement(self.p2, self.word_b, 2),
                RoundResultElement(self.p3, self.word_c, 2),
            ],
            key=lambda r: r.player.nickname,
        )

        self.assertEqual(results, expected, "no player should earns or loses a point")

    def test_two_matching_perform_scoring(self):
        # p1 and p2 submit "apple"; p3 submits "banana"
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p1, word=self.word_a
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p2, word=self.word_a
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p3, word=self.word_b
        )

        submissions = get_submissions(self.current_round)

        results: List[RoundResultElement] = sorted(
            perform_scoring(self.game, submissions), key=lambda r: r.player.nickname
        )

        expected: List[RoundResultElement] = sorted(
            [
                RoundResultElement(self.p1, self.word_a, 3, "earns"),
                RoundResultElement(self.p2, self.word_a, 3, "earns"),
                RoundResultElement(self.p3, self.word_b, 2),
            ],
            key=lambda r: r.player.nickname,
        )

        self.assertEqual(
            results, expected, "player 1 and 2 should earn a point for matching"
        )

    def test_three_matching_perform_scoring(self):
        # p1, p2 and p3 submit "apple";
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p1, word=self.word_a
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p2, word=self.word_a
        )
        SubmittedWord.objects.create(
            round=self.current_round, player=self.p3, word=self.word_a
        )
        submissions = get_submissions(self.current_round)

        results: List[RoundResultElement] = sorted(
            perform_scoring(self.game, submissions), key=lambda r: r.player.nickname
        )

        expected: List[RoundResultElement] = sorted(
            [
                RoundResultElement(self.p1, self.word_a, 1, "loses"),
                RoundResultElement(self.p2, self.word_a, 1, "loses"),
                RoundResultElement(self.p3, self.word_a, 1, "loses"),
            ],
            key=lambda r: r.player.nickname,
        )

        self.assertEqual(
            results, expected, "all players should loses a point for matching"
        )


class LobbyFullTest(TestCase):
    """
    A lobby is capped at 3 players. lobby_is_full() must return True when
    3 different players are already members and a 4th tries to join.
    """

    def setUp(self):

        users = [make_user(f"u{i}") for i in range(4)]
        self.players = [u.player for u in users]

        self.lobby = make_lobby(self.players[0])
        LobbyPlayer.objects.create(lobby=self.lobby, player=self.players[1])
        LobbyPlayer.objects.create(lobby=self.lobby, player=self.players[2])

    def test_lobby_accepts_third_player(self):
        self.assertFalse(
            lobby_is_full(self.lobby, self.players[2]),
            "Lobby should not be full for an existing member",
        )

    def test_lobby_rejects_fourth_player(self):
        fourth = self.players[3]
        self.assertTrue(
            lobby_is_full(self.lobby, fourth),
            "Lobby should be full for a new 4th player",
        )


class GuestFormTest(TestCase):
    """
    The function guest_form_view should:
        1. Create a Player with no linked User (is_guest == True)
        2. Store the new player id in the session
        3. Redirect to create_lobby (when no lobby_code given)
    """

    def setUp(self):
        self.client = Client()

    def test_guest_player_is_created_and_stored_in_session(self):

        url = reverse("guest_form")
        response = self.client.post(url, {"nickname": "test_guest"})

        self.assertRedirects(
            response, reverse("create_lobby"), fetch_redirect_response=False
        )

        guest_id = self.client.session.get("guest_player_id")
        player = Player.objects.filter(id=guest_id).first()

        self.assertIsNotNone(player, "Guest player should have been created")
        self.assertTrue(player.is_guest, "Player should have no linked User")


class CreateLobbyLoggedE2ETest(TestCase):
    """
    As a logged-in user, after clicking the "Create Lobby" button, the following should happen:
      1. POST to create_lobby
      2. Redirect to lobby_invite
      3. Redirect to lobby_room
      5. The lobby room page loads (200) and contains the lobby code
    """

    def setUp(self):
        self.client = Client()
        self.user = make_user("e2euser", "password!1234")
        self.client.login(username="e2euser", password="password!1234")

    def test_full_lobby_creation_flow(self):
        # POST to create_lobby
        response = self.client.post(reverse("create_lobby"))
        self.assertEqual(response.status_code, 302, "create_lobby should redirect")

        # A LobbyGroup must have been created with our player as leader
        player = self.user.player
        lobby = LobbyGroup.objects.filter(leader=player).first()
        self.assertIsNotNone(lobby, "A lobby should have been created for the player")

        # Follow redirect to lobby_invite
        response = self.client.get(response["Location"])
        self.assertEqual(
            response.status_code, 302, "lobby_invite should redirect to lobby_room"
        )

        # Follow redirect to lobby_room
        response = self.client.get(response["Location"])
        self.assertEqual(response.status_code, 200, "lobby_room should return 200")

        # Receive template context correctly.
        context = response.context["context"]
        self.assertEqual(context.current_lobby, lobby)
        self.assertEqual(context.player, player)
        self.assertEqual(context.invite, invite_to_lobby(lobby))
