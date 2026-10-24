# 別計算機への引継ぎひな形

既存planへ必要な欄を統合する。これは承認、転送・投入・回収・削除の自動化、quota制御を実装しない。未確認は未確認とし、実データ・認証情報を共有用templateへ書かない。

## 対象と承認

| 項目 | 記録 |
|---|---|
| plan版・Issue・研究目的・比較 | 未記入 |
| 維持する入力・split・model/prompt・設定・seed・評価 | 未記入 |
| 許可されたhost/account・除外host・deadline・最新hold | 未記入 |
| 投入・転送・回収・依存変更・取消・削除それぞれの承認 | 未確認 |
| 元の実行との数値・品質の同等性／分けて扱う基準 | 未記入 |

## 実行前の照合

- code・入力・model・環境の固定ID、source/destination、必要bytes、include/exclude：未記入
- CPU architecture、GPU/driver、container・依存版、共有mountと永続／scratchの違い：未確認
- 空き容量、利用者・groupのquota、scheduler/account・実行資源：未確認
- 転送preview、前後manifestの照合、既存結果との衝突時の扱い：未記入
- model入力容量とtoken計数が関係する場合、その実行機での根拠：未記入／理由付き適用外

## 分担・再開・停止

- 固定したtask IDと担当、重複・欠落なしの確認、実行中taskの所有権：未記入
- resume key、保存途中の扱い、writer・lock・再投入の制御を実装した場所：未確認
- 同等性を確認する承認済みpilotと採用基準：未記入。未承認のprobeを実行しない
- STOP確認、親子process・要求が停止したことの確認、所有権移動の順序：未記入

## 実行・回収時に残す事実

実際のcode/runtime/input/assignmentの識別情報、解決済みcommand・設定、run/job ID、実行場所と資源、出力・logsを記録する。queued/held/running/failed/completed、検証済み件数・分母、残件、時刻と見積もりの根拠を区別する。

回収前にwriterの終了・確定状態を確認し、別場所へ回収して元と照合する。既存結果の上書き、scratchの削除、job取消を回収の承認へ混ぜない。raw evidence・確認結果・未解決事項を正本へリンクし、短い作業記録へ全データを複製しない。
