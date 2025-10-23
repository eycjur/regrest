# Regrest

[English](README.md) | [日本語](README_ja.md)

**Regrest** は、Pythonのためのシンプルで強力な回帰テストツールです。初回実行時に関数の出力を自動的に記録し、その後の実行で検証します。

## 特徴

- 🎯 **シンプルなデコレーターAPI** - 関数に `@regrest` を追加するだけ
- 📝 **自動記録** - 初回実行で出力を記録、その後の実行で検証
- 🔍 **スマートな比較** - float、dict、list、ネストした構造を適切に処理
- 🛠 **CLIツール** - テスト記録の一覧表示、確認、削除が可能
- ⚙️ **カスタマイズ可能** - 許容誤差、保存場所などを設定可能
- 🔧 **自動.gitignore** - 初回実行時に `.regrest/.gitignore` を自動作成してテスト記録を除外

## 要件

- Python 3.9 以上

## インストール

```bash
# uvを使用（推奨）
uv sync --all-extras

# またはpipを使用
pip install -e .
```

## 開発

このプロジェクトは `make` を使用して開発タスクを実行します：

```bash
# 利用可能なコマンド一覧を表示
make help

# 依存関係をインストール
make install

# コードをフォーマット
make format

# リンターを実行
make lint

# リンターを実行し自動修正
make lint-fix

# テストを実行
make test

# すべてのチェックを実行（format + lint + test）
make check

# 生成されたファイルをクリーンアップ
make clean

# サンプルを実行
make example
```

## サンプルの実行

```bash
# 基本的な使用例
python tests/example.py

# カスタムクラスのテスト
python tests/test_custom_class.py

# .gitignore自動作成のテスト
python tests/test_gitignore.py
```

## クイックスタート

### 基本的な使い方

```python
from regrest import regrest

@regrest
def calculate_price(items, discount=0):
    total = sum(item['price'] for item in items)
    return total * (1 - discount)

# 初回実行：結果を記録
items = [{'price': 100}, {'price': 200}]
result = calculate_price(items, discount=0.1)  # 270.0を返し、記録
# 出力: [regrest] Recorded: __main__.calculate_price (id: abc123...)

# 2回目以降：記録と比較
result = calculate_price(items, discount=0.1)  # 270.0を返し、記録と比較
# 出力: [regrest] Passed: __main__.calculate_price (id: abc123...)
```

### カスタム許容誤差

```python
@regrest(tolerance=1e-6)
def calculate_pi():
    return 3.14159265359
```

### 更新モード

既存の記録をテストではなく更新する場合：

```python
@regrest(update=True)
def my_function():
    return "new result"
```

または環境変数を使用：

```bash
REGREST_UPDATE_MODE=1 python your_script.py
```

## 環境変数

Regrestは環境変数による設定をサポートしています：

- `REGREST_LOG_LEVEL` - ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `REGREST_RAISE_ON_ERROR` - テスト失敗時に例外を投げる (true/false, 1/0)
- `REGREST_UPDATE_MODE` - すべての記録を更新 (true/false, 1/0)
- `REGREST_STORAGE_DIR` - カスタムストレージディレクトリ
- `REGREST_FLOAT_TOLERANCE` - 浮動小数点の許容誤差 (例: 1e-6)

使用例：

```bash
# デバッグログを有効にして実行
REGREST_LOG_LEVEL=DEBUG python your_script.py

# すべての記録を更新
REGREST_UPDATE_MODE=1 python your_script.py

# 厳密モード（エラーで例外を投げる）
REGREST_RAISE_ON_ERROR=true python your_script.py

# カスタムストレージと許容誤差
REGREST_STORAGE_DIR=.test_records REGREST_FLOAT_TOLERANCE=1e-6 python your_script.py
```

**優先順位**: コンストラクタ引数 > 環境変数 > デフォルト値

## CLI使用方法

CLIは複数の方法で呼び出せます：

```bash
# pip install -e . の後
regrest list

# または python -m を使用
python -m regrest list

# または直接実行
python regrest/cli.py list
```

### すべてのテスト記録を一覧表示

