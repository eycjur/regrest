# Regrest - 開発ドキュメント

このドキュメントは、Regrest（回帰テストツール）の設計判断と実装の詳細を記載しています。

## プロジェクト概要

**Regrest** は、Python関数の出力を自動的に記録し、後続の実行で検証する回帰テストツールです。

### 主な特徴

- デコレーターベースの簡潔なAPI（`@regrest`）
- 初回実行で自動記録、以降は自動検証
- JSONとPickleのハイブリッドシリアライゼーション
- 浮動小数点数の許容誤差サポート
- CLIツール（`regrest list/delete`）
- 自動`.gitignore`生成
- Python 3.9以上をサポート

## アーキテクチャ

```
regrest/
├── __init__.py     # パッケージエントリーポイント
├── __main__.py     # python -m regrest のエントリーポイント
├── _logging.py     # ロギング設定
├── decorator.py    # @regrest デコレーター
├── storage.py      # ファイルストレージ（JSON/Pickle）
├── matcher.py      # 値の比較ロジック
├── config.py       # グローバル設定
└── cli.py          # CLIコマンド
```

### CLI呼び出し方法

複数の方法でCLIを呼び出せます：

```bash
# 1. pip install後のコマンド（推奨）
regrest list

# 2. モジュールとして実行
python -m regrest list

# 3. 直接実行
python regrest/cli.py list
```

これらはすべて同じ動作をします。pyproject.tomlの`[project.scripts]`で`regrest`コマンドが定義されており、`__main__.py`で`python -m regrest`が可能になっています。

## 設計判断

### 1. デコレーター名: `@regrest`

**選択**: `@regrest`（`@regtest` ではない）

**理由**:
- ツール名との一貫性（パッケージ: `regrest`, CLI: `regrest`, デコレーター: `@regrest`）
- "regression test" → "regrest" の略として自然

### 2. ストレージ形式: JSONとPickleのハイブリッド

**実装**:
```python
def _try_encode(self, value):
    try:
        json.dumps(value)
        return {'type': 'json', 'data': value}
    except (TypeError, ValueError):
        pickled = pickle.dumps(value)
        encoded = base64.b64encode(pickled).decode('ascii')
        return {'type': 'pickle', 'data': encoded}
```

**理由**:
- JSON: 可読性が高く、バージョン間の互換性が良い
- Pickle: カスタムクラスなど複雑なオブジェクトに対応
- 自動フォールバック: ユーザーは意識する必要なし

**トレードオフ**:
- ✅ 柔軟性: ほぼすべてのPythonオブジェクトをサポート
- ❌ Pickleの互換性: Pythonバージョン間で問題が起きる可能性

### 3. 比較アルゴリズム: 詳細な型別比較

**選択**: `repr()` での単純比較ではなく、型ごとの比較ロジック

**理由**:
1. **浮動小数点の許容誤差**
   ```python
   # repr()では失敗
   0.1 + 0.2 == 0.3  # False

   # matcherでは成功（許容誤差内）
   matcher.match(0.3, 0.1 + 0.2)  # True (with tolerance)
   ```

2. **詳細なエラーメッセージ**
   ```python
   # repr()比較
   "Mismatch: expected {...}, got {...}"

   # matcher
   "Value mismatch at user.profile.settings.theme: expected 'dark', got 'light'"
   ```

3. **型の厳密チェック**
   ```python
   # 回帰テストでは型変更も検出したい
   1 == 1.0  # True (Pythonの比較)
   type(1) != type(1.0)  # True (matcherで検出)
   ```

### 4. `.gitignore` の配置: `.regrest/.gitignore`

**選択**: プロジェクトルートではなく、`.regrest/` 内に配置

**実装**:
```
.regrest/
├── .gitignore          # このファイルで全てを無視
├── module.func.abc.json
└── module.func.def.json
```

`.regrest/.gitignore` の内容:
```gitignore
# Ignore all files in this directory
*
```

**理由**:
- ✅ プロジェクトの `.gitignore` を汚さない
- ✅ `.regrest/` ディレクトリ自体は追跡される（存在を示す）
- ✅ ツール固有の設定がツール固有の場所に配置される

**代替案との比較**:
| 方式 | メリット | デメリット |
|------|---------|-----------|
| ルートの `.gitignore` に追加 | シンプル | プロジェクトファイルを変更 |
| `.regrest/.gitignore` で `*` | クリーン | やや複雑 |
| `.regrest/.gitignore` で `* \n !.gitignore` | `.gitignore` も追跡 | 過剰（不要） |

**最終判断**: `.regrest/.gitignore` で全て無視（現在の実装）

### 5. 記録の識別: SHA256ハッシュ

**実装**:
```python
def _generate_id(self):
    args_str = json.dumps(self.args, sort_keys=True, default=str)
    kwargs_str = json.dumps(self.kwargs, sort_keys=True, default=str)
    data = f"{self.module}.{self.function}:{args_str}:{kwargs_str}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]
```

**理由**:
- 同じ関数でも引数が異なれば別の記録
- ハッシュ衝突のリスクは実用上無視できる（SHA256の16文字）
- ファイル名として使用可能

### 6. カスタムクラスの要件: `__eq__` の実装

**要件**:
```python
class Point:
    def __eq__(self, other):  # 必須
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y
```

**理由**:
- Pickleで復元後の比較に必要
- デフォルトの `__eq__` はオブジェクトIDで比較（常にFalse）
- 明示的な実装を要求することで意図を明確化

## パフォーマンス考慮

### ファイルI/O

