# 縄文土器修復プロジェクト (Jomon Pottery Reconstruction)

AIを用いて、物理シミュレーションで破壊された土器の破片を自動で繋ぎ合わせ、復元するプロジェクトです。

## ディレクトリ構造

### 📂 /datasets
AI学習用のデータセットを格納します。
- `dataset_test_v1/`: 初回の検証で生成した30破片の点群データ。

### 📂 /archives
過去の実験的スクリプトや、古いバージョンのロジックを格納しています。

### 🐍 メインスクリプト
- `visualize_adjacency_dynamic.py`: **[最重要]** 多方向から破片を繋ぐ接合線をリアルタイムに描画します。Blender起動時に実行してください。
- `facet_segmentation_v6_majority.py`: 最新の断面分割アルゴリズム（多数決＆平滑化）です。
- `export_shards_data.py`: 現在のシーンからAI用の学習データ（点群JSON）を書き出します。

### 🎨 Blenderファイル
- `Jomon_Pottery_Base.blend`: 現在のメイン作業ファイルです。

## 使い方
1. Blenderを開き、`Jomon_Pottery_Base.blend` をロードします。
2. `visualize_adjacency_dynamic.py` をテキストエディタで開き、実行（Run Script）すると、接合線が動的に表示されます。
