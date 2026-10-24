# research-agent-kit

研究用agentの共有設定です。GitHubによる実験管理・結果保存をまとめた `research-workflow` と8つの専門skill、共通rules、任意の呼出し回数カウンター、読み取り専用の点検ツールを収録しています。

このrepoをGitで取得し、内容を確認して必要な部分だけを導入します。個人用envの履歴・製品別権限設定・接続先・認証情報は持ち込みません。cloneしただけで、agent設定・通知・定期実行が有効になることはありません。

## この設定の特徴と実装範囲

| 特徴 | 具体的な運用 | 実装の範囲 |
|---|---|---|
| 必要な情報だけ読む | 依頼と近い規約を先に読み、関係するskill・資料へ進む | rulesとskillの指示。全資料を自動読込みする設定はない |
| 計画とGitHub Issueを対応付ける | 条件を確定したplanと同じ版をIssueへ反映し、その版の実装・実行承認を得る | 手順を収録。Issue自動投稿、実行ゲート、特定のGitHub Projectへの自動登録・認証は含めない |
| 証拠を一つの結果bundleにつなぐ | run・設定・入力・code commit・失敗や欠損を記録し、未変更のbundleを再利用する | 手順を収録。実験runner・scheduler連携・移設ツールは含めない |
| 図を作って確認する | 元表・描画コード・来歴とPNG/SVGを保存し、画像を実際に確認する | 手順と合成例。描画環境の自動導入や確認済み記録の自動発行はしない |
| 保存先と生成量を整理する | 成果はrepoのoutputs、正式報告はreportsを提案し、HTMLは依頼時だけ。集約表を使い、並行する説明ファイルを増やさない | rules・手順と出力点検。固定の99-agentパス、容量の強制制限、自動圧縮・削除は含めない |
| 点検の負荷を限定する | コード・環境参照・出力を明示範囲と上限付きで調べ、未検査を明示する | Python製の点検ツールを収録。下記の静的入口は対象コード・宣言済みcommandを実行しない |
| skill・hookの呼出しを数える | 任意有効化し、本文や引数を保存せずSQLiteに集計する | wrapper・observer・集計CLIを収録。Codexのskill計測は未対応 |
| 既存設定と承認を保つ | 選択したskill・rulesだけを採用し、上書き・外部操作の範囲を確認する | 指示を収録。OSの隔離、製品の権限変更、Slack通知・メンション、cron、自律workerは含めない |

rules・skillはagentへの指示です。追加しただけで任意のコードに実行制限を強制するものではありません。利用先の保護branch、実行ゲート、人間だけが行う操作、予算・停止指示を優先します。日報・週報や結果整理の依頼だけで、新たな実験は始めません。

## Gitから取得する

GitとPython 3.11以降を用意します。依存パッケージやagent本体は自動導入しません。点検用CLIはPOSIX環境を想定しています。各skillの数値処理・外部サービスには別途依存・認証が必要です。

```sh
git clone https://github.com/YoheiOhto/research-agent-kit.git
cd research-agent-kit
BUNDLE="$PWD"
git rev-parse HEAD
git status --short
python3 -B -m unittest discover -s tests -v
```

このclone自体が配布物です。env repoやtar.gz、別の配置コマンドは不要です。以下の例の `$BUNDLE` はclone先の絶対パスを指します。まだ共有先のagent設定は変更していません。

共有者が特定のcommitを案内した場合は、その版を選んでから内容を確認します。

```sh
REV='共有者が指定した公開済みコミットID'
git switch --detach "$REV"
git diff --exit-code "$REV" -- .
git status --short --untracked-files=normal
```

最後の状態表示に変更・未追跡ファイルがあれば、利用前に確認してください。テストは同梱manifestと各ファイル、skillの出典・ハッシュの整合も検査します。ただし、manifestとテストも同じ配布物の一部です。内容の一致確認は配布元を認証する署名ではなく、Git commitの信頼性は別に確認します。

### 更新・無効化・撤去

更新する場合は、公開済みの新しいcommitを別のcloneへ取得します。旧版を残して差分・テスト・採用先を確認し、選択したskill・rulesの参照だけを手動で切り替えます。導入先に独自変更があれば、上書きせず比較してください。

計測を止める場合は、自分が追加したobserver・wrapper設定と `RESEARCH_AGENT_USAGE=1` を外します。他の安全hookや既存設定は残します。集計DBや結果を自動削除しません。

