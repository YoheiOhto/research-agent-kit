# 研究repoのagent指示ひな形

導入前にこの注意書きを外し、`<KIT_DIR>`を確認済みcloneの絶対パスへ置き換える。既存AGENTS.mdがある場合は必要な指示を統合し、置き換えない。未記入の環境・権限を、導入済み・許可済みと扱わない。

## 最初に読むもの

このrepoの依頼、Git状態、近いディレクトリの規約と、`<KIT_DIR>/rules/RULES.md`を読む。既存の現在地・Read firstがあれば従い、関係するcode・設定・証拠だけを追加で読む。kit全体の案内や全skillを毎回読み込まない。

Git作業には`<KIT_DIR>/rules/git.md`と`git-workflow`、研究計画・結果には`research-workflow`を使う。導入したskill・helperの場所を確認し、未導入なら必要な準備を報告する。指示だけで実行ゲート・権限・sandboxが実装されたと考えない。

## このrepoで決めること

以下は未記入である。利用者・管理者と合意して、該当する具体値または理由付きの適用外を記録する。

| 項目 | 記入する内容 |
|---|---|
| Git | 個人fork・origin、machine branch、組織の反映先、PR・mergeの権限 |
| 研究記録 | planの場所、承認対象の版の識別、Issue・Projectの対象 |
| 実行 | profile・host・account、承認されたrunner、環境・lockfile、未導入機能 |
| 保存 | 入力・cache・checkpoint・logs・outputs・reports・短い記録・runtime stateの場所と保持方針 |
| 制限 | 科学的条件、API等の利用上限、期限、hold、quota・他の利用者への配慮 |

## 作業の境界

依頼範囲の可逆なローカル作業と相応の検証を進め、無関係な変更を保護する。実装前は`find-existing`が導入済みなら既存runner・lib・例を確認する。研究実装・実データ処理・probe・job投入は、固定したplanと同版のIssue、人の明示承認の範囲に従う。未確定の科学的条件を既定値で埋めない。

実行の前に解決済み設定・入力・model/prompt・variant/seedを計画と照合する。依存変更、実転送、削除・上書き、job取消、共有環境変更、外部投稿・公開には対象ごとの既存承認を確認する。同じ対象・範囲の承認を繰り返し求めず、PRのmergeは特定PRへの依頼がある場合だけ行う。

研究reviewでは導入済みの`research-review`を使い、実際の根拠とfile:lineを示す。長時間処理・再開の設計には導入済みの`preempt`を使う。skillの存在は新しい実行の許可ではない。

画像の作成・編集は導入済みの`visual-assets`で方法と実在toolを選ぶ。HTMLを明示依頼された場合だけ、導入済みの`show-me`と同梱assetを使う。生成画像を実験結果の証拠にせず、保存・実見・来歴と公開範囲を確認する。

## 記録と出力

結果、判断、実際の検証、残る不明点を先にチャットで伝える。通常の説明用HTML・全文ログ・backup・並行する報告を自動生成しない。既存のplan・Issue・結果bundleを正本とし、未変更の証拠を再利用する。

失敗・欠損・未判定を陰性と混ぜず、件数には単位と分母を付ける。図は元表・code・来歴を残して実画像を確認し、未確認はdraftとする。実験条件の改訂と結果追記を分け、承認済み本文・過去の結果を保つ。
