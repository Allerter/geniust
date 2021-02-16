import json
from unittest.mock import MagicMock, create_autospec

import pytest
import tekore as tk
from requests import HTTPError

from geniust.server import (
    CronHandler,
    TokenHandler,
    GenresHandler,
    SearchHandler,
    RecommendationsHandler,
)
from geniust.db import Database


class TestCronHandler:
    def test_cron_handler(self):
        handler = MagicMock()

        CronHandler.get(handler)

        handler.write.assert_called_once()


class TestTokenHandler:
    @pytest.mark.parametrize(
        "state",
        [
            "1_genius_test-state",
            "1_spotify_test-state",
            "1_genius_invalid-state",
            "1_spotify_invalid-state",
        ],
    )
    @pytest.mark.parametrize("code", ["some_code", "invalid_code", "error"])
    @pytest.mark.parametrize("user_state", ["test-state", None])
    def test_token_handler(self, context, user_state, code, state):
        if len(state.split("_")) == 3:
            platform = state.split("_")[1]
        else:
            platform = None

        def get_argument(arg, default=None):
            if arg == "error" and code == "error":
                return "error"
            elif arg == "error":
                return default
            elif arg == "code":
                return code
            else:
                return state

        handler = MagicMock()
        handler.get_argument = get_argument
        handler.auths = context.bot_data["auths"]
        if code == "some_code" and platform == "genius":
            handler.auths["genius"].get_user_token.side_effect = None
            handler.auths["genius"].get_user_token.return_value = "test_token"
        elif code == "invalid_code" and platform == "genius":
            handler.auths["genius"].get_user_token.side_effect = HTTPError()
        elif code == "some_code" and platform == "spotify":
            handler.auths[
                "spotify"
            ]._cred.request_user_token().refresh_token = "test_token"
        elif code == "invalid_code" and platform == "spotify":
            res = MagicMock()
            res.response.status_code = 400
            error = tk.BadRequest("", None, res)
            handler.auths["spotify"]._cred.request_user_token.side_effect = error
        handler.database = create_autospec(Database)
        handler.bot = context.bot
        handler.texts = context.bot_data["texts"]
        handler.user_data = {1: {}}
        handler.user_data[1]["bot_lang"] = context.user_data["bot_lang"]
        handler.user_data[1]["state"] = user_state

        handler.request.protocol = "https"
        handler.request.host = "test-app.com"
        handler.request.uri = f"/callback?code={code}&state={state}"

        TokenHandler.get(handler)

        if (
            state == "1_genius_test-state"
            and user_state == "test-state"
            and code == "some_code"
        ):
            handler.auths["genius"].get_user_token.assert_called_once_with(
                "https://test-app.com/callback?code=some_code&state=1_genius_test-state"
            )
            handler.database.update_token.assert_called_once_with(
                1, "test_token", platform
            )
            assert handler.bot.send_message.call_args[0][0] == 1
            assert handler.user_data[1][f"{platform}_token"] == "test_token"
            assert "state" not in handler.user_data[1]
            handler.redirect.assert_called_once()
        elif (
            state == "1_spotify_test-state"
            and user_state == "test-state"
            and code == "some_code"
        ):
            handler.database.update_token.assert_called_once_with(
                1, "test_token", platform
            )
            assert handler.bot.send_message.call_args[0][0] == 1
            assert handler.user_data[1][f"{platform}_token"] == "test_token"
            assert "state" not in handler.user_data[1]
            handler.redirect.assert_called_once()
        elif code == "error":
            handler.redirect.assert_called_once()
        elif code == "invalid_code" or user_state is None:
            handler.database.update_token.assert_not_called()
        else:
            handler.set_status.assert_called_once_with(400)
            handler.finish.assert_called_once()

    def test_initialize(self):
        handler = MagicMock()
        auths = "auth"
        bot = "bot"
        database = "database"
        texts = "texts"
        user_data = "user_data"
        username = "username"

        res = TokenHandler.initialize(
            handler,
            auths=auths,
            database=database,
            bot=bot,
            texts=texts,
            user_data=user_data,
            username=username,
        )

        assert res is None
        assert handler.auths == auths
        assert handler.database == database
        assert handler.bot == bot
        assert handler.texts == texts
        assert handler.user_data == user_data
        assert handler.username == username


class TestGenresHandler:
    def test_initialize(self):
        handler = MagicMock()
        recommender = "recommender"

        res = GenresHandler.initialize(handler, recommender)

        assert res is None
        assert handler.recommender == recommender

    def test_set_default_headers(self):
        handler = MagicMock()

        res = GenresHandler.set_default_headers(handler)

        assert res is None
        handler.set_header.assert_called_once()

    @pytest.mark.parametrize("age", [None, 24, "err"])
    def test_get(self, recommender, age):
        handler = MagicMock()
        handler.recommender = recommender
        handler.get_argument.return_value = age

        GenresHandler.get(handler)
        res = json.loads(handler.write.call_args[0][0])

        handler.write.assert_called_once()
        if age is None:
            assert res["response"]["genres"] == recommender.genres
        elif age == 24:
            assert res["response"]["genres"] == recommender.genres_by_age(age)
        else:
            assert res["response"].get("genres") is None


class TestSearchHandler:
    def test_initialize(self):
        handler = MagicMock()
        recommender = "recommender"

        res = SearchHandler.initialize(handler, recommender)

        assert res is None
        assert handler.recommender == recommender

    def test_set_default_headers(self):
        handler = MagicMock()

        res = SearchHandler.set_default_headers(handler)

        assert res is None
        handler.set_header.assert_called_once()

    @pytest.mark.parametrize("artist", ["Nas", None])
    def test_get(self, recommender, artist):
        handler = MagicMock()
        handler.recommender = recommender
        handler.get_argument.return_value = artist

        SearchHandler.get(handler)
        res = json.loads(handler.write.call_args[0][0])

        handler.write.assert_called_once()
        if artist is None:
            assert res["response"].get("genres") is None
            handler.set_status.assert_called_once_with(404)
        else:
            assert "Nas" in res["response"]["artists"]


class TestRecommendationsHandler:
    def test_initialize(self):
        handler = MagicMock()
        recommender = "recommender"

        res = RecommendationsHandler.initialize(handler, recommender)

        assert res is None
        assert handler.recommender == recommender

    def test_set_default_headers(self):
        handler = MagicMock()

        res = RecommendationsHandler.set_default_headers(handler)

        assert res is None
        handler.set_header.assert_called_once()

    @pytest.mark.parametrize(
        "genres",
        [
            "pop,rap",
            "",
            "invalid",
        ],
    )
    @pytest.mark.parametrize("artists", ["Nas", "", "Nas,invalid"])
    @pytest.mark.parametrize("song_type", ["preview", "any", "invalid"])
    def test_get(self, recommender, genres, artists, song_type):
        handler = MagicMock()
        handler.recommender = recommender

        def get_argument(arg, default=None):
            if arg == "genres":
                return genres
            elif arg == "artists":
                return artists
            else:
                return song_type

        handler.get_argument = get_argument

        RecommendationsHandler.get(handler)
        res = json.loads(handler.write.call_args[0][0])

        handler.write.assert_called_once()
        if (
            genres in ("", "invalid")
            or artists in ("", "Nas,invalid")
            or song_type == "invalid"
        ):
            assert res["response"].get("genres") is None
            handler.set_status.assert_called_once_with(400)
        else:
            assert res["response"].get("tracks") is not None