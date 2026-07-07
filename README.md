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

## Google Apps Script: SUNO mp3整理

`google_apps_script/suno_organizer.gs` には、Google Drive上の `Tokyo ChillMatic FM / Incoming` に入れたSUNO mp3を、ファイル名ではなくGoogle DriveのファイルID基準で20曲単位に整理するApps Scriptを収録しています。

### Drive側の前提フォルダ

```text
Tokyo ChillMatic FM/
├── Incoming/
└── Videos/
```

### 使い方

1. Google Apps Scriptで新規プロジェクトを作成します。
2. `google_apps_script/suno_organizer.gs` の内容を貼り付けます。
3. 関数 `runSunoOrganizer` を実行します。
4. 初回のみGoogle Driveへのアクセス権限を承認します。

### 動作

- `Incoming` 内の `.mp3` が20曲未満なら、ログに「20曲未満のため処理なし」と出して終了します。
- 20曲以上ある場合、`Videos` 内の既存 `video_XXX` 番号を確認し、重複しない次の番号で `video_001` のようなフォルダを作成します。
- 各 `video_XXX` 内に `tracks` フォルダを作成します。
- 同名mp3が複数あっても、Google DriveのファイルIDで対象を管理し、古い順に20曲ずつ `track01.mp3` から `track20.mp3` にリネームして、`Incoming` から `Videos/video_XXX/tracks` へ移動します。
- 40曲以上ある場合は、20曲単位で繰り返し処理します。

## GitHub ActionsでLOFI動画を生成する

Google Driveの `Tokyo ChillMatic FM / Videos / video_001 / tracks` にある `track01.mp3`〜`track20.mp3` を使い、GitHub Actions上のFFmpegで連結した音源の合計時間に合わせたMP4を生成できます。

### Drive側に置く素材

`Tokyo ChillMatic FM / Videos / video_001 / tracks`:

```text
track01.mp3
track02.mp3
...
track20.mp3
```

`background.png` は必須です。次のどちらかに置いてください。

```text
Tokyo ChillMatic FM / Videos / video_001 / background.png
```

または共通素材として次に置いても使えます。

```text
Tokyo ChillMatic FM / Videos / background.png
```

`rain.mp3` は任意です。存在する場合だけBGMに小さめの音量でミックスし、存在しない場合はBGMのみで動画を生成します。

```text
Tokyo ChillMatic FM / Videos / video_001 / rain.mp3
Tokyo ChillMatic FM / Videos / rain.mp3
```

`rain_overlay.mp4` は任意です。存在する場合だけ背景画像の上に薄く重ねます。

### GitHub Secrets

GitHub ActionsからGoogle Driveを読むため、リポジトリのSecretsに次を追加してください。

```text
GOOGLE_SERVICE_ACCOUNT_JSON
```

値にはGoogle CloudのサービスアカウントJSONを丸ごと貼り付けます。Drive側では、`Tokyo ChillMatic FM` フォルダをそのサービスアカウントのメールアドレスに閲覧共有してください。

### 実行方法

1. GitHubのリポジトリ画面を開く。
2. 上部の **Actions** をクリックする。
3. 左側から **Generate LOFI video** を選ぶ。
4. **Run workflow** をクリックする。
5. `video_number` に `001` を入力する。
6. `output_file` は通常 `Tokyo_Memory_Archive_001.mp4` のままでOKです。
7. もう一度 **Run workflow** を押す。
8. 完了後、実行結果ページ下部の **Artifacts** からMP4をダウンロードする。

### 生成内容

- `track01.mp3`〜`track20.mp3` を番号順に連結します。
- 60分に足りない場合は音楽をループし、60分で切ります。
- `rain.mp3` が存在する場合だけ、小さめの音量でミックスします。存在しない場合はBGMのみで生成します。
- `background.png` / `background.jpg` / `background.jpeg` のいずれかを1920x1080の背景にします。
- `rain_overlay.mp4` がある場合は薄く重ねます。
- 出力はH.264 / AAC / MP4です。
- 標準の完成ファイル名は `Tokyo_Memory_Archive_001.mp4` です。

## GitHub Actions: LOFI動画生成素材

`Generate LOFI video` workflow は、Google Drive から `video_assets/` に素材を取得し、GitHub Actions上のFFmpegでMP4を生成します。ローカルPCでの手作業やCapCutでの後処理は不要です。

