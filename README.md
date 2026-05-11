# KOKONI EC1 Local Controller（テスト用）

KOKONI EC1 3Dプリンターをローカルネットワーク経由で直接制御するためのGUIツール。
ADBを使って純正アプリを一時停止し、内部シリアル（`/dev/ttyS1`）へ直接G-codeを送信。
KOKONIのアプリがサーバーダウンで頻繁に使えないことがある、重めのSTLファイルのスライスに時間がかかる（そもそも受け付けてくれない）などの不満があったので作成

こちらはPCの接続を切れない、無線で1行ずつ送るので不安定である。

プリンタ内部で処理できるようにしたものがこちら。

https://github.com/UltiMorse/kokoni-ec1-server

https://github.com/UltiMorse/kokoni-ec1-desktop
