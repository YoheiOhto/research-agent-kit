---
name: git-workflow
description: 水野班向けの研究repoで、作業branch、変更の保存、個人PR、承認された組織反映を扱う。gstart・wstart・gfinish・gpushの使い分け、PR作成とmergeの区別、Git操作の失敗時に使う。実験の実行承認は扱わない。
license: MIT
---

# Git / GitHub の作業

これは大戸のenvにある運用を、水野班の他の利用者も採用できる手順として整理したskillである。班全体の正式規約や外部書込みの許可を新たに定めるものではない。対象repoの規約、管理者が指定した反映先、利用者の既存承認を確認する。

現在のbranch、未コミット変更、担当、実行中ジョブが読むcheckoutを確認する。他の担当の変更をcommitせず、稼働中のcheckoutを切り替えない。必要なら別の作業領域を準備する。個人forkの`origin`を使い、remote名`upstream`には読取りを含め接続しない。

## 利用前に確認するもの

個人GitHubアカウント、対象fork、`machine/<host>`、組織側の確認用branchを識別する。helperが導入されている場合も、自分のアカウントと対象repoに対応しているか確認する。このskillにhelperの実装は付属しない。大戸用envの`gpush`や`setup_git`を他の利用者へそのまま適用しない。

導入済みで受入先の方針に対応したenv helperは、非対話shellでは次の入口を使う。

```bash
bash "$ENV_DIR/tools/agents/shellfn.sh" --repo "$PWD" --list
bash "$ENV_DIR/tools/agents/shellfn.sh" --repo "$PWD" <function> [args...]
```

`ENV_DIR`はその利用者が確認したenvの絶対パスである。関数が`command -v`に出ないだけで未導入と決めない。一方、対応するwrapperや本人用設定がなければ変更操作を止め、必要な導入・設定を説明する。interactive shellや関数ファイルを直接sourceして拒否を迂回しない。

## 個人repoの流れ

```text
個人main → machine/<host> → work/<task>
                              │ 編集・検証・commit
                              ↓
                         machine/<host> → 個人main宛のPR
                                               │ 対象PRの明示承認
                                               ↓
                                            個人main
```

| 状態 | 導入済みhelperで行う操作 |
|---|---|
| mainを受け取り作業を始める | `gstart`でmainをff-only更新し、machine branchを準備する。未保存変更や稼働ジョブがあるcheckoutは先に保護する |
| machineから編集を始める | `wstart <task-name>`でwork branchを作る。main/master/machine上で編集・commitしない |
| 変更を保存する | 対象ファイルだけを明示してstageし、work上でcommitする。生成・構文・関連テストを済ませる |
| workをmachineへ戻す | 下記の変更サマリーを示し、その範囲の承認後、work上から`gfinish`を呼ぶ。workを取り込み、完了したwork branchを削除する |
| 個人PRを作る | machine上から`gpush "<変更概要>"`。本人のoriginへpushし、base=mainのPRを作成・更新して止まる。自律実行の許否は受入先が採用した規約に従う |
| merge後に最新版を受け取る | `gsync`でmainを受け取る。再編集には`gstart`・`wstart`を使う |

`gfinish`の前に、現在のmachine branchからのcommit一覧、変更ファイルと行数、何を変えたか・理由・検証・残る制限をチャットで示す。履歴・差分の範囲を限定し、他の担当の変更を含めない。既に同じ操作が対象と範囲を定めて明示承認されていれば、同じ承認を再度求めない。

大戸用envでは、本人のmachine branchをpushして個人main宛のPRを作る制約付き`gpush`が常時許可されている。この例を他の利用者の外部操作許可へ置き換えない。PRを作る許可はmergeの許可ではない。対象PRを特定した依頼があるときだけ、そのPRをmergeする。

workの退避と通常PRも分ける。大戸用envの`gpush --backup`は既定previewで、実際の`--apply`は保存先を承認された人が行う。agent用wrapperではpreviewのみ許可される。未対応の受入先で同じ挙動を仮定しない。既存のpre-push hookは外さず、阻害理由と保存済みcommitを報告する。

PR本文は、具体的な問題と変更後の挙動、検証、残る制限を説明する。CLIへ複数行の本文を渡す場合は、実際の改行を持つファイルを`--body-file`で指定する。Issueがある場合は、その計画・判断・結果と対応付ける。

## 個人forkから組織への反映

個人PRが終わっても組織への反映は終わっていない。一般形は次のとおりで、確認用branchは管理者が各利用者・repoについて決める。

1. 個人`machine/<host>` → 個人`main`のPR。
2. 個人`main` → `mizuno-group/<repo>`の指定された確認用branchへのPR。
3. その確認用branch → 組織`main`への別PR。

大戸の実際の対応例は次のとおり。

```text
YoheiOhto/<repo>:main
  → mizuno-group/<repo>:dev_ohto
  → mizuno-group/<repo>:main
```

各矢印は別のPRとmergeである。他のメンバーに`dev_ohto`を流用しない。組織側branchがない場合は、人が組織mainから準備する。勝手に`dev`で代用したり、組織mainへ直行したりしない。

組織の各段階では、PR作成とmergeのそれぞれについて対象と既存承認の範囲を確認する。個人PRの承認から組織への操作を推定しない。組織repoへ直接commit・pushしない。agentによる`gupstream`やremote名`upstream`の利用は禁止し、必要な組織同期は人が行う。

## Issue・Projectと失敗時の扱い

Issueは計画・判断・進捗・結果の索引、Projectは複数Issue等の整理先である。Issueを作成しても特定Projectへ自動所属するとは限らない。Projectの所有者・URL・番号・利用権限は受入先で確認する。このskillは自動登録や認証情報を提供しない。

新しい問題のIssueには、再現条件・影響・期待動作・確認した証拠・未確認事項を示す。既存の同じIssueがあればそちらを使う。投稿先と許可範囲を確認し、公開できない入力・ログ・認証情報は添付しない。実験のIssue作成は実行承認ではない。

操作失敗は、未保存変更、ff-only不能、衝突、生成物のずれ、origin所有者の検証、認証・権限などに分ける。raw Gitでのbranch作成、`reset --hard`、強制push、rebase、強制branch削除、`git config`、`.git/`の直接操作で通さない。両側の変更と承認範囲を確認し、独立して進められる読取りやローカル検証を続ける。
