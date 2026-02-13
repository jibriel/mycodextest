#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse

DEFAULT_DB = Path("todos.json")


@dataclass
class Todo:
    id: int
    title: str
    done: bool = False


class TodoStore:
    def __init__(self, path: Path = DEFAULT_DB) -> None:
        self.path = path
        if not self.path.exists():
            self.save([])

    def load(self) -> List[Todo]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [Todo(**item) for item in data]

    def save(self, todos: List[Todo]) -> None:
        payload = [asdict(todo) for todo in todos]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, title: str) -> Todo:
        todos = self.load()
        next_id = max((t.id for t in todos), default=0) + 1
        todo = Todo(id=next_id, title=title)
        todos.append(todo)
        self.save(todos)
        return todo

    def list_all(self) -> List[Todo]:
        return self.load()

    def mark_done(self, todo_id: int) -> Todo:
        todos = self.load()
        for todo in todos:
            if todo.id == todo_id:
                todo.done = True
                self.save(todos)
                return todo
        raise ValueError(f"Todo id={todo_id} が見つかりません")

    def remove(self, todo_id: int) -> None:
        todos = self.load()
        filtered = [t for t in todos if t.id != todo_id]
        if len(filtered) == len(todos):
            raise ValueError(f"Todo id={todo_id} が見つかりません")
        self.save(filtered)


def format_todo(todo: Todo) -> str:
    status = "✅" if todo.done else "⬜"
    return f"{status} [{todo.id}] {todo.title}"


def render_page(todos: List[Todo], message: str = "") -> str:
    total = len(todos)
    completed = sum(1 for t in todos if t.done)
    open_count = total - completed

    todo_items = []
    for todo in todos:
        escaped_title = html.escape(todo.title)
        status_class = "done" if todo.done else "open"
        badge = "完了" if todo.done else "進行中"
        done_form = ""
        if not todo.done:
            done_form = (
                f"<form method='post' action='/done' class='inline-form'>"
                f"<input type='hidden' name='id' value='{todo.id}' />"
                "<button type='submit' class='btn btn-success'>✓ 完了</button>"
                "</form>"
            )

        remove_form = (
            f"<form method='post' action='/remove' class='inline-form'>"
            f"<input type='hidden' name='id' value='{todo.id}' />"
            "<button type='submit' class='btn btn-danger'>🗑 削除</button>"
            "</form>"
        )

        todo_items.append(
            "<li class='todo-card'>"
            f"<div class='todo-main'><span class='todo-id'>#{todo.id}</span>"
            f"<span class='todo-title {status_class}'>{escaped_title}</span>"
            f"<span class='todo-badge {status_class}'>{badge}</span></div>"
            f"<div class='todo-actions'>{done_form}{remove_form}</div>"
            "</li>"
        )

    body = "\n".join(todo_items) if todo_items else "<li class='empty'>🎉 Todo はありません</li>"
    notice = f"<div class='notice'>✨ {html.escape(message)}</div>" if message else ""

    return f"""<!doctype html>
<html lang='ja'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Todo 管理</title>
  <style>
    :root {{
      --bg1: #0f172a;
      --bg2: #1e1b4b;
      --card: rgba(15, 23, 42, 0.62);
      --line: rgba(255,255,255,0.12);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #22d3ee;
      --success: #34d399;
      --danger: #fb7185;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, 'Noto Sans JP', system-ui, sans-serif;
      color: var(--text);
      background: radial-gradient(circle at top right, #312e81 0%, transparent 35%),
                  radial-gradient(circle at bottom left, #0e7490 0%, transparent 30%),
                  linear-gradient(145deg, var(--bg1), var(--bg2));
      display: grid;
      place-items: center;
      padding: 24px;
    }}
    .shell {{
      width: min(900px, 100%);
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      backdrop-filter: blur(14px);
      box-shadow: 0 24px 50px rgba(0, 0, 0, 0.35);
    }}
    h1 {{ margin: 0 0 16px; font-size: 2rem; letter-spacing: 0.02em; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .stat {{ background: rgba(255,255,255,0.06); border: 1px solid var(--line); border-radius: 14px; padding: 10px 12px; }}
    .stat .label {{ color: var(--muted); font-size: 0.8rem; }}
    .stat .value {{ font-size: 1.3rem; font-weight: 700; }}
    .add-form {{ display: flex; gap: 10px; margin-bottom: 12px; }}
    .add-form input {{ flex: 1; background: rgba(255,255,255,0.08); border: 1px solid var(--line); border-radius: 12px; padding: 12px; color: var(--text); outline: none; }}
    .add-form input::placeholder {{ color: #cbd5e1; }}
    .btn {{ border: 0; border-radius: 10px; padding: 9px 12px; font-weight: 600; cursor: pointer; transition: transform .12s ease, opacity .2s ease; }}
    .btn:hover {{ transform: translateY(-1px); opacity: .92; }}
    .btn-primary {{ background: linear-gradient(120deg, #06b6d4, #3b82f6); color: white; }}
    .btn-success {{ background: rgba(52, 211, 153, 0.2); color: #6ee7b7; border: 1px solid rgba(110,231,183,0.35); }}
    .btn-danger {{ background: rgba(251, 113, 133, 0.18); color: #fda4af; border: 1px solid rgba(253,164,175,0.35); }}
    .notice {{ background: rgba(34, 211, 238, 0.18); border: 1px solid rgba(103, 232, 249, 0.45); color: #a5f3fc; padding: 10px 12px; border-radius: 12px; margin-bottom: 12px; }}
    ul {{ list-style: none; margin: 14px 0 0; padding: 0; display: grid; gap: 10px; }}
    .todo-card {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.06); }}
    .todo-main {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .todo-id {{ color: var(--muted); font-family: ui-monospace, monospace; }}
    .todo-title.done {{ text-decoration: line-through; color: #9ca3af; }}
    .todo-badge {{ border-radius: 999px; font-size: .75rem; padding: 2px 9px; border: 1px solid; }}
    .todo-badge.open {{ color: #67e8f9; border-color: rgba(103,232,249,.5); }}
    .todo-badge.done {{ color: #86efac; border-color: rgba(134,239,172,.5); }}
    .todo-actions {{ display: flex; gap: 8px; align-items: center; }}
    .inline-form {{ margin: 0; }}
    .empty {{ text-align: center; color: #d1fae5; border: 1px dashed rgba(167, 243, 208, .5); padding: 14px; border-radius: 12px; background: rgba(167, 243, 208, .08); }}
    @media (max-width: 680px) {{
      .stats {{ grid-template-columns: 1fr; }}
      .todo-card {{ flex-direction: column; align-items: flex-start; }}
      .todo-actions {{ width: 100%; }}
      .add-form {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main class='shell'>
    <h1>Todo 管理</h1>
    <section class='stats'>
      <article class='stat'><div class='label'>合計</div><div class='value'>{total}</div></article>
      <article class='stat'><div class='label'>未完了</div><div class='value'>{open_count}</div></article>
      <article class='stat'><div class='label'>完了</div><div class='value'>{completed}</div></article>
    </section>
    {notice}
    <form method='post' action='/add' class='add-form'>
      <input type='text' name='title' placeholder='次にやることを入力...' required />
      <button type='submit' class='btn btn-primary'>＋ 追加</button>
    </form>
    <ul>
      {body}
    </ul>
  </main>
</body>
</html>
"""