### 必須素材
- `tracks/track01.mp3` 〜 `tracks/track20.mp3`
- 背景画像（次のいずれか1つ）
  - `background.png`
  - `background.jpg`
  - `background.jpeg`

### 任意素材
- `rain.mp3` — あればBGMに小さくミックスします。無い場合はBGMのみで続行します。
- `rain_overlay.mp4` — あれば背景の上に薄く重ねます。無い場合はスキップします。
- `logo.png` / `logo.jpg` / `logo.jpeg` — あれば中央下部に小さく重ねます。無い場合はスキップします。

### CapCut背景動画の扱い

`background_loop.mp4` がある場合は、CapCutで作成済みの雨・フィルムノイズ入り短尺動画として優先的に使い、指定時間までループ延長します。

- FFmpeg側では音声由来の波形表示を追加しません。
- `background_loop.mp4` 自体に含まれる雨やフィルムノイズを前提にし、音源は従来通りMP4へ付けます。
- `background_loop.mp4` 使用時は、CapCutで作成した映像をできるだけそのまま使うため、FFmpegの映像フィルター（scale / fps / format / fade / blend / overlay / noise）をかけず、動画ストリームを直接マップしてコピーします。
- `background_loop.mp4` に含まれる雨音は本編と同じ音量のままループし、Suno BGM終了後も既定5秒間だけ雨映像と一緒に継続してから同時終了します（フェードアウトなし）。
- `ENABLE_RAIN_OVERLAY=0` や `ENABLE_FILM_GRAIN=0` は、FFmpegで追加する任意効果だけを制御します。CapCut動画内に既に入っている雨・フィルムノイズを弱める処理は行いません。
- 安定性優先のため、画像背景使用時にロゴ・雨オーバーレイ・フィルムグレインの生成に失敗した場合は、それらを外して再試行し、MP4出力を優先します。

### 音量調整

BGMと`background_loop.mp4`内の雨音の音量は環境変数で調整できます。`amix` は `normalize=0` でミックスし、入力音量が自動的に半分へ下がらないようにしています。

```bash
BGM_VOLUME=1.0 BACKGROUND_AUDIO_VOLUME=1.0 AUDIO_LIMIT=0.98 scripts/generate_lofi_video.sh
```

### 任意機能の無効化

必要な場合はworkflowや手動実行時の環境変数で任意機能を無効化できます。

```bash
ENABLE_LOGO=0 scripts/generate_lofi_video.sh
```

## GitHub Actionsで生成MP4をArtifactへ保存する

`Generate LOFI video` workflowは、生成したMP4をGitHub Actions Artifactへ保存します。サービスアカウントのstorage quotaエラーを避けるため、生成済みMP4のGoogle Drive `Outputs` への新規アップロードは停止しています。

### 現在の保存先
- incoming作品フォルダから生成したMP4は、`incoming-generated-mp4` Artifactに保存します。
- デバッグ用に `DRIVE_FOLDER_ID` を指定して生成したMP4は、`output_file` と同名のArtifactに保存します。
- Google Driveへの完成MP4アップロードは実行しません。

### incoming処理の成功条件
1. Google Driveのincoming作品フォルダから素材を取得します。
2. `scripts/generate_lofi_video.sh` でMP4生成が成功します。
3. 生成済みMP4をGitHub Actions Artifactとして保存できる場所へコピーします。
4. incoming作品フォルダをGoogle Drive上の `completed` へ移動します。

## GitHub ActionsでMP4をYouTubeへ非公開アップロードする（一時停止中）

`Generate LOFI video` workflowのYouTubeアップロードは一時停止中です。workflowはYouTube Data APIアップロードを実行せず、生成済みMP4をGitHub Actions Artifactとして保存します。

YouTube API認証情報は、アップロード再開時までworkflowでは使用しません。

## GitHub Actions: 検証用LOFI動画生成とArtifact保存

`.github/workflows/generate_lofi_video.yml` は手動実行（`workflow_dispatch`）で、MP4生成とArtifact保存を検証できます。Google Driveへの完成MP4アップロードとYouTube非公開アップロードは現在実行しません。