- **記録時**: ファイル1つ書き込み（追記ではなく新規作成）
- **検証時**: ファイル1つ読み込み
- **最適化**: 読み込みキャッシュは現在未実装（将来の拡張ポイント）

### メモリ使用量

- 記録は全てメモリに展開される
- 大きな戻り値（数GB）には不向き
- **推奨**: テストデータは適度なサイズに保つ

## セキュリティ考慮

### Pickleの使用

**リスク**: Pickleデシリアライズは任意コード実行のリスクあり

**対策**:
- ユーザーが自分で作成した記録のみを読み込む前提
- 信頼できないソースからの記録は読み込まない
- **将来の改善**: 署名やチェックサムの追加を検討

### ファイルパス

- `storage_dir` は相対パスのみサポート（パストラバーサル対策）
- デフォルトは `.regrest/`

## 拡張性

### プラグインシステム（未実装）

将来的に以下を拡張可能にする:
- カスタムシリアライザー
- カスタムマッチャー
- カスタムストレージバックエンド（DB、S3など）

### マッチャーの拡張

現在のマッチャーは以下をサポート:
- プリミティブ型（int, float, str, bool）
- コレクション型（list, tuple, dict, set）
- 再帰的なネスト構造

**拡張ポイント**:
```python
# カスタムマッチャーの例（将来）
@regrest(matcher=CustomMatcher())
def my_function():
    return MyCustomType()
```

## テスト戦略

### テストファイルの構成

```
example.py                   # 基本的な使用例（プロジェクトルート）
tests/
├── __init__.py
├── test_custom_class.py    # カスタムクラスのテスト
└── test_gitignore.py       # .gitignore自動作成のテスト
```

### 開発ツール

- **ビルドシステム**: pyproject.toml (PEP 517/518)
- **パッケージマネージャー**: uv
- **フォーマッター**: ruff (line-length: 88)
- **リンター**: ruff + mypy
- **テスト**: pytest + pytest-cov
- **タスクランナー**: make

### カバレッジ

主要な機能:
- ✅ 基本的な記録・検証
- ✅ カスタムクラスのサポート
- ✅ 許容誤差の設定
- ✅ `.gitignore` の自動作成
- ✅ 環境変数による設定
- ✅ ロギング機能
- ⚠️ エッジケース（今後追加予定）

## 既知の制限事項

1. **非決定的な関数**: ランダム値、タイムスタンプなどには不向き
2. **大きな出力**: メモリに全て展開されるため、巨大なデータには不向き
3. **Pythonバージョン**: Pickleの互換性により、異なるPythonバージョン間で問題が起きる可能性（Python 3.9以上を推奨）
4. **マルチプロセス**: 同時書き込みの競合は未対策

## 今後の改善案

### 短期
- [x] 型ヒントの完全対応（Python 3.9+の新しい構文）
- [x] ruffによるフォーマットとリント
- [x] Makefileによるタスク自動化
- [x] PyPIへの公開
- [ ] エラーメッセージの改善
- [ ] より多くのテストケース
- [ ] CI/CDの完全な導入（GitHub Actions設定済み）

### 中期
- [ ] 記録の差分表示（`regrest diff`）
- [ ] 記録のマージ（`regrest merge`）
- [ ] 読み込みキャッシュの実装
- [ ] カバレッジレポートの改善

### 長期
- [ ] プラグインシステム
- [ ] DBバックエンドのサポート
- [ ] Web UIの提供

## コントリビューション

### 開発ワークフロー

コードを変更した後は、必ず以下のコマンドを実行してください：

```bash
make check
```

このコマンドは以下を順番に実行します：
1. `make format` - ruffでコードをフォーマット
2. `make lint` - ruffとmypyでリント
3. `make test` - pytestでテストを実行

すべてのチェックが通ることを確認してからコミットしてください。

**重要**: タスク完了後は、このCLAUDE.mdを更新してください：
- 設計判断を追加・更新
- アーキテクチャ図を更新
- 開発履歴に変更内容を記録
- 今後の改善案を更新（完了したタスクにチェックマークを付ける）

個別に実行する場合：

```bash
# コードフォーマット
make format

# リント（ruff + mypy）
make lint

# 自動修正付きリント
make lint-fix

# テスト実行
make test

# ビルド
make build

# クリーンアップ
make clean
```

### コーディング規約

- ruff でフォーマット（line-length: 88）
- mypy で型チェック（Python 3.9+）
- Docstring は Google スタイル
- 型ヒントは組み込み型を使用（`dict`, `list`など）

### プルリクエスト

1. 機能追加は issue で議論
2. テストを追加
3. README を更新
4. **CLAUDE.md を更新**（設計判断、アーキテクチャ、開発履歴など）
5. CHANGELOG を更新
6. **必須**: `make check` がすべて通ることを確認

## ライセンス

MIT License

## 開発履歴

### 0.1.0 (2025-01-XX)
- **PyPIへの公開** - `pip install regrest`でインストール可能に
- 初回リリース
- 基本的なデコレーター機能（`@regrest`）
- JSONとPickleのハイブリッドストレージ
- スマートな値比較（浮動小数点の許容誤差サポート）
- CLIツール（`regrest list`, `regrest delete`）
- カスタムクラスのサポート
- 自動`.gitignore`生成
- 環境変数による設定サポート
- カラフルなログ出力
- Python 3.9以上をサポート
- pyproject.tomlベースのビルドシステム
- ruff + mypyによる静的解析
- Makefileによるタスク自動化
- GitHub Actionsによる継続的インテグレーション
