# Tokyo Rain LOFI Generator (MVP)

ローカルPC上で、**スマホ1タップ生成**向けの最小構成を動かせるMVPです。  
FFmpegだけで720pの雨夜LOFIループ動画(MP4)を生成します。

## 機能
- 動画時間選択（1〜60分）
- 雨量調整
- VHS強度調整
- 色味調整（Cool/Neutral/Warm）
- タイトル自動生成
- 5分ループ固定モード
- MP4ダウンロード

## ローカル起動（共通）
```bash
pip install -r requirements.txt
python app.py
```

ブラウザで `http://localhost:8080` を開きます。

## Windowsでの実行手順

### 1. 必要ソフトをインストール
- Python 3.10以上（`python` コマンドが使える状態）
- FFmpeg（`ffmpeg` コマンドが使える状態）

> FFmpegをインストール後、`ffmpeg -version` が通るようにPATHを設定してください。

### 2. プロジェクトフォルダを開く
PowerShellでこのプロジェクトのフォルダへ移動します。

```powershell
cd C:\path\to\tokyo_rain_lofi
```

### 3. 必要コマンド（初回セットアップ）
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. 起動方法
```powershell
python app.py
```

起動後、ブラウザで以下を開いてください。

- `http://localhost:8080`

### 5. 停止方法
PowerShellで `Ctrl + C` を押すと停止できます。

## 備考
- 生成物は `outputs/` に保存されます。
- FFmpegが見つからない場合は、PATH設定後にPowerShellを再起動して再実行してください。

## 今後の拡張
- 1080p切替
- 背景画像/レイヤー差し替え
- BGM差し込み
- プリセット（深夜駅/コンビニ前/路地裏）
