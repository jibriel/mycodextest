# Todo 管理

ローカル JSON ファイルに保存する、シンプルな Todo 管理ツールです。
CLI とローカル Web サーバーの両方で利用できます。

## Web サーバーで使う（推奨）

```bash
python3 todo.py serve --host 127.0.0.1 --port 8000
```

ブラウザで `http://127.0.0.1:8000` を開くと、追加・完了・削除を操作できます。

## CLI で使う

```bash
python3 todo.py add "買い物をする"
python3 todo.py list
python3 todo.py done 1
python3 todo.py remove 1
```

`--db` で保存先ファイルを変更できます。

```bash
python3 todo.py --db /tmp/mytodos.json add "テスト"
python3 todo.py --db /tmp/mytodos.json serve --port 8010
```

## テスト

```bash
python3 -m pytest -q
```
