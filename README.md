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

## GitHub Actionsで60分LOFI動画を生成する

Google Driveの `Tokyo ChillMatic FM / Videos / video_001 / tracks` にある `track01.mp3`〜`track20.mp3` を使い、GitHub Actions上のFFmpegで60分MP4を生成できます。

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

### 自動波形ビジュアライザー

動画生成時に、最終ミックス音声へ反応するシンプルな横波形を下部中央へ自動追加します。

- FFmpegの `showwaves` フィルターを使用します。
- 波形は白系の小さめ表示で、透明背景として背景画像の上に重ねます。
- 最終音声を `asplit` で分岐し、MP4に入れる音声と波形生成用の音声を同じミックスから作るため、`rain.mp3` がある場合は雨音込みの最終音声に反応します。
- 安定性優先のため、波形・ロゴ・雨オーバーレイの生成に失敗した場合は、それらを外して再試行し、MP4出力を優先します。

### 任意機能の無効化

必要な場合はworkflowや手動実行時の環境変数で任意機能を無効化できます。

```bash
ENABLE_WAVEFORM=0 scripts/generate_lofi_video.sh
ENABLE_LOGO=0 scripts/generate_lofi_video.sh
```

## GitHub ActionsでMP4をGoogle Driveへ自動アップロードする

`Generate LOFI video` workflowは、生成したMP4を従来通りGitHub Actions Artifactへ保存したあと、Google Driveの `Tokyo ChillMatic FM / Outputs` にもアップロードします。

### 前提
- GitHub repository secret `GOOGLE_SERVICE_ACCOUNT_JSON` にGoogleサービスアカウントJSONを登録しておきます。
- Google Drive上の `Tokyo ChillMatic FM` フォルダを、サービスアカウントのメールアドレスに共有します。
- サービスアカウントには、`Tokyo ChillMatic FM` 配下でファイル作成・更新できる権限を付与します。

### 実行手順
1. GitHubの **Actions** タブを開きます。
2. **Generate LOFI video** workflowを選びます。
3. **Run workflow** を押します。
4. `video_number` に素材フォルダ番号（例: `001`）を入力します。
5. `output_file` に完成MP4ファイル名（例: `Tokyo_Memory_Archive_001.mp4`）を入力します。
6. 実行完了後、以下を確認します。
   - GitHub ActionsのArtifactに `output_file` と同名のMP4が保存されていること。
   - Google Driveの `Tokyo ChillMatic FM / Outputs` に同名MP4がアップロードされていること。

### Outputsフォルダについて
- `Tokyo ChillMatic FM` 直下に `Outputs` フォルダが無い場合、workflowが自動作成します。
- `Outputs` 内に同名MP4が既に存在する場合は、新しい生成結果で上書き更新します。

### 失敗時の挙動
- Artifact保存はGoogle Driveアップロードより先に実行されます。
- Google Driveアップロードステップは `continue-on-error: true` のため、Driveアップロードに失敗してもArtifact保存済みのMP4は維持されます。
- Driveアップロードに失敗した場合は、Actionsログの **Upload MP4 to Google Drive** ステップでエラー内容を確認してください。

## GitHub ActionsでMP4をYouTubeへ非公開アップロードする

`Generate LOFI video` workflowは、生成したMP4をGitHub Actions ArtifactとGoogle Drive `Tokyo ChillMatic FM / Outputs` に保存したあと、YouTubeにも自動アップロードできます。YouTube側の公開設定はworkflow内で固定しており、必ず **非公開（private）** としてアップロードします。サムネイルの自動設定は行いません。

### YouTube APIの認証方式

YouTube Data APIの動画アップロードには、YouTubeチャンネルへの操作権限を持つユーザーのOAuth 2.0認可が必要です。Google Drive連携で使っているサービスアカウント方式では、通常のYouTubeチャンネルへ動画をアップロードできません。

このリポジトリでは、GitHub Actions上で次の流れを使います。

1. Google CloudでOAuthクライアントを作成します。
2. 対象YouTubeチャンネルを操作できるGoogleアカウントで、`https://www.googleapis.com/auth/youtube.upload` スコープを許可します。
3. 取得したrefresh tokenをGitHub Secretsへ保存します。
4. workflow実行時にrefresh tokenからaccess tokenを取得し、YouTube Data API `videos.insert` でMP4をアップロードします。

