# 水野班向けの導入・研究運用

この文書は、大戸が使っているagent運用を水野班へ共有するための案内です。個人環境の例と、各repo・管理者・利用者が決める条件を分けています。班全体の正式規約や全員への実行許可を、この文書だけで定めるものではありません。

必要な章だけ読みます。Git作業は[git-workflow](../skills/git-workflow/SKILL.md)、研究の条件・結果保存は[research-workflow](../skills/research-workflow/SKILL.md)、ツールの導入・計測は[README](../README.md)が詳細の入口です。

## 1. 何が利用できるか

| 区分 | このrepoにあるもの | 追加で必要なもの |
|---|---|---|
| agentへの指示 | 共通rules、Git rules、Gitと研究のworkflow、専門skill | 受入先のAGENTS.md／CLAUDE.mdからの参照、必要なskillの選択導入 |
| 単体実行できる点検・計測 | 静的コード、venv等の参照、出力の点検、任意の呼出しカウンター | Python 3.11以降。実際の引数と上限はREADMEに記載 |
| Git helper | この文書とGit skillによる使い方・権限の説明 | 本人用に対応したenv。大戸のhelper本体はこのrepoに含めない |
| 実験・通知・定期処理 | 計画、承認、保存、Slack等の運用方法 | 対応するenvの投入ゲート・scheduler・通知hook・報告tool・設定・認証 |

Git helperの原本には`YoheiOhto`固定の所有者検証、初回Git identity・global hooksの設定が残っています。`PERSONAL_OWNER`だけ変えれば他の人へ対応するとは限りません。管理者と実装・設定を確認し、未導入のコマンドを利用可能として扱わないでください。個人env全体のsourceや`setup_git`を、そのまま実行する導入方法は案内していません。

## 2. 利用者とrepoごとに決めること

| 対象 | 確認する内容 |
|---|---|
| 個人GitHub | 自分のアカウント、個人fork、`origin`のURLと所有者、commitの公開名・メール方針 |
| branchと組織反映 | `machine/<host>`、`work/<task>`、組織の確認用branch、reviewerと各段階の権限 |
| GitHub Project | 所有者、URL・番号、書込み権限、どの研究repoのIssueを整理するか |
| 実行環境 | local／Slurm／PBS、実行ホスト、account・queue／partition、承認されたrunner・環境 |
| 保存先 | 入力、コード、キャッシュ、logs、checkpoints、outputs、reports、短い作業記録、runtime state |
| 利用量と停止 | APIの要求数・token・費用・並列数・retry、Miyabiのaccount残量、締切・hold・個別制限 |
| Slack | workspace、通知先、メンション先ユーザーID、bot／webhookの管理者と保存先 |

未確認のProjectや組織branchを推測で作成せず、認証情報をREADME・plan・Issue・commitへ入れません。規約を記録しても、権限付与や認証は完了しません。

## 3. Git・PR・組織への反映

[Git rules](../rules/git.md)を採用し、具体的な操作の前に[git-workflow](../skills/git-workflow/SKILL.md)を読みます。大戸の基本形は次です。

```text
gstart → machine/<host>
  → wstart <task> → work/<task>で編集・検証・commit
  → 変更サマリーと範囲の確認 → gfinish → machine/<host>
  → gpush → 個人main宛のPR
  → 対象PRの明示承認 → merge → gsync
```

`gfinish`はローカルのworkをmachineへ戻す操作です。`gpush`は個人GitHubへのpushとPR作成で、mainへのmergeを含みません。merge後も、組織への反映は別段階です。

組織への一般形は「個人main → 管理者が指定した組織の確認用branch → 組織main」です。大戸は`YoheiOhto/<repo>:main → mizuno-group/<repo>:dev_ohto → mizuno-group/<repo>:main`を使います。他の利用者の反映先は管理者と決め、`dev_ohto`を全員の既定値にしません。

組織の各段階は別のPRです。個人PRのmerge承認を次の組織操作へ流用せず、agentは組織repoへ直接commit・pushしません。remote名`upstream`への接続・`gupstream`は人が行う運用です。agentは読取りも含め利用しません。

