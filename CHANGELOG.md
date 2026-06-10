# 変更履歴

[日本語](CHANGELOG.md) / [English](CHANGELOG.EN.md) / [中文](CHANGELOG.ZH.md) / [한국어](CHANGELOG.KR.md)

## v3.0.0

### 追加

- 起動時に `Brand.png` をフェードイン / フェードアウトで表示するスプラッシュ表示を追加
- `Brand.png` を README の上部に表示
- 最新スクリーンショットを README に反映
- `Brand.png` をアプリ資産として同梱

### 変更

- README を最新機能に合わせて全面的に整理
- 日本語、英語、中国語、韓国語の README を更新
- 日本語、英語、中国語、韓国語の CHANGELOG を更新
- PyInstaller ビルド例に `--add-data` を追加し、画像資産を同梱しやすく変更
- バージョン番号を `v3.0.0` に更新

### 確認

- Python 構文チェックを実施
- ZIP 整合性チェックを実施

## v2.3.0

- lightmode 適用時の配色を修正
- DesktopNaotu に `.km` ファイルを渡して開く処理を修正

## v2.2.0

- 「木閲覧」の選択方式を改善
- 「フォルダ木生成」を追加
- ディスク情報表示時のローディング表示を追加
- ログサイズ表示を追加

## v2.1.0

- ログ機能を追加
- Doughnut Chart 表示を追加
- マインドマップ出力設定を拡張

## v2.0.0

- GUI の多言語切り替えを追加
- darkmode / lightmode 切り替えを追加
- README / CHANGELOG / LICENSE 関連ファイルを多言語化

## v1.x

- ディスク一覧表示、`.km` 出力、DesktopNaotu 連携、設定管理、ファイル分析などの基本機能を実装