### 推奨実行手順
1. GitHub の **Actions** タブを開きます。
2. **Generate LOFI video** workflow を選びます。
3. **Run workflow** を押します。
4. 動画の長さは、ダウンロードしたSuno音源を連結した合計再生時間に雨音アウトロ5秒を足して自動計算されます。
5. 成功したらGitHub Actions Artifactに保存されたMP4を確認します。

### 動画尺
- `TARGET_SECONDS` や `duration_minutes` で固定尺を指定せず、連結したSuno音源の合計時間に `RAIN_OUTRO_SECONDS`（既定5秒）を足した長さを動画長として使用します。
- Suno音源はループせず最後まで再生し、終了後は無音としてパディングするためBGMは鳴りません。
- `background_loop.mp4` の雨映像と雨音は動画全体（Suno合計尺＋アウトロ）までループし、アウトロ終了時に同時停止します。
- 雨音アウトロにフェードアウトはかけず、雨音の音量は本編中の`background_loop.mp4`音声と同じです。
- 生成済みMP4はGoogle Driveへアップロードせず、GitHub Actions Artifactとして保存します。

### FFmpeg高速化設定
GitHub Actions では長時間エンコードの検証前に生成・Artifact保存経路を確認するため、必要に応じて以下の高速化設定で実行します。

- `FFMPEG_PRESET=ultrafast`
- `FFMPEG_CRF=30`
- `ENABLE_FILM_GRAIN=0`
- `ENABLE_FILM_DUST=0`

これにより、GitHub Actions 上の処理時間を抑えられます。

## Google Drive incoming 自動処理（main merge後に初回テスト）

既存の手動 `Run workflow` は残したまま、`.github/workflows/generate_lofi_video.yml` に30分ごとの `schedule` 実行を追加しています。手動実行時は `video_number` / `output_file` を入力し、連結したSuno音源の合計時間に合わせた動画を生成してArtifactへ保存できます。

### Driveフォルダ構成

Google Drive側に次の構成を用意してください。フォルダ名は自動処理スクリプトが参照します。

```text
Google Drive/
  Tokyo ChillMatic FM/
    incoming/
      work_001/
        background.png
        track01.mp3
        track02.mp3
        ...
    completed/
    failed/
```

### incoming作品フォルダの素材条件

- `background.png` / `background.jpg` / `background.jpeg` のいずれか1枚だけを配置します。
- `.mp3` 音源を配置します。理想は20曲です。
- 20曲未満でも1曲以上あれば自動処理対象になります。その場合、既存の `generate_lofi_video.sh` が必要とする `track01.mp3`〜`track20.mp3` 形式に合わせるため、不足分はダウンロード後に一時的に複製されます。
- 条件を満たさない作品フォルダは移動せず、GitHub Actionsログに理由が出ます。

### 自動実行の流れ

1. GitHub Actionsが30分ごとに `Tokyo ChillMatic FM/incoming` を確認します。
2. 条件を満たす未処理の作品フォルダを1件だけ検出します。
3. 作品フォルダから `background.*` と `.mp3` を `video_assets/` にダウンロードします。
4. 既存の `scripts/generate_lofi_video.sh` で、連結したSuno音源の合計時間に合わせたMP4を生成します。
5. 生成したMP4をGitHub Actions Artifact保存用ディレクトリへコピーします。
6. 成功した作品フォルダは `completed/` へ移動します。
7. 生成に失敗した作品フォルダは `failed/` へ移動します。原因は該当Actions runのログで確認します。

### 二重実行防止

処理成功後は作品フォルダ自体を `incoming/` から `completed/` に移動します。失敗時も `failed/` に移動するため、同じ作品フォルダが `incoming/` に残らず、次回スケジュールで二重実行されません。

### 初回テスト手順（mainへmerge後）

1. `main` へmerge後、GitHub Actionsの `Generate LOFI video` を手動実行し、Suno音源の合計時間に合わせた動画が生成され、Artifactに保存されることを確認します。
2. Google Driveの `Tokyo ChillMatic FM/incoming/work_001/` に `background.png` とmp3素材を配置します。
3. 次のスケジュール実行を待つか、必要に応じて `Generate LOFI video` のスケジュール相当のrunを確認します。
4. Actionsログで検出・生成・Artifact保存の完了を確認します。
5. 成功後、`work_001` が `completed/` に移動していることを確認します。失敗した場合は `failed/` に移動していることと、Actionsログのエラー内容を確認します。