## 4. Issue・Project・実行承認

| 対象 | 役割 | それだけでは起きないこと |
|---|---|---|
| plan | 条件の正本と、その版の実行状況 | 計画を保存しても実装・実行の承認にはならない |
| Issue | planの版、判断、進捗、結果への索引 | 作成・label・closeだけで実験やProject登録を許可しない |
| GitHub Project | 複数Issue／PRを一覧・status等で整理する場所 | Issueが必ず自動で所属するわけではない |
| 人の実行承認 | 対象plan版・条件・実装と実行の範囲・期限への決定 | 他の実験、条件変更、組織merge、削除・転送等へは拡張しない |
| PR | コード・設定・文書の変更をreviewして取り込む単位 | PRのmergeだけで研究結果が検証済みになるわけではない |

実験の流れは「相談 → 固定したplan → 同版をIssueへ反映 → 人の明示承認 → 実装・実設定review → 実行」です。未確定事項が残る間は計画と読取り調査までにします。承認済み部分を書き換えず、結果・資源調整・失敗履歴は合意した実行状況欄へ追記します。

[実験計画のIssue Form](../templates/experiment-plan.yml)を、導入先研究repoの`.github/ISSUE_TEMPLATE/experiment-plan.yml`へ必要に応じてコピーできます。既存フォームは比較してから扱います。これは記録用のフォームで、実行ゲート・承認記録・Projectへの登録は実装しません。実験のIssueは対象研究repoに作り、共有kitのrepoを研究記録の代わりにしません。

班のProjectへ所属させるには、そのProjectへの権限と、認証方法に合った設定が別途必要です。Projectの所有者・番号はまだこの共有版の既定値にしていません。tokenの発行や権限の拡張は本人・管理者が行い、agentが権限を製造したり、他人のtokenを共有したりしません。実際の所属を確認するまでは「連携済み」と報告しません。

## 5. local／Slurm／PBSと実行時の確認

| 環境 | 選ぶ根拠と運用 |
|---|---|
| local | 対象ホストとrepoが許可したローカル処理。profile名だけでログインノードの学習・GPU処理を許可しない |
| Slurm | David／Grace等、Slurm管理下の承認された実行先。env導入時はplan・Issue・承認を確認する`runx`を使う |
| PBS／qsub | Miyabi等、PBSのaccount・queue・課金残量を確認する実行先。Slurmのpartition名・資源単位をそのまま移さない |

これらのprofile・runner・実行ゲートは本kitには入っていません。envが導入済みの場合も、通常のlogin shellで`bash -lc 'type -t runx'`が`function`となるか確認し、その環境の承認された入口を使います。関数が見つからないときにrawの`sbatch`・`srun`・`qsub`や直接実行で迂回しません。

投入前には、入力の識別情報、分割、model／prompt、全variant・seed・設定、実行環境と依存版、資源・出力先をplanと照合します。CPU architecture・storage・containerが違う場合は互換性を確認します。軽い合成テストと実データ処理・資源probeは分け、未承認の実験を「点検」として実行しません。

textのmodel判定では実行機上のmodel・runtimeの入力容量を確認し、instructions・schema等も含めたtoken数と出力の予約分を見ます。収まる文書を機械的な文字数で分割しません。大量処理前には要求数・総token・並列数・retry・停止上限を決め、再開時は入力・model・prompt・判定条件が一致する保存済み結果を再利用します。

資源だけの調整をどこまでagentへ任せるかは、受入先の承認済み方針に従います。大戸の個人設定では、科学的条件を維持する同一クラスタ内の資源調整を許可し、厳守する累積予算を外部APIとMiyabi時間に置いています。これは班の他利用者・accountに「計算量無制限」を与える設定ではありません。共有quota、他の利用者、容量、walltime、締切、holdと明示制限を守ります。

再開にはcode・入力・設定の同一性と、checkpoint・途中結果・残りの承認範囲を確認します。依存変更、データ転送、削除、job取消は別の承認範囲です。良さそうな結果を理由にvariantを増やしません。

## 6. outputs・reports・短い記録・runtime state