撤去する場合も、自分が導入したskillとrules参照を識別し、原本との差分を確認してから利用先の手順で取り除きます。別の設定が混じる場所や履歴を一括削除するコマンドは提供しません。旧版へ戻す場合は、その版を確認してから同じ選択範囲を戻します。

## 入っているもの

| 場所 | 内容 |
|---|---|
| `rules/RULES.md` | 依頼の範囲、承認、研究条件、証拠の保全、記録を増やしすぎないための原則 |
| `skills/` | 研究ワークフロー1つと専門スキル8つ。各1コピーと、その参照資料・補助スクリプト |
| `hooks/usage_hook.py` | 明示的に有効にした呼出しの計測用wrapper・observer |
| `hooks/invocation_counts.py` | 計測結果の集計・表示 |
| `tools/static_code_check.py`、`tools/research_code_check.py` | 明示したソース範囲を検査する入口と内部実装。静的入口はプロジェクトの任意コマンドを実行しない |
| `tools/environment_audit.py` | 指定repoのvenv・キャッシュ参照を読む点検。削除・import・環境再構築はしない |
| `tools/inspect_outputs.py`、`tools/outputs_audit.py` | 指定repoの出力数・容量を上限付きで読む入口と内部実装。scheduler照会・圧縮・削除はしない |
| `LICENSE`、各スキルの`LICENSE`、外部スキルの`SOURCE.json` | 利用条件、出典。自作スキルの版・原本はmanifestで確認 |
| `MANIFEST.json` | 切出し元envのcommit、収録ファイルとハッシュ、共有版での変更。manifest自身は自己ハッシュに含めない |

| スキル名 | 何に使うか |
|---|---|
| `research-workflow` | 計画とIssueの対応付け、承認された実行、結果・PNG/SVGの保存、依頼時のHTML共有 |
| `biopython` | 配列やFASTAなどの生物情報ファイル、NCBI/PubMedを扱う |
| `experimental-design` | 比較、割付、交絡、反復など、データ収集前の実験設計を考える |
| `exploratory-data-analysis` | 対応形式のデータを範囲を限定して調べ、欠損や分布を確認する |
| `gget` | 遺伝子情報などを複数の生物情報サービスで調べる |
| `scikit-learn` | 前処理、機械学習、評価、パラメータ探索を組み立てる |
| `statistical-analysis` | 仮定を確認し、比較、効果量、不確実性を分析する |
| `statistical-power` | 研究計画時の検出力や必要サンプル数を検討する |
| `yomiyasu` | AIが書いた日本語を、意味と条件を保って推敲する |

依存パッケージ、対応形式、外部サービスの条件は個別に確認し、コピー先でもライセンスと出典を残します。

## GitHubで実験を管理し、結果を残す

`research-workflow`は、次の運用を共有するための自作スキルです。利用先の規約を優先し、具体的な保存場所や実行条件は計画時に決めます。

1. チャットで研究目的・比較・条件を確定し、版を識別できる`plan.md`を正本として保存します。
2. 投稿を依頼された対象repoのIssueに、同じ版の計画、比較、成果物、制限を反映します。Issueを建てただけでは実装・実行の承認にはなりません。
3. 対象版への明示承認後に実装・実行します。実際のcode commit、設定、入力、run/job ID、出力先を記録します。
4. 結果と図を検証し、planの実行状況とIssueから同じ結果bundleへリンクします。条件を変える場合は旧版を残して相談します。

Issueは計画・判断・進捗の索引に使います。生データや重みを一括で添付したり、GitHubへ自動投稿したりする機能は含みません。Issueの更新・closeも、利用者が許可した対象と範囲で行います。

保存場所が未定の場合に提案する構成は次のとおりです。既存の成果を移動する指示ではありません。

```text
experiments/<id>/plan.md                    計画の正本・実行状況
outputs/<experiment>/<run>/                 各runの結果・ログ等
outputs/<experiment>/reports/<bundle>/      比較表・図・再現用コード・来歴・図の確認記録
reports/daily/ または reports/weekly/       依頼された日報・週報
```

