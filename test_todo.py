from pathlib import Path
from threading import Thread
import http.client
from urllib.request import urlopen

from todo import TodoStore, create_server, render_page


def test_add_and_list(tmp_path: Path) -> None:
    db = tmp_path / "todos.json"
    store = TodoStore(db)

    created = store.add("牛乳を買う")

    assert created.id == 1
    assert created.title == "牛乳を買う"
    assert created.done is False
    assert store.list_all()[0].title == "牛乳を買う"


def test_done_and_remove(tmp_path: Path) -> None:
    db = tmp_path / "todos.json"
    store = TodoStore(db)
    first = store.add("A")
    second = store.add("B")

    done = store.mark_done(first.id)
    assert done.done is True

    store.remove(second.id)
    remaining = store.list_all()
    assert len(remaining) == 1
    assert remaining[0].id == first.id


def test_render_page_includes_title() -> None:
    html = render_page([])
    assert "Todo 管理" in html
    assert "Todo はありません" in html


def test_web_server_add_and_list(tmp_path: Path) -> None:
    db = tmp_path / "web_todos.json"
    server = create_server("127.0.0.1", 0, db)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request(
            "POST",
            "/add",
            body="title=web%E3%83%86%E3%82%B9%E3%83%88",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = conn.getresponse()
        assert response.status == 303
        conn.close()

        with urlopen(f"http://127.0.0.1:{port}/") as response:
            body = response.read().decode("utf-8")
            assert "webテスト" in body
    finally:
        server.shutdown()
        server.server_close()


def test_redirect_location_is_url_encoded_for_japanese_message(tmp_path: Path) -> None:
    db = tmp_path / "redirect_todos.json"
    server = create_server("127.0.0.1", 0, db)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request(
            "POST",
            "/add",
            body="title=%E5%88%86%E6%9E%90%E3%82%92%E4%BD%9C%E6%88%90",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = conn.getresponse()
        assert response.status == 303
        location = response.getheader("Location")
        assert location is not None
        assert "%E8%BF%BD%E5%8A%A0%E3%81%97%E3%81%BE%E3%81%97%E3%81%9F" in location
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