```bash
# すべての記録を表示
regrest list

# キーワードで絞り込み
regrest list -k calculate
regrest list -k __main__
```

出力例：
```
Found 2 test record(s):

__main__:
  calculate_price()
    ID: abc123def456
    Arguments:
      args[0]: [{'price': 100}, {'price': 200}]
      discount: 0.1
    Result:
      270.0
    Recorded: 2024-01-15T10:30:00
```

### 記録の削除

```bash
# IDで削除
regrest delete abc123

# パターンで削除
regrest delete --pattern "mymodule.*"

# すべての記録を削除
regrest delete --all
```

### カスタム保存ディレクトリ

```bash
regrest --storage-dir=.my_records list
```

## 仕組み

1. **初回実行**: `@regrest` でデコレートされた関数を呼び出すと、通常通り実行され、以下を保存します：
   - モジュール名と関数名
   - 引数（位置引数とキーワード引数）
   - 戻り値
   - タイムスタンプ

   記録は `.regrest/` ディレクトリにJSONファイルとして保存されます。

2. **その後の実行**: 同じ引数で次回呼び出すと：
   - 関数が実行される
   - 結果が記録された値と比較される
   - 一致する → テスト成功 ✅
   - 一致しない → `RegressionTestError` が発生 ❌

3. **更新モード**: 期待値を更新する必要がある場合：
   - `@regrest(update=True)` または `REGREST_UPDATE=1` を使用
   - 古い記録が新しい結果で置き換えられる

## 設定

### グローバル設定

```python
from regrest import Config, set_config

config = Config(
    storage_dir='.my_records',
    float_tolerance=1e-6,
)
set_config(config)
```

### 関数ごとの設定

```python
@regrest(tolerance=1e-9)
def precise_calculation():
    return 3.141592653589793
```

## 高度な機能

### 比較ロジック

マッチャーは以下を賢く比較します：
- **プリミティブ型**: 文字列、真偽値は厳密一致
- **数値**: floatは許容誤差あり、整数は厳密一致
- **コレクション**: リスト、辞書、セットの深い比較
- **ネストした構造**: 詳細なエラーメッセージ付きの再帰的比較

### 記録の識別

記録は以下で識別されます：
- モジュール名
- 関数名
- 引数のSHA256ハッシュ（先頭16文字）

つまり、引数の組み合わせが異なると別々の記録が作成されます。

## 使用例

### 例1: データ処理

```python
from regrest import regrest

@regrest
def process_data(data):
    # 複雑なデータ変換
    result = {
        'mean': sum(data) / len(data),
        'max': max(data),
        'min': min(data),
    }
    return result

# 初回実行で結果を記録
stats = process_data([1, 2, 3, 4, 5])

# 将来の実行で結果が変わっていないことを検証
stats = process_data([1, 2, 3, 4, 5])  # 記録された値と一致する必要あり
```

### 例2: APIレスポンス

```python
@regrest
def format_user_response(user):
    return {
        'id': user['id'],
        'name': f"{user['first_name']} {user['last_name']}",
        'email': user['email'].lower(),
    }

user_data = {
    'id': 123,
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'JOHN@EXAMPLE.COM',
}

# 記録: {'id': 123, 'name': 'John Doe', 'email': 'john@example.com'}
response = format_user_response(user_data)
```

### 例3: 数値計算

```python
import math

@regrest(tolerance=1e-10)
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# 浮動小数点計算を許容誤差付きで検証
distance = calculate_distance(0, 0, 3, 4)  # 5.0のはず
```

### 例4: カスタムクラス

```python
class Point:
    """カスタムクラスの例."""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        """等価性の定義が必須."""
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        """エラーメッセージ用（推奨）."""
        return f"Point({self.x}, {self.y})"


@regrest
def calculate_midpoint(p1, p2):
    """カスタムクラスを返す関数."""
    return Point(
        (p1.x + p2.x) / 2,
        (p1.y + p2.y) / 2,
    )

# カスタムクラスはpickleで保存される
result = calculate_midpoint(Point(0, 0), Point(10, 10))
```

**カスタムクラスの要件**：
- ✅ Pickleでシリアライズ可能であること
- ✅ `__eq__` メソッドを実装すること（比較のため）
- ✅ `__repr__` メソッドの実装を推奨（わかりやすいエラーメッセージのため）