| 出力 | 保存・確認するもの |
|---|---|
| 結果bundle | 指標・比較表、失敗や欠損、入力の識別情報、code commit、実行設定、再現手順。未変更の結果は同じbundleを再利用し、変更時は旧版を残す |
| PNG／SVG | PNGのプレビューと、図に適した場合のSVG。元の表・描画コード・設定・来歴も保存し、画像を実際に開いて軸・単位・凡例・欠損・表との一致を確認する。確認できなければdraftとする |
| 説明用HTML | 明示的な依頼があるときだけ作成。保存先は利用者と合意し、個人環境の固定パスは仮定しない。確認済みの図と説明を自己完結のページに含め、元のPNG／SVGや結果bundleも保持する |

詳細は導入先の`skills/research-workflow/SKILL.md`にあります。これは運用手順であり、Issueの自動操作、ジョブ投入の許可条件を強制する仕組み、作図ライブラリや画像検証プログラムを導入するものではありません。結果整理の依頼だけで、新しい実験や解析を始めることもありません。

最初の手順を確認するための合成例は、導入先の`skills/research-workflow/references/example.md`にあります。計画・Issue下書き・6行のCSV・任意の描画コード・来歴・未確認の目視記録をつなぎます。実研究の結果や実行承認ではありません。描画には別途Matplotlibが必要で、自動導入やIssue投稿は行いません。

## 必要な範囲だけ点検する

ソースの検査例です。`/対象repo`を実際の場所へ、`lib`を調べる相対パスへ置き換えます。

```sh
python3 -I -S "$BUNDLE/tools/static_code_check.py" --root /対象repo --scope-only --include lib
```

この入口はGit・shell・宣言済みのテストコマンドを起動せず、Python構文・AST・秘密情報の形式などを検査します。上限は既定で200ファイル、ソース合計8MiB、5,000項目です。打切り・読取り失敗は不完全として終了コード2を返します。shell構文・一般のYAML・TOMLなど、未検査の項目はJSONで明示します。内部実装の`research_code_check.py`を直接起動する従来のfast/full経路では、プロジェクト設定のコマンドが動くことがあるため、共有版の静的検査には上記の入口を使います。

`-I -S`は、検査対象repoや環境変数によるPython起動時のコード読込みを避けるためです。結果は標準出力へ返し、ソースの実行・import、依存導入、画像や結果の生成はしません。検査合格だけで研究の妥当性や実行許可を判断しないでください。

Python環境の参照だけを点検する例です。

```sh
python3 -I -S "$BUNDLE/tools/environment_audit.py" --repo /対象repo --max-root-entries 2048 --json
```

指定repoの共有venv・切れた参照・古い環境名・uvキャッシュの候補を確認します。パッケージのimport、GPU利用確認、削除、再構築は実行しません。調べていない領域は不明として残し、利用先の保存・環境管理方針と合わせて判断してください。

出力数・容量は次の読み取り専用入口で点検できます。

```sh
python3 -I -S "$BUNDLE/tools/inspect_outputs.py" --repo /対象repo --json
```

`outputs/<experiment>/<run>/`形式を対象に、5,000項目・2秒の走査枠でmetadataを調べます。時間は走査の区切りで確認するため、OSの読込み待ちなどで実時間が延びることはあります。打切り時の件数・容量は全体の合計ではありません。ハードリンクの重複や圧縮済み形式を区別し、scheduler照会や圧縮・削除は行いません。保存期間の候補は自動削除の許可ではなく、実際の保持方針は利用者が決めます。形式が違う出力や別の保管領域は、この点検の対象外として残ります。

## 自分の設定に取り入れる

`rules/RULES.md`を読み、管理者と既存ルールとの整合を確認します。ルールの担当を一つに決め、厳しい承認条件や人間だけが行う操作を保ちます。

Codexの既存`AGENTS.md`、Claudeの既存`CLAUDE.md`へ、導入先の`rules/RULES.md`を読む参照を追記します。全体を置き換えないでください。指示の追加だけでは実行制限を実装できません。

必要なスキルだけを、Codexなら`${CODEX_HOME:-$HOME/.codex}/skills/`、Claude Codeなら`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/`へコピーします。**同名があればコピーせず比較してください。** `statistical-power`の例です。

```sh
SKILL=statistical-power
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"  # Claudeは上記の保存先に変更
mkdir -p "$SKILLS_DIR"
if [ ! -e "$SKILLS_DIR/$SKILL" ] && [ ! -L "$SKILLS_DIR/$SKILL" ]; then
  cp -R "$BUNDLE/skills/$SKILL" "$SKILLS_DIR/"
else
  echo '同名の保存先があるため、コピーしません'
fi
```

