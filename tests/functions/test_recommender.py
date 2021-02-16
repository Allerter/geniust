from unittest.mock import patch, MagicMock

import pytest

from geniust import constants
from geniust.constants import Preferences
from geniust.functions import recommender as rcr


@pytest.mark.parametrize("age", [0, 10, 20, 50, 70, 100])
def test_genres_by_age(recommender, age):
    res = recommender.genres_by_age(age)

    assert isinstance(res, (list, tuple))
    for genre in res:
        assert genre in recommender.genres


@pytest.mark.parametrize("artist", ["Eminem", "test", ""])
def test_search_artists(recommender, artist):
    res = recommender.search_artist(artist)

    if artist == "Eminem":
        assert artist in res


@pytest.mark.parametrize("genres", [[], ["pop", "rap"], ["persian"]])
def test_binarize(recommender, genres):
    res = recommender.binarize(genres)

    assert sum(res) == len(genres)


@pytest.mark.parametrize("genres", [["pop", "rap"], ["persian"]])
@pytest.mark.parametrize("artists", [["Eminem"], []])
@pytest.mark.parametrize("song_type", ["any", "preview", "full", "preview,full"])
def test_shuffle(recommender, genres, artists, song_type):
    preferences = Preferences(genres=genres, artists=artists)

    res = recommender.shuffle(preferences, song_type)

    for song in res:
        if song_type == "preview,full":
            assert song.download_url and song.preview_url
        elif song_type == "preview":
            assert song.preview_url
        elif song_type == "full":
            assert song.download_url
        has_user_genres = False
        for genre in genres:
            has_user_genres = genre in song.genres or has_user_genres
        assert has_user_genres
        if "persian" in genres:
            assert "persian" in song.genres
        else:
            assert "persian" not in song.genres


@pytest.mark.parametrize("genius_token", ["test_token", None])
@pytest.mark.parametrize("spotify_token", ["test_token", None])
def test_welcome_to_shuffle(update_message, context, genius_token, spotify_token):
    update = update_message
    context.user_data["genius_token"] = genius_token
    context.user_data["spotify_token"] = spotify_token

    res = rcr.welcome_to_shuffle(update, context)

    assert res == constants.SELECT_ACTION


def test_input_preferences(update_callback_query, context):
    update = update_callback_query

    res = rcr.input_preferences(update, context)

    assert res == constants.SELECT_GENRES


@pytest.mark.parametrize(
    "update",
    [
        pytest.lazy_fixture("update_message"),
        pytest.lazy_fixture("update_callback_query"),
    ],
)
def test_input_age(update, context):
    if update.message:
        update.message.text = "20"

    res = rcr.input_age(update, context)

    if update.callback_query:
        assert res == constants.SELECT_GENRES
    else:
        assert res == constants.SELECT_ARTISTS


@pytest.mark.parametrize("genres", [[], ["pop"]])
@pytest.mark.parametrize("query_data", ["genre", "done", "select_4"])
def test_select_genres(update_callback_query, context, query_data, genres):
    update = update_callback_query
    update.callback_query.data = query_data
    context.user_data["genres"] = genres

    rcr.select_genres(update, context)

    if context.user_data["bot_lang"] == "fa" and query_data == "genres":
        assert "persian" in context.user_data["genres"]


@pytest.mark.parametrize(
    "update",
    [
        pytest.lazy_fixture("update_message"),
        pytest.lazy_fixture("update_callback_query"),
    ],
)
def test_begin_artist(update, context):
    res = rcr.begin_artist(update, context)

    assert res == constants.SELECT_ARTISTS


def test_input_artist(update_callback_query, context):
    update = update_callback_query

    res = rcr.input_artist(update, context)

    assert res == constants.SELECT_ARTISTS


@pytest.mark.parametrize(
    "update",
    [
        pytest.lazy_fixture("update_message"),
        pytest.lazy_fixture("update_callback_query"),
    ],
)
@pytest.mark.parametrize("query", ["select_none", "select_0", "done"])
def test_select_artists(update, context, query):
    if update.message:
        update.message.text = "0"
    else:
        update.callback_query.data = query
        if query == "done":
            context.user_data["genres"] = ["pop"]
            context.user_data["artists"] = []

    rcr.select_artists(update, context)

    if update.callback_query and query == "done":
        context.bot_data["db"].update_preferences.assert_called_once()


@pytest.mark.parametrize("platform", ["genius", "spotify"])
def test_process_preferences(update_callback_query, context, platform):
    update = update_callback_query
    update.callback_query.data = f"process_{platform}"
    context.user_data["genius_token"] = "test_token"
    context.user_data["spotify_token"] = "test_token"

    client = MagicMock()
    current_module = "geniust.functions.recommender"
    with patch(current_module + ".tk", client), patch(
        current_module + ".lg.PublicAPI", client
    ), patch("geniust.api.GeniusT", client):
        rcr.process_preferences(update, context)


def test_reset_shuffle(update_callback_query, context):
    update = update_callback_query

    res = rcr.reset_shuffle(update, context)

    assert res == constants.END
    context.bot_data["db"].delete_preferences.assert_called_once()


@pytest.mark.parametrize(
    "update",
    [
        pytest.lazy_fixture("update_message"),
        pytest.lazy_fixture("update_callback_query"),
        pytest.lazy_fixture("update_callback_query"),
    ],
)
def test_display_recommendations(update, context):
    context.user_data["preferences"] = Preferences(genres=["pop"], artists=[])

    res = rcr.display_recommendations(update, context)

    assert res == constants.END