## 保存形式

記録は `.regrest/` ディレクトリにJSONファイルとして保存されます：

```
.regrest/
├── mymodule.calculate_price.abc123def456.json
└── mymodule.process_data.789ghi012jkl.json
```

各ファイルの内容（JSONシリアライズ可能なデータの場合）：
```json
{
  "module": "mymodule",
  "function": "calculate_price",
  "args": {
    "type": "json",
    "data": [[{"price": 100}, {"price": 200}]]
  },
  "kwargs": {
    "type": "json",
    "data": {"discount": 0.1}
  },
  "result": {
    "type": "json",
    "data": 270.0
  },
  "timestamp": "2024-01-15T10:30:00.123456",
  "record_id": "abc123def456"
}
```

カスタムクラスなどJSONシリアライズできないデータの場合：
```json
{
  "module": "mymodule",
  "function": "calculate_midpoint",
  "args": {
    "type": "pickle",
    "data": "gASVNAAAAAAAAACMCF9fbWFpbl9flIwFUG9pbnSUk5QpgZR9lCiMAXiUSwCMAXmUSwB1Yi4="
  },
  "result": {
    "type": "pickle",
    "data": "gASVNgAAAAAAAACMCF9fbWFpbl9flIwFUG9pbnSUk5QpgZR9lCiMAXiURwAUAAAAAAAAjAF5l..."
  },
  "timestamp": "2024-01-15T10:30:00.123456",
  "record_id": "def456ghi789"
}
```

**エンコーディング方式**：
- JSONシリアライズ可能 → そのまま保存
- JSONシリアライズ不可 → Pickleでシリアライズ + Base64エンコード

## ベストプラクティス

1. **バージョン管理**:
   - **自動除外**: 初回実行時に `.regrest/.gitignore` が自動作成され、テスト記録が除外されます
   - **チーム共有**: チーム全体で記録を共有したい場合は、`.regrest/.gitignore` を削除してください
   - **ディレクトリ自体は追跡**: `.regrest/` ディレクトリは追跡されますが、中のファイル（テスト記録）は無視されます

2. **決定的な関数**: `@regrest` は決定的な出力を持つ関数（同じ入力 → 同じ出力）で使用

3. **更新ワークフロー**: 意図的に動作を変更する場合：
   ```bash
   # 変更を確認してから記録を更新
   REGREST_UPDATE=1 python your_script.py
   ```

4. **選択的テスト**: パターンを使って特定のモジュールをテスト：
   ```bash
   regrest delete --pattern "old_module.*"  # 古いテストを削除
   ```

## 制限事項

- **非決定的な関数**: ランダムな出力、タイムスタンプなどを含む関数には `@regrest` を使用しない
- **大きな出力**: 非常に大きな戻り値は保存ファイルが扱いにくくなる可能性がある
- **Pythonバージョン**: Python 3.9以上が必要
- **シリアライズ**:
  - 引数と戻り値はJSONまたはPickleでシリアライズ可能である必要がある
  - カスタムクラスは `__eq__` メソッドが必須（比較のため）
  - Pickleを使用するとPythonバージョン間の互換性に注意が必要

## コントリビューション

コントリビューションを歓迎します！Pull Requestをお気軽に送信してください。

送信前に以下を確認してください：
1. `make check` を実行してすべてのテストとリンターが通ることを確認
2. 新機能にはテストを追加
3. 必要に応じてドキュメントを更新

## ライセンス

MIT License

## 変更履歴

### 0.1.0（初回リリース）
- コアデコレーター機能（`@regrest`）
- JSON/Pickleハイブリッドストレージシステム
- 浮動小数点許容誤差付きスマート比較
- CLIツール（`regrest list`, `regrest delete`）
- カスタムクラスのサポート
- 自動`.gitignore`生成
- 環境変数による設定
- カラフルなログ出力
- Python 3.9以上をサポート
- pyproject.tomlベースのビルドシステム
- ruff + mypyによる静的解析
- Makefileによるタスク自動化
- GitHub Actions CI/CD