| 保存物 | 大戸のenvでの配置例 |
|---|---|
| code・plan | repoの`experiments/<id>/`、再利用する実装は既存の`lib/`等 |
| 実験成果 | repoの`outputs/<experiment>/<run>/`。入力・logs・cache・checkpointを区別する |
| review済み結果bundle | `outputs/<experiment>/reports/<bundle>/`に元表・図・描画コード・来歴・確認記録 |
| 正式な日報・週報 | repoの`reports/daily/`・`reports/weekly/` |
| 短い作業記録・依頼HTML | 利用者のartifact保存先。大戸のenvでは`~/99-agent/`配下 |
| 通知・計測等のruntime state | 各toolが指定する利用者のstate領域。例：計測は`${XDG_STATE_HOME:-~/.local/state}/research-agent/` |

大戸の`99-agent`は、東京時間の土曜開始の週とrepoのパス識別子で整理します。env導入時の`artifact_paths.py --repo`で場所を確認します。`RESEARCH_AGENT_ARTIFACT_ROOT`はその親を変更します。コード、repoのclone、実験の出力・checkpoint・ログをここへ集めません。

同じ証拠・解釈の結果bundleは再利用し、変わった場合は旧版を残して区別します。項目ごとの小ファイル、説明のたびのHTML、全文ログ・backupの常時生成を避け、保存枠・保存対象を計画時に決めます。大戸の短い記録領域の目安・制限を、他の利用者の結果削除ルールに置き換えません。

具体例として、大戸の短い記録・依頼HTMLの領域にはtaskディレクトリ単位で100ファイル・1GBの枠があり、超過前に相談します。envの`check_artifacts.py`は違反を報告する点検で、全処理の容量をOSで制限するものではありません。4週より古い週の整理も専用toolのdry-runを確認し、削除する対象の明示承認後に行います。これらを班員の保持期限や実験成果の削除許可に転用しません。

共有版の出力点検は件数・容量を上限付きで調べる機能です。容量を強制制限し、古い出力を自動で圧縮・削除する機能はありません。打切りを全体の合計と扱わず、容量不足では現状と保持判断を相談します。過去の結果をquota達成のために消しません。

図は元表・code・来歴とともにPNGと適切なSVGを保存し、実画像を開いて確認します。大戸のenvの正式な結果最終化ではPNG/PDF/SVGと確認記録・receiptを検証してから結論を採用します。このkitのreview note例だけで、そのreceiptを代用しません。HTMLは依頼時だけ作り、通常はチャットで説明します。

一般画像・編集と制作方法の選択は[visual-assets](../skills/visual-assets/SKILL.md)、依頼されたHTMLの説明と意匠は[show-me](../skills/show-me/SKILL.md)を使えます。HTML assetはskill内へ同梱し、他の設定をコピーしなくても読める構成です。CSS・画像・本文の外部依存を点検し、未記入をdraftとして表示します。配布用ひな形をrepoへ置くことと、利用者の実ページを保存・公開することは別です。

## 7. Slack通知とメンション

この節は対応するenvの通知コードを導入済みの利用者向けです。本kitはSlackを送信せず、設定を追加しただけで通知が動くわけではありません。

共通設定例の保存先は`~/.config/research-env/notifications.json`です。秘密のWebhook・tokenはGitに置かず、本人のローカル設定を管理します。メンション先は自分のSlackユーザーIDに置き換えます。

```json
{
  "agent_mention_user_id": "U012ABCDEF",
  "features": {}
}
```

`U012ABCDEF`は説明用です。実際の送信には、そのenvが対応するWebhook／bot・チャンネル等の設定が別途必要です。`AGENT_SLACK_MENTION_USER_ID`が設定されていれば設定ファイルより優先し、空文字ならメンションを無効にします。

対象はagentの承認待ち・質問回答待ちです。完了・失敗などの通知には追加しません。対応コードは本文をエスケープし、指定したユーザーだけをメンションします。既存の通知停止・重複抑制と、送信する許可の範囲を保ちます。テスト送信も実際の外部送信なので、対象・回数を決めてから行います。

## 8. agent別設定・導入後の確認

