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

## Windowsでの実行手順（初心者向け・PowerShell）

以下は **そのまま上から順に** 実行してください。  
（`PS C:\...>` のような表示はプロンプトなので、コマンド部分だけ入力すればOKです）

### ステップ 1: PowerShell を開く
- スタートメニューで「PowerShell」と検索して開きます。

### ステップ 2: このプロジェクトのフォルダに移動
> 例: デスクトップに置いた場合

```powershell
cd $HOME\Desktop\tokyo_rain_lofi
```

> 例: Cドライブ直下に置いた場合

```powershell
cd C:\tokyo_rain_lofi
```

### ステップ 3: Python が使えるか確認
```powershell
python --version
```

- `Python 3.10` 以上が表示されればOKです。
- エラーが出る場合はPythonをインストールして、PowerShellを開き直してください。

### ステップ 4: FFmpeg が使えるか確認
```powershell
ffmpeg -version
```

- バージョン情報が表示されればOKです。
- エラーが出る場合はFFmpegをインストールし、PATH設定後にPowerShellを再起動してください。

### ステップ 5: 仮想環境を作成（初回のみ）
```powershell
python -m venv .venv
```

### ステップ 6: 仮想環境を有効化
```powershell
.\.venv\Scripts\Activate.ps1
```

- 成功すると先頭に `(.venv)` が付きます。

### ステップ 7: 必要ライブラリをインストール
```powershell
pip install -r requirements.txt
```

### ステップ 8: アプリを起動
```powershell
python app.py
```

### ステップ 9: ブラウザで開く
- 次のURLにアクセスします:
  - `http://localhost:8080`

### ステップ 10: 停止する
- PowerShellに戻って `Ctrl + C` を押します。

---

## よくあるつまずき

### 実行ポリシーで `Activate.ps1` が止められる
次を実行してから、再度アクティベートしてください。

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

その後:

```powershell
.\.venv\Scripts\Activate.ps1
```

### `ffmpeg` が見つからない
- FFmpegをインストール
- 環境変数 PATH に `ffmpeg.exe` のあるフォルダを追加
- PowerShellを再起動して再実行

## 備考
- 生成物は `outputs/` に保存されます。

## 今後の拡張
- 1080p切替
- 背景画像/レイヤー差し替え
- BGM差し込み
- プリセット（深夜駅/コンビニ前/路地裏）

## 生成エラー対策（2026-05 更新）
- `filter_complex` を安定化した最小構成に変更し、まず**確実に1分MP4を生成**する動作にしています。
- 雨/VHSは簡略化済みです（クラッシュ回避優先）。
- 出力先 `outputs/` は生成時にも毎回 `mkdir` して作成保証しています。
- 失敗時は PowerShell のログ出力に加え、ブラウザ画面にも詳細エラーが表示されます。

## Windowsローカルで再起動して生成確認する手順
1. 実行中のサーバーを停止（`Ctrl + C`）。
2. 必要なら仮想環境を再有効化：
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. アプリ再起動：
   ```powershell
   python app.py
   ```
4. ブラウザで `http://localhost:8080` を開き直し（可能なら `Ctrl + F5` で強制再読み込み）。
5. 「🎬 生成する」を押し、1分MP4が `outputs\` に作成されることを確認。
6. 失敗した場合は、
   - PowerShellの `[FFMPEG][STDERR]` ログ
   - ブラウザの「エラー詳細」欄
   の両方を確認してください。

## 真っ暗・無音を防ぐ最低テスト条件（必須）
- 1分（`duration_min=1`）で生成し、次を満たすこと。
  - 映像: 暗い東京夜景風の背景（グラデーション + 建物光 + 薄いVHSノイズ）が見える。
  - 文字: `Tokyo Rain LOFI` が画面上部に表示される。
  - 音声: サイン波だけでなく、低音量の雨音風ノイズが重なって聞こえる。
- 生成完了後、ブラウザに `MP4をダウンロード` リンクが表示され、`/download/<filename>.mp4` にアクセスできること。
- 目視・聴取確認の推奨手順
  1. 生成したMP4を再生して冒頭10秒で黒一色でないことを確認。
  2. 再生中にミュート解除状態で、持続音 + サーッという弱いノイズの両方を確認。
  3. タイムライン中盤でも文字と背景が維持されることを確認。

# AI Agent Operating Manual

## Project

Tokyo Rain LOFI Generator

Purpose:
Create nostalgic rainy Tokyo LOFI videos for sleep, focus, and long-form listening.

---

# Core Worldview

Keywords:

- rainy Tokyo
- lonely
- nostalgic
- melancholic
- VHS texture
- analog noise
- subtle glitch
- Japanese night atmosphere
- urban realism
- convenience store at midnight
- late night train station
- sleepy city pop atmosphere

---

# Priorities

Most important:

1. sleep usability
2. long replay endurance
3. low stimulation
4. calm atmosphere
5. subtle movement
6. loop compatibility
7. nostalgic emotional tone

---

# Forbidden Style

Avoid:

- bright anime style
- hyper saturation
- flashy EDM feeling
- TikTok fast editing
- overactive camera movement
- excessive CGI feeling
- clean modern anime aesthetic

---

# Visual Direction

Preferred visuals:

- rain on windows
- dim room lighting
- vending machines at night
- convenience stores
- train platforms
- wet streets
- apartment interiors
- drifting smoke
- slow curtain movement
- tiny camera drift
- VHS artifacts
- film grain
- imperfect linework

---

# Technical Direction

Environment:

- Replit
- FFmpeg
- GitHub
- mobile-friendly workflow

Output goals:

- long-form mp4
- stable rendering
- lightweight processing
- smartphone usability

---

# Coding Philosophy

The AI should:

- prioritize stability over complexity
- avoid unnecessary dependencies
- generate reusable structure
- explain major errors simply
- keep implementation modular

---

# UI Philosophy

UI should be:

- simple
- mobile-first
- low cognitive load
- minimal buttons
- dark atmosphere

---

# Error Handling

When errors happen:

1. explain probable cause
2. provide simple fix
3. avoid overly technical wording
4. preserve existing project structure

---

# Agent Role

The human is not mainly a programmer.

The human role is:

- direction
- quality control
- worldview management
- final approval
- prioritization

The AI role is:

- implementation
- drafting
- troubleshooting
- optimization support

---

# Long-Term Goal

Build semi-automated AI-assisted content production systems focused on:

- LOFI videos
- AI-assisted workflows
- long-term asset creation
- scalable creative systems
