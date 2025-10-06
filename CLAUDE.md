# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリの目的

このリポジトリはカレンダーアプリケーション用の各国の祝日定義を管理しています。以下が含まれます：
- `json/`ディレクトリ内に76カ国の祝日JSONファイル（例：`JP.json`, `US.json`, `DE.json`）
- Google Calendar APIから祝日データを取得・更新するスクリプト

## 祝日データ構造

### JSONファイルフォーマット
各国のJSONファイルは、祝日オブジェクトの配列をコンパクト形式（インデントなし、1行形式）で格納：
```json
[{"date":"2025-01-01T00:00:00.000Z","name":"元日"},{"date":"2025-07-04T00:00:00.000Z","name":"Independence Day"}]
```

**重要な特性：**
- 日付フォーマット: 常に`YYYY-MM-DDTHH:MM:SS.sssZ`（ISO 8601形式、`.000Z`サフィックス付き）
- 祝日名: JPは日本語（`ja`ロケール）、その他の国は英語（`en`ロケール）
- ファイル名: ISO 3166-1 alpha-2の2文字大文字国コード（例：`JP.json`, `US.json`）
- **1行形式**: ファイル全体が改行なしの1行（エディタでは自動折り返しで複数行に見える）
- インデントやフォーマットなし（コンパクトJSON）
- 日付の昇順でソート
- 同じ日付の重複は後のエントリで上書き（通常、英語の祝日名が保持される）

### 言語マッピング
- **JP**: 日本語（例：`元日`, `成人の日`）
- **その他の国**: 英語（例：`New Year's Day`, `Independence Day`）

## セットアップ

### 初回セットアップ
```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows

# 依存関係をインストール（このプロジェクトは標準ライブラリのみ使用）
pip install -r requirements.txt

# Google Calendar API キーを環境変数に設定
export GCAL_API_KEY="YOUR_API_KEY"
```

### 仮想環境の有効化（作業時）
```bash
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows
```

### 仮想環境の無効化
```bash
deactivate
```

## スクリプト

### holidays_gcal_fetch.py
Google Calendar APIから祝日を取得するための参照用スクリプト。APIインターフェースと使用パターンを示しています。

**使用例：**
```bash
source venv/bin/activate
export GCAL_API_KEY="YOUR_API_KEY"
python holidays_gcal_fetch.py --countries JP,US,GB --format json --out holidays.json
```

### update_holidays.py
**主要スクリプト** - 国別祝日JSONファイルを更新します。`json/*.json`から全ての国コードを自動検出します。

**主な機能：**
- `json/`ディレクトリ内の全ての国を自動処理（76カ国対応）
- 既存データに新しい祝日をマージ（日付で重複排除、後のエントリを優先）
- 2つのモード: 追記（デフォルト）または再作成（`--recreate`）
- 国ごとに適切なGoogle Calendarロケールを使用（JP=ja、その他=en）
- SSL証明書検証に`certifi`を使用

**使用例：**
```bash
source venv/bin/activate
export GCAL_API_KEY="YOUR_API_KEY"

# 全ての既存国ファイルに2025-2027年の祝日を追記
python update_holidays.py --start-year 2025 --end-year 2027

# ファイルを再作成（ファイルが存在する場合はエラー）
python update_holidays.py --start-year 2025 --end-year 2027 --recreate

# 強制的に再作成（既存ファイルを上書き）
python update_holidays.py --start-year 2025 --end-year 2027 --recreate --force
```

## Google Calendar API統合

### カレンダーIDパターン
Google Calendarはロケール固有のカレンダーIDを使用：
- 日本（日本語）: `ja.japanese.official#holiday@group.v.calendar.google.com`
- 日本（英語）: `en.japanese.official#holiday@group.v.calendar.google.com`
- USA: `en.usa.official#holiday@group.v.calendar.google.com`
- パターン: `{locale}.{country_name}.official#holiday@group.v.calendar.google.com`

### API認証
- カレンダーは公開されているためAPIキーのみ必要（OAuthは不要）
- `GCAL_API_KEY`環境変数または`--api-key`パラメータで設定
- APIエンドポイント: `https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`

### サポートされている国
`update_holidays.py`スクリプトには76カ国のカレンダーIDを含む`CALENDAR_MAPPING`辞書があります。

**既知のカレンダーIDパターン：**
- 国コード形式: `en.{cc}.official#holiday@group.v.calendar.google.com` (例: `en.ee.official`, `en.rs.official`)
- 国名形式: `en.{country_name}.official#holiday@group.v.calendar.google.com` (例: `en.spain.official`, `en.german.official`)
- エイリアス: `UK` → `GB`（同じカレンダーID）、`YV` → `VE`（ベネズエラ）

**新しい国のサポートを追加する場合：**
1. Google Calendar IDを調べる（curlコマンドで存在確認推奨）
2. `update_holidays.py`の`CALENDAR_MAPPING`にエントリを追加
3. `json/`ディレクトリに初期JSONファイルを作成（ファイル名は2文字大文字国コード）
4. JPを除く全ての国で`en`ロケールを使用（JPは`ja`を使用）

## 開発時の注意事項

### 祝日データを修正する場合
- 正確なJSONフォーマットを維持（コンパクト、インデントなし）
- `.000Z`サフィックス付きのISO 8601日付フォーマットを維持
- ファイルを日付順にソート
- 国ごとに正しい言語を使用（JP=日本語、その他=英語）

### 新しい国を追加する場合
1. その国のGoogle Calendar IDが存在することを確認
2. `update_holidays.py`の`CALENDAR_MAPPING`にマッピングを追加
3. 適切なロケールを決定（日本は`ja`、ほとんどの国は`en`）
4. 空のJSONファイルを作成するか、`--recreate`モードを使用

### スクリプトを更新する場合
- 外部依存: `certifi`のみ（SSL証明書検証用）、その他は標準ライブラリ
- Python 3.6+との互換性を維持
- 既存のエラーハンドリングパターンに従う（stderrへの出力、適切な終了コード）
- HTTPリクエストにはurllibを使用（requestsライブラリは使用しない）

### トラブルシューティング

**SSL証明書エラーが発生する場合：**
```bash
pip install --upgrade certifi
```

**404エラーでカレンダーが見つからない場合：**
```bash
# curlで正しいカレンダーIDを確認
curl "https://www.googleapis.com/calendar/v3/calendars/en.{country}.official%23holiday%40group.v.calendar.google.com/events?key=YOUR_API_KEY&timeMin=2025-01-01T00:00:00Z&timeMax=2025-02-01T00:00:00Z"
```

**JSONファイルがエディタで複数行に見える場合：**
- これは正常です（エディタの自動折り返し機能）
- 実際のファイルは改行なしの1行形式です