本kitのskillは選んで導入し、rulesは既存のAGENTS.md／CLAUDE.mdから参照します。設定全体を置き換えません。Codex・Claude Code・Antigravityにはnative event・権限・toolの違いがあり、同じ指示でも同じ動作を保証しません。計測の対応表はREADMEを参照してください。

大戸のenvではlocal／qsub／slurmの各profileを共通原本から生成し、短い起動入口と、必要部分だけ読むGUIDANCEを使います。Git commitに固定したsnapshotへ設定を配布し、作業中checkoutへの追従を避けます。これらの生成・sync・native profile検査はkitに含めていません。

大戸のCodex profileは`danger-full-access`・対話承認なしが既定ですが、班員の推奨既定として配布していません。hooks・rulesはOSの隔離ではありません。本人の実行環境と管理者の方針に合う権限・sandboxを選び、既存の厳しい制限を維持します。

最初はkitのテストと読取り点検、採用するskill・rulesの差分から確認します。env側の`sync_env --dry-run`は予定差分の確認、`--apply`は稼働設定の変更です。実機agent・認証・scheduler・通知・cronの検証を、それぞれ別に扱います。設定ファイルの存在やテスト成功だけで、導入先の全機能が起動したとは報告しません。

## 9. 貼って使うひな形とskillの選択

ひな形は必要な部分だけを既存の指示・plan・結果へ統合します。全ファイルを毎回コピーせず、未記入の草案を実行設定や承認記録にしません。

| 場面 | 使うもの |
|---|---|
| 既存AGENTS.md／CLAUDE.mdへ指示を加える | [AGENTS例](../templates/project-AGENTS.md)・[Claude入口例](../templates/project-CLAUDE.md)。kitの絶対パスと本人用の実行・Git・保存条件を確認して統合 |
| 新しい研究の条件を相談する | `research-workflow`と[planひな形](../templates/experiment-plan.md)・[Issue Form](../templates/experiment-plan.yml)。未承認・未確定のまま実装しない |
| 実装の前に似たcodeを探す | [find-existing](../skills/find-existing/SKILL.md)。探した範囲と再利用候補を返し、未発見を不存在と扱わない |
| 研究codeの正しさを読む | [research-review](../skills/research-review/SKILL.md)。既定は差分reviewで、修正・新しい分析・再実行を自動で始めない |
| 長時間処理の途中保存・再開を設計する | [preempt](../skills/preempt/SKILL.md)。保存状態・入力と設定の同一性・重複しない再開・軽い合成確認を扱う |
| 結果と図を残す | [結果サマリー](../templates/result-summary.md)。未確認の結果や画像をreview済みと書かない |
| 一般画像の生成・編集と実験図を選び分ける | [visual-assets](../skills/visual-assets/SKILL.md)。実在するtool、保持条件・透明度、実見、最終保存先・来歴を確認 |
| HTMLで説明する | [show-me](../skills/show-me/SKILL.md)と[HTMLひな形](../skills/show-me/assets/research-summary.html)。明示依頼時だけ作成し、実画像・表示・外部依存を確認 |
| 出力増加を抑える | [保持方針](../templates/storage-policy.md)。集約単位・必要なcheckpoint・保持根拠・枠を合意し、容量だけを理由に証拠を捨てない |
| 別の計算機へ引き継ぐ | [引継ぎひな形](../templates/remote-handoff.md)。移設先・承認・identity・分担・照合を記録 |

元envの`autoresearch`・`autonomous-experiment`・`debug-experiment`・`review-exp`・`standup`・`roadmap`・`research-reporting`等の専用skillとCLIは、このkitへ一括では入れていません。計画・review・報告の原則は同梱workflowとこの案内で使い、scheduler・queue・実績回収等を接続する場合は、そのenvの実装と導入状態を別途確認します。skill名を知っていることは実装の存在や実行許可の証拠ではありません。

## 10. 失敗時は分類してから対処する

対象のrun/job IDから実際のcommand・設定・終了状態と必要なログ部分を辿ります。可変の`latest`や他の担当のログを取り違えず、全文・全実験の一括収集を避けます。

