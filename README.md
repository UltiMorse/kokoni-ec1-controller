# KOKONI EC1 Local Controller

KOKONI EC1 3Dプリンターをローカルネットワーク経由で直接制御するためのGUIツールです。  
ADBを使って純正アプリを一時停止し、内部シリアル（`/dev/ttyS1`）へ直接G-codeを送信します。
KOKONIのアプリがサーバーダウンで頻繁に使えないことがある、重めのSTLファイルのスライスに時間がかかるなどの不満があったので制作しました。
今後、公式サーバーがサービス終了した際には、フィラメントの交換などもできるようにしたものも開発済みなので、公開します。

---
<img width="721" height="778" alt="image" src="https://github.com/user-attachments/assets/5d2065d0-8807-46ca-a544-1b19b87415bf" />

## 免責
本ツールは非公式です。使用は自己責任で行ってください

- 故障・火災・起動不能などについて開発者は責任を負いません
- 使用中はプリンターから離れず監視してください

---

## 主な機能
- **直接制御**：クラウドや公式スマホアプリを介さずG-code送信

- **内部純正アプリ切り替え**：こちらから操作しているときに邪魔になる組み込みアプリ`com.dq.printer` の有効/無効を切替。起動時のセットアップなどはこの純正アプリで行われるので、enableにしてから再起動をしないと初期セットアップ時のライトの点滅が終わらないということが起こるので、切り替えをGUIでできるようにしました。

- **リアルタイムログ**：応答をターミナルで確認  

- **IPアドレスの入力欄**: プレースホルダーとして、開発者の環境(Buffaloルーター)のIPが入力されています。各自の環境に合わせて192.168.11.25の部分をお使いのプリンターのIPアドレスに書き換えてください。ポート番号の :5555 は共通ですので、IPアドレス部分のみを変更して「CONNECT」ボタンを押すことで接続が完了します。

- **マニュアル操作**
  - ホーム復帰
  - レベリング位置へ移動
  - 緊急停止（KILL）

---

## 前提
- **ADB**
  - Linux: `sudo apt install adb`
  - Windows: Platform-Tools を導入して PATH を通す（未確認）
- **ネットワーク**
  - PCとプリンターが同一LAN内にあること
- **プリンターIP**
  - 各自で確認して設定。5555番ポートが開いているものを探すと楽です。MACアドレス（物理アドレス）が f0:b0:40 から始まるものを探してください。それが KOKONI EC1 です。
  Linuxでの確認例: ```ip neighbor show``` を実行し、f0:b0:40 を含むIPアドレス（例: 192.168.11.25）を探します。確実な方法: ```nmap -p 5555 192.168.x.0/24 --open``` を実行し、open と表示されるIPを確認してください。
- **UltiMaker Cura**
  - プリンタ本体から抜き出したG-codeによると、どうやら公式サーバーでの処理はUltiMaker Curaを使っているようであったので、下の方で紹介するプロファイルの設定をした上でG-codeを生成していただきたいです。
  - Cura: https://ultimaker.com/ja/software/ultimaker-cura/

---

## スライサーUltiMaker Curaの設定

### 1. プリンター追加
`Add Printer > Non-UltiMaker > Custom FFF Printer`

| 項目 | 値 |
|------|----|
| サイズ | 100 x 100 x 58 mm |
| プレート | Rectangular |
| G-code | Marlin |
| Gantry | 58 mm |
| X/Y min | -20 / -10 |
| X/Y max | 10 / 10 |

#### Start G-code
    M104 S200
    M105
    M109 S200
    M82
    G28
    G1 Z15.0 F6000
    G92 E0
    G1 F200 E3
    G92 E0
    G1 F2700 E-6.5

#### End G-code
    M107
    M104 S0
    M140 S0
    G92 E1
    G1 E-1 F300
    G28 X0 Y0
    M84

---

### 2. プロファイル読み込み
`configs/KOKONI EC1.curaprofile` をインポート

- フロー率：92%
- 速度：45mm/s
- 初層厚：0.1mm

など公式アプリ生成のG-codeをもとに作成したプロファイルを作成したのでそれを使ってください非公式のフィラメントを詰め替えて使うときなどは温度を調整するなど、各自でフィラメントの溶け具合などを確認して調整してください。

---

## 使い方

### バイナリ
1. Releasesからダウンロード  
2. 実行権限付与（Linux）
       chmod +x kokoni-controller-linux
3. 起動してIP入力（例：192.168.1.xxx:5555）

---

### 開発者向け

    git clone https://github.com/UltiMorse/kokoni-ec1-controller.git
    cd kokoni-ec1-controller
    uv sync
    uv run kokoni_gui.py

uvが好きなのでuvを使っています。

---

## License
MIT License