### スマホだけでYouTube API認証情報を取得する手順

以下はスマホのブラウザだけで `YOUTUBE_CLIENT_ID`、`YOUTUBE_CLIENT_SECRET`、`YOUTUBE_REFRESH_TOKEN` を取得するための手順です。Google Cloud Consoleはスマホ表示だとメニューが隠れることがあるため、見つからない場合はブラウザの **デスクトップ用Webサイトを表示** をONにしてください。

#### 事前確認

1. スマホのブラウザで、YouTubeへアップロードしたいチャンネルを管理しているGoogleアカウントにログインします。
2. ブランドアカウントのチャンネルを使っている場合は、YouTubeアプリまたはYouTube Studioで、そのGoogleアカウントが対象チャンネルを操作できることを確認します。
3. 取得した値はあとでGitHub Secretsへ貼り付けるため、スマホのメモアプリなどに一時的に控えます。作業後はメモから削除してください。

#### 1. Google Cloudプロジェクトを作る

1. ブラウザで `https://console.cloud.google.com/` を開きます。
2. 右上のアカウントアイコンを押し、YouTubeチャンネルを操作するGoogleアカウントになっていることを確認します。
3. 画面上部のプロジェクト名、または **プロジェクトを選択** を押します。
4. **新しいプロジェクト** を押します。
5. **プロジェクト名** に `Tokyo ChillMatic FM Uploader` など分かりやすい名前を入力します。
6. **作成** を押します。
7. 作成後、画面上部のプロジェクト選択から、いま作ったプロジェクトを選びます。

#### 2. YouTube Data API v3を有効化する

1. 左上の三本線メニューを押します。
2. **APIとサービス** → **ライブラリ** を押します。
3. 検索欄に `YouTube Data API v3` と入力します。
4. 検索結果の **YouTube Data API v3** を押します。
5. **有効にする** を押します。

#### 3. OAuth同意画面を設定する

1. 左上の三本線メニューを押します。
2. **APIとサービス** → **OAuth 同意画面** を押します。
3. **User Type** が表示された場合は、個人のGoogleアカウントでは通常 **外部** を選び、**作成** を押します。
4. **アプリ名** に `Tokyo ChillMatic FM Uploader` と入力します。
5. **ユーザーサポートメール** で自分のGoogleアカウントを選びます。
6. **デベロッパーの連絡先情報** のメールアドレスに自分のメールアドレスを入力します。
7. **保存して次へ** を押します。
8. **スコープ** 画面では、ここでは追加せず **保存して次へ** を押します。
9. **テストユーザー** 画面で **ユーザーを追加** を押します。
10. YouTubeチャンネルを操作するGoogleアカウントのメールアドレスを入力し、**追加** を押します。
11. **保存して次へ** を押します。
12. 内容確認画面で **ダッシュボードに戻る** を押します。

#### 4. OAuthクライアントを作成してClient ID / Client Secretを取得する

1. 左上の三本線メニューを押します。
2. **APIとサービス** → **認証情報** を押します。
3. 画面上部の **認証情報を作成** を押します。
4. **OAuth クライアント ID** を押します。
5. **アプリケーションの種類** で **ウェブ アプリケーション** を選びます。
6. **名前** に `GitHub Actions YouTube Uploader` と入力します。
7. **承認済みのリダイレクト URI** の **URIを追加** を押します。
8. 次のURLを入力します。

   ```text
   https://developers.google.com/oauthplayground
   ```

9. **作成** を押します。
10. 表示された **クライアント ID** をコピーします。これがGitHub Secret `YOUTUBE_CLIENT_ID` の値です。
11. 表示された **クライアント シークレット** をコピーします。これがGitHub Secret `YOUTUBE_CLIENT_SECRET` の値です。
12. 画面を閉じてしまった場合は、**APIとサービス** → **認証情報** → 作成したOAuthクライアント名を押すと、Client ID / Client Secretを再確認できます。

#### 5. OAuth PlaygroundでRefresh Tokenを取得する

1. 同じスマホのブラウザで `https://developers.google.com/oauthplayground` を開きます。
2. 右上の歯車アイコンを押します。
3. **Use your own OAuth credentials** にチェックを入れます。
4. **OAuth Client ID** に、先ほど取得した `YOUTUBE_CLIENT_ID` を貼り付けます。
5. **OAuth Client secret** に、先ほど取得した `YOUTUBE_CLIENT_SECRET` を貼り付けます。
6. 設定パネルを閉じます。
7. 左側のスコープ一覧で **YouTube Data API v3** を探して開きます。見つからない場合は、スコープ入力欄に次を直接貼り付けます。

   ```text
   https://www.googleapis.com/auth/youtube.upload
   ```