| 分類 | 確認する証拠 | 対処の境界 |
|---|---|---|
| OOM | RAM／VRAMのどちらか、終了状態、対象設定と使用量 | 条件を保つ修正と、既存方針内の資源調整。batch・精度・系列長の無断変更や、同等性不明のchunk変更はしない |
| timeout | 進捗があったか、どの単位まで保存できたか | 進捗と同一性に根拠がある再開を検討。停止していた処理を時間だけ増やして再投入しない |
| code／config | traceback、承認planと実設定の不一致 | 必要な修正だけを承認済み条件へ合わせる。失敗が見えなくなるだけの除外や基準変更をしない |
| environment | 依存・container・mount・architecture・認証の実状態 | 必要な変更を示す。依存導入や共有環境の修理は別途承認 |
| data | 対象入力の欠損・破損・identity違い | 元入力を推測で修正せず、影響と不足を報告して依存処理を止める |
| node障害 | schedulerの障害記録と保存済み状態 | 原因・互換性と既存承認を確認する。共有設定や他人のjobを修理しない |
| unknown | 確認できた範囲と未解決点 | 推測の修正・再投入をしない。独立した読取りや合成確認を進める |

再投入前は残る承認範囲・条件・利用量・期限・holdと、重複した実行がないことを確認します。この表自体が修正・投入の許可や新しい実験条件にはなりません。完了済み結果を消して再実行guardを迂回しません。

## 11. 資源見積もりの根拠を残す

近いmodel・入力規模・長さ・batch・精度・処理の過去jobを先に見ます。RAMは対象stepの使用量、VRAMはframework等の観測を使い、SlurmのMaxRSSやhost RAMからVRAMを推定しません。既知のqueue容量を、実際のworkload使用量と混同しません。

worker数と数値libraryのthread数を合わせて見て、schedulerの割当CPUと実測のpeak RAM・I/Oの余裕に収めます。物理core数や空きGPUだけを根拠に並列・API要求を増やしません。入力を何度も全読込みせず、検証済み前処理の再利用、streaming、上限付きqueueを検討します。

所要時間は「queue待ち＋転送＋環境準備＋残件／同条件の実測速度＋回収」で見積もります。待ち時間・条件差・保存のoverheadは不確実性として示し、要求値・推奨値・根拠と確度を分けます。ここに架空の測定値や班全体の固定余裕率は設定しません。

証拠がなければ最小の代表probeを提案し、その実データ処理・投入は承認を受けてから行います。終了後のjob ID、workload identity、要求資源、elapsed、RAM、観測できたVRAM、状態・終了codeを次の見積もりの根拠にします。

## 12. 別計算機への引継ぎ

[引継ぎひな形](../templates/remote-handoff.md)で、CPU architecture・container・依存、共有mountとscratch、正規の出力先、容量・quotaを確認します。code・入力・model・設定の固定IDを照合し、hardware差が結果に影響する場合は承認済みの同等性基準を使います。

担当taskを明示して重複・欠落を調べ、実行中taskの所有権を勝手に移しません。回収はwriterが確定してから元と照合し、既存結果の上書きやscratch削除を一括で承認されたものとしません。別cluster・実転送・投入・環境変更・取消・削除は、それぞれ既存承認の範囲を確認します。

このkitはSSH設定・秘密鍵・実データ・転送／削除スクリプトを配布しません。引継ぎ文書だけで移設制御、停止確認、quota制限や科学的同等性が実装されたとは扱いません。

## 13. 原本と変更の追跡

Git運用の原本はenvの`agents/shared/skills/git-workflow/SKILL.md`と`agents/shared/claude/git.md`、研究・出力・通知の原本は同じenvの`agents/shared/instructions/`、`agents/README.md`、`docs/environment_tools.md`等です。探索・研究review・再開は対応する元skill、ひな形と切り分け表は計画・遠隔実験・debug・資源計画の原本を参照しています。採用元のcommitと共有版での調整は本repoのMANIFESTとGit履歴に残します。

共有のために個人envの全履歴・inventory・認証情報をコピーする必要はありません。班に必要な運用を文書とskillへ移し、実行コードの追加は本人用設定への対応と検証を済ませた範囲で行います。