Gitから取得する段階では既存設定を変えません。手動採用では、選んだ指示・スキルだけを追加します。個人用の権限設定、env固有パス、計算機設定、認証情報は含めません。パッケージ・モデル・データを変更せず、自律実行、実験、ジョブ投入、外部通信も許可しません。必要な導入・実行は受入先の承認に従います。

## 利用回数を必要な場合だけ数える

計測ツールもPython 3.11以降の標準ライブラリで動きます。`RESEARCH_AGENT_USAGE=1`を指定した呼出しから記録を始め、`${XDG_STATE_HOME:-$HOME/.local/state}/research-agent/invocations.sqlite3`のSQLiteデータベース1つにUTCで記録します。prompt、コマンド本文、rawイベント、呼出しごとのファイルは保存しません。ロック競合やI/O障害で記録を失うことがありますが、安全hookの判定は変えません。

この有効化変数は`usage_hook.py`による自動観測用です。`invocation_counts.py record`は利用者が明示的に1件を書き込む別の操作で、この変数に関係なく記録します。読むだけの場合は`report`を使います。

| client | 数える範囲 | 限界 |
|---|---|---|
| Claude Code | `Skill`ツールの試行・成功・失敗、導入済みスキル名に一致したコマンド展開 | 展開は実行成功の証明ではない |
| Codex | 手動でwrapperを付けたhookの起動 | スキル呼出しの計測は未対応 |
| Antigravity | 手動でwrapperを付けたhookの起動 | native連携は未検証。Gemini CLIとは別。スキルは数えない |

既存hookを計測する例です。パスとhook名を置き換え、clientに応じて`claude`または`antigravity`を指定します。

```sh
RESEARCH_AGENT_USAGE=1 python3 '/導入先/agent-kit/hooks/usage_hook.py' wrap --client codex --profile portable --name existing-guard -- /既存hookの絶対パス/guard.sh
```

元のhookのstdin・stdout・stderr・終了状態を保ちます。計測helper自体をwrapせず、安全hookも残してください。

Claudeのスキル計測は既存settingsの`hooks`配列へobserverを追加します。各イベントのcommandは次の同じ文字列です。

```sh
RESEARCH_AGENT_USAGE=1 python3 '/導入先/agent-kit/hooks/usage_hook.py' observe --client claude --profile portable
```

| event | matcher |
|---|---|
| `PreToolUse` | `^Skill$` |
| `PostToolUse` | `^Skill$` |
| `PostToolUseFailure` | `^Skill$` |
| `UserPromptExpansion` | `.*` |

`PreToolUse`は試行で、後で拒否されることもあります。直接入力した`/skillname`は`Skill`ツールを通らないため、4番目も必要です。MCP promptや、導入済みスキル名と一致しないコマンド展開は除きます。[Claude公式資料](https://code.claude.com/docs/en/hooks)の形式で、既存の安全hookを上書きせず追加します。設定は自動変更しません。

集計を見たいときだけ実行します。

```sh
python3 "$BUNDLE/hooks/invocation_counts.py" report --json
```

有効化後の観測回数です。未計測や過去の利用をゼロとせず、重複のない実行総数ともみなさないでください。ファイル読取り、hook起動、スキル選択、作業完了は別です。回数だけで有用性・正しさは判断できず、会話への自動添付も不要です。


## 出典と検証範囲

元の実装は `YoheiOhto/env` のcommit `d0806dd69afbed63f99a56eea377ca421c7022bc` から、第三者向けに選択済みのファイルだけを切り出しました。この元commitは来歴であり、このrepoの単体利用に元envの取得は不要です。元envの全設定や過去の履歴の公開可否を保証するものでもありません。

外部由来の8 skillは原本を改変せず、各LICENSE・SOURCE.jsonと固定revision・ハッシュを保持しています。自作research-workflowと点検・計測コードの条件はrootのLICENSEを参照してください。yomiyasuのUnicode関連の告知も同梱します。

同梱テストは、配布物の整合、Python構文、静的点検の非実行性、環境・出力の点検、計測の任意有効化などを小さい合成入力で確認します。実機のagent起動・認証・skillのnativeイベント・外部サービス・GPU・scheduler・実研究の正しさを保証しません。

合成例のCSVと描画コード構文は確認していますが、初回切出し環境にはMatplotlibがないため、描画と画像の目視確認は未実施です。作図例はこの制限を保ったdraftとして利用してください。