### 認証情報

既存のSecrets（`GOOGLE_SERVICE_ACCOUNT_JSON`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`）をそのまま使います。自動処理ではDriveフォルダ移動を行うため、`GOOGLE_SERVICE_ACCOUNT_JSON` のサービスアカウントが `Tokyo ChillMatic FM` 配下の読み取り・移動権限を持っている必要があります。

フォルダ名の変更・重複による事故を避けるため、GitHub Secretsに `TOKYO_CHILLMATIC_DRIVE_FOLDER_ID` を設定できます。このSecretにGoogle DriveのルートフォルダIDを入れると、workflowはフォルダ名検索を行わずIDで `Tokyo ChillMatic FM` ルートを参照します。未設定の場合は、従来どおりデフォルト名 `Tokyo ChillMatic FM` でルートフォルダを検索します。

`TOKYO_CHILLMATIC_DRIVE_FOLDER_ID` の設定手順:

1. Google Driveで `Tokyo ChillMatic FM` フォルダを開きます。
2. ブラウザURLの `/folders/` 以降の文字列をコピーします（例: `https://drive.google.com/drive/folders/<ここがフォルダID>`）。
3. GitHubリポジトリの **Settings** → **Secrets and variables** → **Actions** → **New repository secret** を開きます。
4. **Name** に `TOKYO_CHILLMATIC_DRIVE_FOLDER_ID`、**Secret** にコピーしたフォルダIDを入力して保存します。

## iPhone中心のGoogle Drive Projects運用

PCを常時起動せず、iPhoneでSuno素材をGoogle Driveへ保存して自動生成キューへ投入する運用です。

### Driveフォルダ構成

```text
Tokyo ChillMatic FM/
  Projects/
    SHINBASHI/
      background.png
      SHINBASHI 01.mp3
      SHINBASHI 02.mp3
      ...
      SHINBASHI 20.mp3
  incoming/
  completed/
  failed/
```

### iPhoneでの手順

1. Suno上で曲名を手動で整えます。
2. iPhoneで音源を手動ダウンロードし、Google Driveの `Tokyo ChillMatic FM/Projects/<作品名>/` に保存します。
3. 背景画像を `background.png` / `background.jpg` / `background.jpeg` のいずれかの名前で同じ作品フォルダに保存します。
4. 作品フォルダ内が `background.*` 画像1枚 + `.mp3` 音源20曲になったら、ProjectsチェックWorkflowが `incoming` へ移動します。
5. `incoming` に入った作品フォルダは、既存のスケジュール実行Workflowが検知し、動画生成とArtifact保存の対象になります。

### 自動チェックの動き

- `.github/workflows/check_drive_projects.yml` は手動実行（`workflow_dispatch`）できます。
- 同Workflowはスケジュールでも30分ごとに `Tokyo ChillMatic FM/Projects` を確認します。
- 完成条件を満たした作品フォルダだけを `incoming` へ移動します。
- `incoming` への投入後は既存の `Generate LOFI video` Workflowが従来通り処理します。
- 既存の手動Run Workflowは残しているため、これまで通りDrive番号指定での手動生成も可能です。

### 移動される条件

- `background.*` 画像がちょうど1枚あること。
- `.mp3` ファイルがちょうど20曲あること。
- `incoming` に同名フォルダが存在しないこと。
- `completed` に同名フォルダが存在しないこと。
- `failed` に同名フォルダが存在しないこと。

### スキップされる条件

- `background.*` 画像が0枚。
- `background.*` 画像が2枚以上。
- `.mp3` ファイルが20曲未満。
- `.mp3` ファイルが20曲超。
- `incoming` / `completed` / `failed` のいずれかに同名フォルダがある。

### `completed` / `failed` の意味

- `incoming`: 実行キュー専用です。ここに入った作品フォルダは動画生成・Artifact保存対象になります。
- `completed`: 自動生成とArtifact保存準備が成功した作品フォルダの移動先です。同名作品の二重処理防止にも使います。
- `failed`: 自動生成またはArtifact保存準備が失敗した作品フォルダの移動先です。同名作品の再投入防止にも使います。
