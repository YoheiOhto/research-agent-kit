# Git / GitHub の採用ルール

これは水野班向けに共有する大戸の運用例です。対象repoの管理者が定めた保護・権限と、利用者が採用した手順を優先します。配布物を読むだけでは、Git設定・hook・外部操作の権限は変わりません。

- 編集・commitは`work/<task>`で行い、`main`・`master`・`machine/*`を直接編集しない。他の担当の変更と、実行中ジョブが読むcheckoutを保護する。
- `machine/<host>`はマシンごとの作業を集める固定branch、`main`はPRで採用した変更の統合先とする。`wstart`・`gfinish`等は、利用者に対応した実装が導入済みの場合だけ使う。
- ローカルの作業完了とGitHubへの公開、PR作成とPRのmergeを分ける。変更・検証・影響を示し、既存の承認を同じ対象・範囲で再利用する。PRのmergeは対象PRを特定した明示依頼がある場合だけ行う。
- 組織repoへ直接commit・pushしない。個人forkから、管理者が指定した組織の確認用branch、組織mainへの順にPRで進める。個人PRの承認を組織のPR・mergeへ流用しない。
- `YoheiOhto → mizuno-group:dev_ohto → mizuno-group:main`は大戸の対応関係であり、他のメンバーに`dev_ohto`を割り当てない。組織branchがない場合は管理者へ確認する。
- agentはremote名`upstream`へ読取りも含め接続せず、`gupstream`も使わない。必要な組織同期は人が行う。
- agentはraw Gitでのbranch作成、rebase、強制push・強制削除、`git config`、`.git/`の直接操作で手順やguardを迂回しない。必要なhelperがない場合は変更操作を止め、準備すべきものを説明する。
- Issue・Project・PRは関連付けても別の対象である。作成・更新・所属変更は、許可されたrepo・Projectと操作の範囲でだけ行う。Issue作成やラベル付与を実験の実行承認と解釈しない。

Git操作の前に、[git-workflow skill](../skills/git-workflow/SKILL.md)で、状態に合う入口、変更サマリー、個人PRと組織反映の段階を確認します。利用者別の準備と実装上の制限は[水野班向け運用案内](../docs/mizuno-lab.md)を参照してください。
