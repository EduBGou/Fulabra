import json
import threading
import time

from channels.generic.websocket import WebsocketConsumer
from django.template.loader import render_to_string
from django.contrib.sessions.backends.base import SessionBase
from asgiref.sync import async_to_sync

from fulabra_app.utils import invite_to_lobby

from .forms import GameWordForm
from .contexts import *
from .models import *


class LobbyConsumer(WebsocketConsumer):
    disconnect_timers: dict[str, threading.Timer] = {}
    choose_word_timers = {}
    next_round_timers = {}

    def remove_player_disconnection_timer(self):
        timer_key = f"{self.lobby_code}_{self.player.id}"
        if timer_key in self.disconnect_timers:
            self.disconnect_timers[timer_key].cancel()
            del self.disconnect_timers[timer_key]

    def connect(self):
        self.user: User = self.scope["user"]
        self.session: SessionBase = self.scope.get("session", {})
        self.lobby_code: str = self.scope["url_route"]["kwargs"]["lobby_code"]
        self.category = Category.objects.first()
        self.lobby = LobbyGroup.objects.filter(code=self.lobby_code).first()
        self.lobby_player_membership: LobbyPlayer = None

        if not self.lobby:
            self.accept()
            self.send_error_message("This lobby doesn't exist.")
            self.close()
            return

        if self.user.is_authenticated:
            self.player = self.user.player
        else:
            guest_player_id = self.session.get("guest_player_id")
            self.player = (
                Player.objects.filter(id=guest_player_id).first()
                if guest_player_id
                else None
            )

        if not self.player:
            self.player = Player.objects.create(nickname="guest")
            self.session["guest_player_id"] = self.player.id
            self.session.save()

        self.accept()
        async_to_sync(self.channel_layer.group_add)(self.lobby_code, self.channel_name)

        self.remove_player_disconnection_timer()

        current_player_count = self.lobby.lobby_memberships.count()
        self.lobby_player_membership = LobbyPlayer.objects.filter(
            lobby=self.lobby, player=self.player
        ).first()

        if not self.lobby_player_membership:
            if current_player_count >= 3:
                self.send_error_message("This lobby is already full (max 3 players).")
                self.close()
                return

            LobbyPlayer.objects.filter(player=self.player).delete()
            self.lobby_player_membership = LobbyPlayer.objects.create(
                lobby=self.lobby, player=self.player
            )

        if self.lobby.status == LobbyGroup.LobbyStatus.PLAYING:
            self.game, _ = Game.objects.get_or_create(lobby=self.lobby)
            self.current_round = (
                GameRound.objects.filter(game=self.game)
                .order_by("-round_number")
                .first()
            )

            if self.game.status == Game.GameStatus.RESULT:
                html = render_to_string(
                    "fulabra_app/partials/round_result.html",
                    {"context": RoundResultContext(self.get_submissions())},
                )
                self.send(text_data=html)

            else:
                context = GameFrameContext(
                    self.lobby,
                    self.game,
                    self.current_round,
                    GameWordForm(round=self.current_round),
                )
                html = render_to_string(
                    "fulabra_app/partials/game_frame.html", {"context": context}
                )
                self.send(text_data=html)
        else:
            self.group_send_player_list()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            self.lobby_code, self.channel_name
        )

        if self.lobby_player_membership:
            timer_key = f"{self.lobby_code}_{self.player.id}"

            cleanup_timer = threading.Timer(
                10,
                self.player_cleanup,
                args=[self.lobby_code, self.lobby_player_membership.id, timer_key],
            )
            self.disconnect_timers[timer_key] = cleanup_timer
            cleanup_timer.start()

    def receive(self, text_data=None, bytes_data=None):
        import json

        data = json.loads(text_data)
        action = data.get("action")

        if action == "start_game":
            self.start_game()

        elif action == "return_lobby":
            self.return_lobby()

        elif action == "submit_word":
            self.submit_word(data)

        elif action == "cancel_submit":
            self.cancel_submit()

        elif data.get("category"):
            self.broadcast_category(data.get("category"))

    def start_game(self):
        self.lobby.refresh_from_db()
        members_count = self.lobby.lobby_memberships.count()

        if members_count != 3 or self.lobby.leader != self.player:
            return

        self.lobby.status = LobbyGroup.LobbyStatus.PLAYING
        self.lobby.save()

        self.game, created = Game.objects.get_or_create(
            lobby=self.lobby, category=self.category
        )

        if created:
            for membership in self.lobby.lobby_memberships.all():
                GamePlayer.objects.get_or_create(
                    game=self.game, player=membership.player
                )

        self.next_round()

    def return_lobby(self):
        url = invite_to_lobby(self.lobby)
        html = render_to_string("fulabra_app/hx_redirect.html", {"redirect_url": url})
        self.group_send_html(html)

    def submit_word(self, data_dict):
        self.lobby.refresh_from_db()
        self.game = Game.objects.filter(lobby=self.lobby).first()
        self.current_round = self.game.rounds.last()
        form = GameWordForm(data=data_dict, round=self.current_round)

        if form.is_valid():
            word_obj: Word = form.cleaned_data["word"]

            self.game = Game.objects.get(lobby=self.lobby)
            self.current_round = self.game.rounds.last()

            print(f"{self.player.nickname} -> submit: {word_obj.label}")

            if not SubmittedWord.objects.filter(
                round=self.current_round, player=self.player, word=word_obj
            ).first():
                SubmittedWord.objects.create(
                    round=self.current_round, player=self.player, word=word_obj
                )

            form.fields["word"].widget.attrs["readonly"] = "readonly"
            form.data["word"] = word_obj.label
            form.data["action"] = "cancel_submit"

        submission_count = self.current_round.submitted_words.count()
        if submission_count >= 3:
            self.end_round()

        else:
            html = render_to_string(
                "fulabra_app/partials/word_form.html",
                {"context": WordFormContext(form, form.is_valid(), submission_count)},
            )

            self.send(text_data=html)

    def cancel_submit(self):
        self.lobby.refresh_from_db()
        submitted_word = SubmittedWord.objects.filter(
            round=self.current_round, player=self.player
        ).first()

        form = GameWordForm(round=self.current_round)
        form.data["action"] = "submit_word"

        if submitted_word:
            form.data["word"] = submitted_word.word.label
            submitted_word.delete()

        print(f"{self.player.nickname} -> cancel: {submitted_word.word.label}")

        submission_count = self.current_round.submitted_words.count()
        html = render_to_string(
            "fulabra_app/partials/word_form.html",
            {"context": WordFormContext(form, submission_count=submission_count)},
        )

        self.send(text_data=html)

    def broadcast_category(self, category_name):
        self.category = Category.objects.filter(name=category_name).first()

        if not self.category:
            self.send_error_message("Invalid Category!")
            return

        html = render_to_string(
            "fulabra_app/partials/category.html",
            {"context": CategoryContext(self.category)},
        )
        self.group_send_html(html)

    def run_countdown_choose_word_timer(self, lobby_code, duration):
        """Asynchronous worker that decrements time and pushes updates to clients"""
        for time_remaining in range(duration, -1, -1):
            if lobby_code not in self.choose_word_timers:
                return
            html = render_to_string(
                "fulabra_app/partials/round_countdown.html",
                {"seconds": time_remaining},
            )
            self.group_send_html(html)
            time.sleep(1)

        time.sleep(1)
        self.end_round()

    def perfom_scoring(
        self, submissions: List[SubmittedWord]
    ) -> List[RoundResultElement]:

        words = [sub.word for sub in submissions if sub.word]
        word_frequencies: dict[Word, int] = {}
        results: List[RoundResultElement] = []

        for w in words:
            if w in word_frequencies.keys():
                word_frequencies[w] += 1
            else:
                word_frequencies[w] = 1

        inactive_players = [m.player for m in self.game.game_memberships.all()]

        for sub in submissions:
            inactive_players.remove(sub.player)
            game_player = sub.player.game_membership

            if word_frequencies[sub.word] == 2:
                game_player.score += 1
                game_player.save()
                results.append(
                    RoundResultElement(sub.player, sub.word, game_player.score, "earns")
                )

            elif word_frequencies[sub.word] == 3 and game_player.score > 0:
                game_player.score -= 1
                game_player.save()
                results.append(
                    RoundResultElement(sub.player, sub.word, game_player.score, "loses")
                )
            else:
                results.append(
                    RoundResultElement(sub.player, sub.word, game_player.score)
                )

        for p in inactive_players:
            SubmittedWord.objects.create(round=self.current_round, player=p)
            results.append(RoundResultElement(p, None, p.game_membership.score))

        return results

    def end_round(self, verify: bool = False):
        print(f"round {self.current_round.round_number} ended!")
        if self.lobby_code in self.choose_word_timers:
            del self.choose_word_timers[self.lobby_code]

        if self.game.status != Game.GameStatus.CHOOSING:
            return

        self.game.refresh_from_db()
        self.game.status = Game.GameStatus.RESULT
        self.game.save()

        if self.player != self.lobby.leader and verify:
            return

        self.current_round = self.game.rounds.last()
        submissions = self.get_submissions()
        results = self.perfom_scoring(submissions)

        winners = self.filter_winners(results)
        game_over = len(winners) > 0

        if game_over:
            self.game.status = Game.GameStatus.FINISHED
            self.game.save()

        html = render_to_string(
            "fulabra_app/partials/round_result.html",
            {"context": RoundResultContext(results, game_over)},
        )
        self.group_send_html(html)

        if game_over:
            return

        if self.lobby_code not in self.next_round_timers:
            timer_thread = threading.Thread(
                target=self.run_next_round_timer,
                args=[5],
                daemon=True,
            )
            self.next_round_timers[self.lobby_code] = timer_thread
            timer_thread.start()

    def filter_winners(self, results: List[RoundResultElement]):
        winners: List[Player] = []
        for res in results:
            if res.score >= 3:
                winners.append(res.player)

        return winners

    def run_next_round_timer(self, duration):
        time.sleep(duration)
        self.next_round()

    def next_round(self):
        if self.lobby_code in self.next_round_timers:
            del self.next_round_timers[self.lobby_code]

        self.game.refresh_from_db()

        if self.game.rounds.last():
            self.current_round = self.game.rounds.last()
            next_round_number = self.current_round.round_number + 1
        else:
            next_round_number = 1

        self.current_round = GameRound.objects.create(
            game=self.game, round_number=next_round_number
        )

        self.game.status = Game.GameStatus.CHOOSING
        self.game.save()

        context = GameFrameContext(
            self.lobby,
            self.game,
            self.current_round,
            GameWordForm(round=self.current_round),
        )
        html = render_to_string(
            "fulabra_app/partials/game_frame.html", {"context": context}
        )
        self.group_send_html(html)

        if self.lobby_code not in self.choose_word_timers:
            timer_thread = threading.Thread(
                target=self.run_countdown_choose_word_timer,
                args=(self.lobby_code, 30),
                daemon=True,
            )
            self.choose_word_timers[self.lobby_code] = timer_thread
            timer_thread.start()

    def group_send_html(self, html):
        async_to_sync(self.channel_layer.group_send)(
            self.lobby_code,
            {"type": self.send_html_event.__name__, "html": html},
        )

    def send_html_event(self, event):
        self.send(text_data=event["html"])

    def get_submissions(self) -> QuerySet[SubmittedWord]:
        return self.current_round.submitted_words.select_related("word", "player").all()

    def group_send_player_list(self):
        async_to_sync(self.channel_layer.group_send)(
            self.lobby_code, {"type": self.send_player_list_event.__name__}
        )

    def send_player_list_event(self, event):
        if self.lobby_player_membership:
            try:
                self.lobby_player_membership.refresh_from_db()
            except LobbyPlayer.DoesNotExist:
                return

        self.lobby.refresh_from_db()
        context = PlayerListContext(self.lobby_player_membership)
        html = render_to_string(
            "fulabra_app/partials/player_list.html", {"context": context}
        )

        self.send(text_data=html)

    def player_cleanup(self, lobby_code: str, membership_id: int, timer_key: str):
        if timer_key in self.disconnect_timers:
            del self.disconnect_timers[timer_key]

        memebership = LobbyPlayer.objects.filter(id=membership_id).first()
        if memebership:
            memebership.delete()

        fresh_lobby = LobbyGroup.objects.filter(code=lobby_code).first()
        if not fresh_lobby:
            return

        if fresh_lobby.lobby_memberships.count() == 0:
            fresh_lobby.delete()
            print(f"Lobby {lobby_code} stayed empty and was deleted.")
        else:
            fresh_lobby.leader = (
                LobbyPlayer.objects.filter(lobby=fresh_lobby).first().player
            )
            fresh_lobby.save()
            self.group_send_player_list()

    def send_error_message(self, message: str):
        context = {"error_message": message}
        html = render_to_string(
            "fulabra_app/partials/error_message.html", {"context": context}
        )
        self.send(text_data=html)