8. `https://www.googleapis.com/auth/youtube.upload` にチェックが入っていることを確認します。
9. **Authorize APIs** を押します。
10. Googleのログイン画面が出たら、YouTubeへアップロードしたいチャンネルを操作できるGoogleアカウントを選びます。
11. **このアプリはGoogleで確認されていません** と表示された場合は、**詳細** → **Tokyo ChillMatic FM Uploader（安全ではないページ）に移動** を押します。自分だけで使うテストアプリなので、この表示は想定内です。
12. 権限確認画面で、YouTubeへのアップロード権限を確認し、**許可** を押します。
13. OAuth Playgroundへ戻ったら、**Step 2 Exchange authorization code for tokens** の **Exchange authorization code for tokens** を押します。
14. 表示された `Refresh token` の値をコピーします。これがGitHub Secret `YOUTUBE_REFRESH_TOKEN` の値です。
15. `Access token` ではなく、必ず `Refresh token` をコピーしてください。GitHub Actionsで長期的に使うのはrefresh tokenです。

#### 6. GitHub Secretsへ登録する

1. スマホのブラウザでGitHubの対象リポジトリ `tokyo_rain_lofi` を開きます。
2. **Settings** を押します。スマホで見えない場合は、横スクロールするか、ブラウザの **デスクトップ用Webサイトを表示** をONにします。
3. **Secrets and variables** → **Actions** を押します。
4. **New repository secret** を押します。
5. **Name** に `YOUTUBE_CLIENT_ID` と入力し、**Secret** にClient IDを貼り付け、**Add secret** を押します。
6. 同じ手順で `YOUTUBE_CLIENT_SECRET` にClient Secretを登録します。
7. 同じ手順で `YOUTUBE_REFRESH_TOKEN` にRefresh Tokenを登録します。
8. 既存のGoogle Drive保存も使うため、`GOOGLE_SERVICE_ACCOUNT_JSON` も登録済みであることを確認します。

#### 取得できる値の対応表

| GitHub Secret名 | 取得する画面 | 入れる値 |
| --- | --- | --- |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → APIとサービス → 認証情報 → OAuthクライアント | クライアント ID |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console → APIとサービス → 認証情報 → OAuthクライアント | クライアント シークレット |
| `YOUTUBE_REFRESH_TOKEN` | OAuth Playground → Step 2 | Refresh token |

### GitHub Secrets

リポジトリの **Settings → Secrets and variables → Actions → Repository secrets** に次を登録してください。

```text
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
```

既存のGoogle Drive連携用secretも引き続き必要です。

```text
GOOGLE_SERVICE_ACCOUNT_JSON
```

### workflow入力

**Generate LOFI video** の **Run workflow** で、YouTube用に次の入力を指定できます。

- `youtube_title` — YouTube動画タイトル。
- `youtube_description` — YouTube動画説明文。
- `youtube_tags` — カンマ区切りタグ。例: `lofi, chill, tokyo, rain, study music`

### 実行手順

1. GitHubの **Actions** タブを開きます。
2. **Generate LOFI video** workflowを選びます。
3. **Run workflow** を押します。
4. `video_number` と `output_file` を指定します。
5. `youtube_title`、`youtube_description`、`youtube_tags` を指定します。
6. workflowを実行します。
7. 完了後、以下を確認します。
   - GitHub Actions ArtifactにMP4が保存されていること。
   - Google Driveの `Tokyo ChillMatic FM / Outputs` にMP4が保存されていること。
   - YouTube Studioに非公開動画としてアップロードされていること。

### 失敗時の挙動

- MP4生成とArtifact保存はYouTubeアップロードより先に実行されます。
- Google Drive保存もYouTubeアップロードより先に実行されます。
- YouTubeアップロードステップは `continue-on-error: true` のため、YouTube API認証・クォータ・通信などが原因で失敗しても、MP4生成、Artifact保存、Google Drive保存は失敗扱いになりません。
- YouTubeアップロードに失敗した場合は、Actionsログの **Upload private video to YouTube** ステップでエラー内容を確認してください。