class TodoHandler(BaseHTTPRequestHandler):
    store: TodoStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        params = parse_qs(parsed.query)
        message = params.get("message", [""])[0]
        html_text = render_page(self.store.list_all(), message)
        encoded = html_text.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(payload)

        try:
            if self.path == "/add":
                title = form.get("title", [""])[0].strip()
                if not title:
                    raise ValueError("Todo 内容が空です")
                self.store.add(title)
                self.redirect_with_message("追加しました")
                return

            if self.path == "/done":
                todo_id = int(form.get("id", ["0"])[0])
                self.store.mark_done(todo_id)
                self.redirect_with_message("完了にしました")
                return

            if self.path == "/remove":
                todo_id = int(form.get("id", ["0"])[0])
                self.store.remove(todo_id)
                self.redirect_with_message("削除しました")
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
        except ValueError as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"エラー: {exc}".encode("utf-8"))

    def redirect_with_message(self, message: str) -> None:
        query = urlencode({"message": message}, encoding="utf-8")
        self.redirect(f"/?{query}")

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def create_server(host: str, port: int, db_path: Path) -> ThreadingHTTPServer:
    store = TodoStore(db_path)

    class BoundTodoHandler(TodoHandler):
        pass

    BoundTodoHandler.store = store
    return ThreadingHTTPServer((host, port), BoundTodoHandler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="シンプルな Todo 管理")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Todo 保存先(JSON)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Todo を追加")
    p_add.add_argument("title", help="Todo 内容")

    sub.add_parser("list", help="Todo 一覧を表示")

    p_done = sub.add_parser("done", help="Todo を完了にする")
    p_done.add_argument("id", type=int, help="完了にする Todo ID")

    p_rm = sub.add_parser("remove", help="Todo を削除")
    p_rm.add_argument("id", type=int, help="削除する Todo ID")

    p_serve = sub.add_parser("serve", help="ローカル Web サーバーを起動")
    p_serve.add_argument("--host", default="127.0.0.1", help="バインドするホスト")
    p_serve.add_argument("--port", type=int, default=8000, help="ポート番号")

    return parser


def run_cli(args: argparse.Namespace) -> int:
    store = TodoStore(args.db)
    try:
        if args.command == "add":
            print("追加:", format_todo(store.add(args.title)))
        elif args.command == "list":
            todos = store.list_all()
            if not todos:
                print("Todo はありません")
            for todo in todos:
                print(format_todo(todo))
        elif args.command == "done":
            print("完了:", format_todo(store.mark_done(args.id)))
        elif args.command == "remove":
            store.remove(args.id)
            print(f"削除: [{args.id}]")
    except ValueError as exc:
        print(f"エラー: {exc}")
        return 1
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "serve":
        server = create_server(args.host, args.port, args.db)
        print(f"Todo サーバーを起動しました: http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n停止します")
        finally:
            server.server_close()
        return 0

    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
