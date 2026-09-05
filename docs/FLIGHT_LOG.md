# 最新の飛行経路ログ

2026-09-05実装、2026-09-06に姿勢と約10Hz記録を追加。保存先はプロジェクト直下の`logs/latest-flight.csv`。
通常の配置では`C:\Users\azoo\git\arrietty-up\logs\latest-flight.csv`。
この変更前の飛行経路は保存されておらず、遡って復元できない。
導入時に起動済みのUPBGEには、終了して通常のlauncherから再起動すると反映される。

## 保存と上書き

- Pでゲームを開始した最初のフレームで、同じCSVを新規作成・上書きする。
  Button 1で実走行を始める前の待機位置も含む。設定画面での待機だけでは消さない。
- 約0.1秒に1行（最大10Hz、実際のゲームフレームに依存）、Esc終了時には最後の地点・姿勢も記録する。
- 同じゲーム中は経路を追記するのでファイルサイズは増える。次のPで前回分を
  置き換える。Button 1の安全復帰ではログを消さない。日付別ファイルは作らない。
- CSVは別スレッドで書き、各行でflushする。ゲーム側は最大120件のqueueへ
  待たずに渡す。ディスク停止などでqueueが満杯ならサンプルを落とし、
  runtime property `flight_log_dropped_samples`へ件数を出す。書込み障害は
  `flight_log_status`とconsoleの`ARRIETTY_FLIGHT_LOG_ERROR`へ出し、飛行は継続する。
- 強制終了では最後の未書込みサンプルを失う場合がある。録画・全フレーム保存・
  完全なリプレイではなく、飛行経路を確認するためのログ。

## 列

| 列 | 内容 |
|---|---|
| recorded_utc | 実際に記録したUTC日時 |
| session_seconds / ride_seconds | Pからの秒数 / Button 1からの走行秒数 |
| east_m / north_m | 世界座標X（東）/ Y（北）、m |
| altitude_m | シミュレータの機体Z、高度m。測量上の海抜値ではない |
| bearing_deg | 北0度、東90度の方位 |
| pitch_deg | 機首上げが正の適用ピッチ角、度 |
| roll_deg | 右翼下げが正の適用ロール角、度。内部のbank_degreesとは逆符号 |
| speed_kmh | シミュレータの移動速度 |
| ride_active / flight_enabled / airborne | 走行開始・飛行モード・離陸状態、0/1 |
| distance_m | シミュレータの累積移動距離 |
| world_file | 使用したblendのパス |
| world_local_time | 適用した世界日時。実際の記録日時とは別 |
| origin_latitude / origin_longitude | ENU座標の原点の緯度・経度 |

Funafutiの原点は滑走路中心`-8.5239843, 179.1967829`。各地点はこの原点に
対する東・北方向の距離で表す。世界情報はeditorのgame_preで渡し、ゲーム中に
bpyへアクセスしない。対応する世界情報がない場面では末尾のmetadata列は空欄。

`pitch_deg`・`roll_deg`は既存列の後ろへ追加した。操作指令・HMD姿勢ではなく、
`_vehicle_orientation`が適用する機体姿勢と同じ値を保存する。空中では
`flight.pitch_degrees`と`-flight.bank_degrees`、地上では同関数に合わせて両方0。
既存の120件queueは10Hzで約12秒分。遅れを埋める架空サンプルは作らない。
Arrietty-UPプロセスを新しく起動してから収録する。既存CSVを変換・上書きはしない。

2026-09-06の姿勢付きログ初回テスト後、ユーザーの指摘で機体表示のロールが
旋回方向と逆だったことが判明。`_vehicle_orientation`のbank回転符号を修正した。
飛行計算とCSVのroll符号は元から正しいため、収録済みCSVは変換不要。
初回ログは旧表示と同じ見た目を再現するのでなく、記録されたバンク方向を
正しく再現する。次回の新しいUPBGEプロセスからHMD側の表示にも修正が反映される。

実機確認は2〜3分、離陸後に左右のロールと機首上げ・下げを入れ、Escで終了。
再生側で保存するまでは次のPを開始しない。旧CSVの姿勢は後から復元できない。

## 診断ログ

通常launcherの標準出力は`logs/latest-console.out.log`、エラー出力は
`logs/latest-console.err.log`。UPBGEプロセス起動ごとに同じ名前で上書きする。
同じプロセス内のP/Escではconsoleログは継続する。以前のTEMP内の
`arrietty-live-日時.*.log`は既存分を削除していない。ログ全体はGit対象外。

## 検証

`python -m unittest discover -s tests`で78件PASS。経路の間引き、前回分の
上書き、最終座標、二重終了時の保持、書込み失敗の隔離、bpy境界を含む。
Secret Worldの`tests/upbge_world_setup.py`をUPBGEで実行し、世界日時・原点・
ファイル名の引渡しもPASS。追加後の実機飛行ログの確認は次回飛行時に行う。

その後、2026-09-05の実飛行で記録を確認済み。走行開始後163.677秒、163点、
最高高度32.717m、最終移動距離1042.478m。終了時の最終サンプルもある。
`../Arrietty-trajectory/build/accepted-flight.csv`へコピーを確保し、通常版
Blenderで位置・方位の再生を検証した。元のlatest CSVは変更していない。
