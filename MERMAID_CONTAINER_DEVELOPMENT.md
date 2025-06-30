# Mermaidコンテナによるシステムグラフ描画機能開発方針

## 概要

Mochimakiプロジェクトに、既存の`output_mermaid.txt`ファイルからシステムグラフを描画する機能を追加します。この機能は、[Mermaid.js](https://github.com/mermaid-js/mermaid)を使用したDockerコンテナを利用して実装します。

## 開発目標

1. **ローカル描画機能**: [mermaid.live](https://mermaid.live/)と同等の機能をローカルで実現
2. **Fletアプリ統合**: 既存のMochimakiアプリケーションに描画機能を統合
3. **リアルタイム更新**: システム構成の変更時に自動的にグラフを更新
4. **インタラクティブ操作**: グラフのズーム、パン、ノード選択などの操作をサポート

## 技術スタック

### バックエンド
- **Mermaid.js**: グラフ描画エンジン
- **Node.js**: Mermaid.jsの実行環境
- **Docker**: コンテナ化された描画サービス
- **Express.js**: Webサーバー（グラフ表示用）

### フロントエンド
- **HTML/CSS/JavaScript**: グラフ表示とカスタムインタラクティブ操作
- **Webブラウザ**: グラフ表示ウィンドウ
- **Flet**: 既存のUIフレームワーク（ボタンクリックのみ）
- **SVG操作**: カスタムズーム・パン・選択機能

## アーキテクチャ設計

### 1. Mermaidコンテナ
```
mermaid-container/
├── Dockerfile
├── package.json
├── server.js (Webサーバー)
├── public/
│   ├── index.html (グラフ表示ページ)
│   ├── style.css
│   ├── script.js (インタラクティブ機能)
│   └── viewer.html (専用ビューワー)
└── README.md
```

### 2. 統合アーキテクチャ
```
Mochimaki App (Flet)
    ↓ ボタンクリック → ブラウザ起動
Mermaid Container (Node.js + Mermaid.js + Web UI)
    ↓ HTTP通知 (ファイル内容送信)
output_mermaid.txt
    ↓ リアルタイム描画処理
インタラクティブグラフ表示
```

## グラフ表示方式の設計

### 表示主体: Mermaidコンテナ
**理由**:
- 複雑なシステムグラフの拡大・縮小・パン操作が必要
- インタラクティブな操作（ノード選択、ツールチップ等）
- Mochimakiプロジェクトの肥大化を避ける
- 専門的なグラフ表示機能を独立して管理

### 表示方法: Webブラウザ + カスタムインタラクティブ機能
**実装方式**:
1. Mochimaki側で「システムグラフ表示」ボタンをクリック
2. デフォルトブラウザでMermaidコンテナのURLを開く
3. Mermaid.jsでSVG形式のグラフを生成
4. カスタムJavaScriptでインタラクティブ機能を追加
5. `output_mermaid.txt`の変更をリアルタイムで監視・反映

### インタラクティブ機能の実装
**実装方式**:
- **SVGベース**: Mermaid.jsでSVG形式を生成し、カスタム操作を追加
- **ズーム・パン**: カスタムJavaScriptでマウス・タッチ操作を実装
- **ノード選択**: SVG要素のクリックイベントでハイライト機能
- **ツールチップ**: ノードホバー時に詳細情報を表示
- **検索機能**: ノード名での検索・ハイライト

### リアルタイム更新機能
**実装方式**:
- **分離された通知**: `auto_generate_mermaid_file`関数の呼び出し後に別関数でMermaidコンテナにHTTP通知
- **WebSocket**: ブラウザとコンテナ間のリアルタイム通信
- **即座反映**: ファイル生成完了と同時にグラフ更新

## 実装フェーズ

### Phase 1: Mermaidコンテナの基本実装
**目標**: 基本的な描画機能とWeb UIを実現

**タスク**:
1. Mermaid.jsコンテナの作成
   - DockerfileでNode.js + Mermaid.js環境を構築
   - Express.js Webサーバーを実装
   - 基本的なグラフ表示ページを作成

2. 通知受信機能
   - `POST /api/update`エンドポイントでファイル更新通知を受信
   - ファイル読み込み機能
   - エラーハンドリング

3. 基本的なWeb UI
   - グラフ表示ページ
   - 基本的なズーム・パン機能
   - レスポンシブデザイン

**成果物**:
- 動作するMermaidコンテナ
- 基本的なWeb UI
- 通知受信機能

### Phase 2: Fletアプリとの統合
**目標**: Mochimakiアプリからブラウザ起動機能を統合

**タスク**:
1. コンテナ管理機能の追加
   - コンテナの起動/停止
   - ポート管理
   - ヘルスチェック

2. Flet UI統合
   - 「システムグラフ表示」ボタンの機能実装
     - ボタンクリック時、Mochimakiアプリはdocker-compose psコマンドの出力から全コンテナ情報を取得し、Mermaidコンテナ（コンテナ名: "mochimaki-mermaid-system-graph-viewer"）のポート情報を動的に特定する。
     - Mermaidコンテナの内部ポート（8080）に対応するホスト側ポート番号を抽出し、
       `http://localhost:{ホストポート}` のURLを生成する。
     - そのURLをデフォルトブラウザで開き、MermaidコンテナのWeb UIにアクセスする。
     - ポート番号が固定でない場合も、常に最新の割当ポートでアクセス可能。
     - ポート情報取得やブラウザ起動処理は`on_open_browser_click`等の関数で実装。
   - ブラウザ起動機能
   - エラーハンドリング

3. 通知機能の統合
   - `notify_mermaid_container`関数を新規作成
   - `auto_generate_mermaid_file`呼び出し後に通知関数を実行
   - MermaidコンテナへのHTTP通知
   - エラー時のフォールバック

**成果物**:
- Mochimakiアプリからのブラウザ起動
- リアルタイム更新機能
- エラーハンドリング

### Phase 3: 高度な機能実装
**目標**: インタラクティブな操作とエクスポート機能

**タスク**:
1. インタラクティブ機能
   - **SVGベースのズーム・パン**: カスタムJavaScriptでマウス・タッチ操作を実装
   - **ノード選択・ハイライト**: SVG要素のクリックイベントでハイライト機能
   - **ツールチップ表示**: ノードホバー時に詳細情報を表示
   - **検索機能**: ノード名での検索・ハイライト
   - **垂直・水平移動**: 全方向のパン操作をサポート

2. エクスポート機能
   - PNG形式での保存（高解像度対応）
   - SVG形式での保存（ベクター形式）
   - PDF形式での保存
   - クリップボードへのコピー

3. 設定機能
   - テーマ選択（Mermaid.jsの組み込みテーマ）
   - レイアウト調整
   - カスタマイズオプション
   - 表示設定の保存

**成果物**:
- 完全なインタラクティブ機能（カスタム実装）
- 多形式エクスポート
- カスタマイズ可能な設定

## ファイル構造

### 新規作成ファイル
```
mermaid-container/
├── Dockerfile
├── package.json
├── server.js
├── public/
│   ├── index.html (グラフ表示ページ)
│   ├── style.css
│   ├── script.js (インタラクティブ機能)
│   └── viewer.html (専用ビューワー)
└── README.md

utils/
├── mermaid_container_manager.py (新規)
├── graph_viewer.py (新規)
└── mermaid_notifier.py (新規) - 通知機能専用

Mochimaki.py (既存ファイルの修正)
```

### 修正ファイル
- `utils/ui_utils.py`: 通知機能の統合
- `utils/system_graph_viewer.py`: 通知機能の追加
- `Mochimaki.py`: UI統合

## 関数設計

### 既存関数（変更なし）
```python
def auto_generate_mermaid_file():
    """システム構成のMermaidファイルを自動生成する"""
    # ファイル生成のみに特化
    # 通知機能は含まない
```

### 新規関数
```python
def notify_mermaid_container():
    """Mermaidコンテナにファイル更新を通知する"""
    # output_mermaid.txtの内容を読み込み
    # HTTP POSTでファイル内容を送信
    # コンテナ側で受信して処理
    # エラーハンドリング
    # フォールバック機能

def update_apps_card_with_notification():
    """アプリケーションカードを更新し、Mermaidコンテナに通知する"""
    # update_apps_card()を呼び出し
    # auto_generate_mermaid_file()を呼び出し
    # notify_mermaid_container()を呼び出し
```

## ファイルアクセス方式

### 実装方式: HTTPリクエストによるファイル内容送信
**理由**:
- コンテナの独立性を保つ
- セキュリティリスクを回避
- シンプルな実装
- 移植性が高い

**実装詳細**:
1. `notify_mermaid_container()`で`output_mermaid.txt`の内容を読み込み
2. HTTP POSTリクエストでファイル内容をMermaidコンテナに送信
3. コンテナ側で受信した内容を処理してグラフを描画

**API仕様**:
```javascript
POST /api/update
{
  "mermaid_content": "%%{init: {'theme': 'dark'}}%%\ngraph TD\n    A[Start] --> B[End]",
  "file_path": "/path/to/output_mermaid.txt",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## API設計

### MermaidコンテナAPI
```javascript
// Web UI エンドポイント
GET /                    // メインのグラフ表示ページ
GET /viewer             // 専用ビューワーページ
GET /api/graph          // 現在のグラフデータ取得
GET /api/health         // ヘルスチェック

// 通知エンドポイント
POST /api/update        // ファイル更新通知
{
  "mermaid_content": "%%{init: {'theme': 'dark'}}%%\ngraph TD\n    A[Start] --> B[End]",
  "file_path": "/path/to/output_mermaid.txt",
  "timestamp": "2024-01-01T12:00:00Z"
}

// WebSocket エンドポイント
WS /ws/graph-updates    // リアルタイム更新通知
```

### 通知API
```javascript
// ファイル更新通知
{
  "type": "file_updated",
  "file_path": "/path/to/output_mermaid.txt",
  "timestamp": "2024-01-01T12:00:00Z"
}

// エラー通知
{
  "type": "error",
  "message": "ファイル読み込みエラー",
  "details": "..."
}
```

## エラーハンドリング

### 想定されるエラー
1. **コンテナ起動失敗**: Docker環境の問題
2. **ファイル読み込みエラー**: `output_mermaid.txt`が存在しない
3. **描画エラー**: Mermaidテキストの構文エラー
4. **ネットワークエラー**: コンテナとの通信失敗

### エラー対応
- ユーザーフレンドリーなエラーメッセージ
- 自動リトライ機能
- フォールバック機能（外部ブラウザでの表示）

## パフォーマンス考慮事項

### 最適化戦略
1. **キャッシュ機能**: 同じMermaidテキストの再描画を避ける
2. **非同期処理**: 描画処理をバックグラウンドで実行
3. **リソース管理**: コンテナのメモリ使用量を監視
4. **レンダリング最適化**: 大きなグラフの段階的描画

## セキュリティ考慮事項

### セキュリティ対策
1. **入力検証**: Mermaidテキストの構文チェック
2. **リソース制限**: コンテナのCPU・メモリ制限
3. **ネットワーク分離**: 必要最小限のポート開放
4. **ファイルアクセス制限**: 指定されたディレクトリのみアクセス可能

## テスト戦略

### テスト項目
1. **単体テスト**: 各コンポーネントの動作確認
2. **統合テスト**: コンテナとFletアプリの連携確認
3. **パフォーマンステスト**: 大きなグラフの描画性能
4. **エラーテスト**: 異常系の動作確認

### テスト環境
- ローカル開発環境
- Docker環境
- 異なるOS環境（Windows, Linux, macOS）

## デプロイメント

### 開発環境
- ローカルDocker環境
- 手動でのコンテナ起動
- デバッグモードでの実行

### 本番環境
- 自動コンテナ管理
- ヘルスチェック機能
- ログ監視機能

## 今後の拡張可能性

### 機能拡張
1. **複数グラフ対応**: 複数のシステム構成図の管理
2. **履歴機能**: グラフの変更履歴の保存
3. **共有機能**: グラフのURL共有
4. **テンプレート機能**: よく使うグラフパターンの保存

### 技術拡張
1. **WebSocket対応**: リアルタイム更新
2. **PWA対応**: オフライン動作
3. **モバイル対応**: レスポンシブデザイン

## 参考資料

- [Mermaid.js GitHub](https://github.com/mermaid-js/mermaid)
- [Mermaid Live Editor](https://mermaid.live/)
- [Mermaid Documentation](https://mermaid.js.org/)
- [Flet Documentation](https://flet.dev/docs/)

## 開発スケジュール

### Week 1: Phase 1
- Mermaidコンテナの基本実装
- 基本的なAPIエンドポイント

### Week 2: Phase 2
- Fletアプリとの統合
- 基本的なUI実装

### Week 3: Phase 3
- インタラクティブ機能
- エクスポート機能

### Week 4: テスト・調整
- 総合テスト
- パフォーマンス調整
- ドキュメント整備

---

**注意**: このドキュメントは開発方針の概要です。実際の実装時には、技術的な詳細やAPI仕様をさらに詳細に定義する必要があります。 

**注意**: `mochimaki-mermaid-system-graph-viewer`コンテナはMochimaki.pyの実行時に常住するため、`project_info.json`への記載は不要です。このコンテナはMochimakiアプリケーションの一部として管理され、システムグラフ表示機能を提供します。 