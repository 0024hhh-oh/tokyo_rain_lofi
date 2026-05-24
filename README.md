# Tokyo Rain LOFI Generator (MVP)

Replit上で動く、**スマホ1タップ生成**向けの最小構成です。  
FFmpegだけで720pの雨夜LOFIループ動画(MP4)を生成します。

## 機能
- 動画時間選択（1〜60分）
- 雨量調整
- VHS強度調整
- 色味調整（Cool/Neutral/Warm）
- タイトル自動生成
- 5分ループ固定モード
- MP4ダウンロード

## 起動
```bash
pip install -r requirements.txt
python app.py
```

ブラウザで `http://localhost:8080` を開きます。

## Replit向けメモ
- `run` コマンドを `python app.py` に設定
- FFmpegが有効な環境で実行
- 生成物は `outputs/` に保存

## 今後の拡張
- 1080p切替
- 背景画像/レイヤー差し替え
- BGM差し込み
- プリセット（深夜駅/コンビニ前/路地裏）
