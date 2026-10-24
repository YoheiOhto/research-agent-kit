# 実験計画のひな形 — 未承認の草案

必要な条件を利用者と相談し、既存planへ取り込むためのひな形です。このファイル自体は実験・実行承認ではありません。未確定のnullや未記入欄をAIの既定値で埋めず、適用外には具体的な理由を記録します。

条件JSONは元envのschema_version 1を参照しています。本kitにexperiment_gate.py・runx・承認記録の生成機能はありません。受入先に対応版が導入されていればその検査を使い、他のprojectの形式がある場合はそちらを優先します。コピーしただけで検査済み・実行可能とは扱いません。

## 目的・比較と判定

研究目的、仮説検証／探索の区別、対象集団と入力版、baseline、支持・棄却・不明の判定、行わないことを合意します。結果の良し悪しと、leakageなし・件数一致等の品質基準を分けます。

## 確定する実験条件

以下は全て未確定です。arrayは承認対象を明示列挙するために使い、探索の許可としません。入力・model・prompt・依存・計算場所は固定した識別情報を残します。

```experiment-conditions
{
  "schema_version": 1,
  "hypothesis": {
    "objective": null,
    "study_type": null,
    "hypotheses": null,
    "baseline": null,
    "decision_rules": null,
    "non_goals": null
  },
  "data": {
    "identity": null,
    "sample_size": null,
    "sample_size_rationale": null,
    "inclusion_exclusion": null,
    "labels": null,
    "input_paths": null,
    "prior_access": null
  },
  "split": {
    "unit": null,
    "boundaries": null,
    "leakage_controls": null,
    "tuning_rule": null,
    "test_access_rule": null
  },
  "preprocessing": {
    "steps": null,
    "missing_values": null,
    "tokenization": null,
    "truncation": null,
    "retrieval": null
  },
  "model": {
    "checkpoint": null,
    "revision": null,
    "tokenizer": null,
    "tokenizer_revision": null,
    "trainable_components": null,
    "initialization": null
  },
  "prompt": {
    "templates": null,
    "content_refs": null,
    "generation_settings": null,
    "renderer": null
  },
  "hyperparameters": {
    "batch": null,
    "optimizer": null,
    "schedule": null,
    "training_length": null,
    "stopping_selection": null,
    "precision": null,
    "quantization": null,
    "selection_rationale": null
  },
  "seeds": {
    "values": null,
    "repetitions": null,
    "determinism": null
  },
  "evaluation": {
    "primary_metrics": null,
    "secondary_metrics": null,
    "aggregation": null,
    "uncertainty": null,
    "multiple_comparisons": null,
    "denominator": null,
    "failure_handling": null,
    "quality_checks": null,
    "independent_verification": null
  },
  "variants": {
    "tasks": null,
    "total_tasks": null,
    "baseline_id": null,
    "selection_rule": null
  },
  "resources": {
    "profile": null,
    "location": null,
    "per_job": null,
    "total_limits": null,
    "valid_until": null
  },
  "environment": {
    "runtime": null,
    "dependencies": null,
    "allowed_files": null,
    "shared_library_impact": null
  },
  "outputs": {
    "locations": null,
    "preservation": null,
    "resume_policy": null
  },
  "debug_policy": {
    "allowed_repairs": null,
    "retry_allowed": null,
    "resume_allowed": null,
    "equivalence_requirements": null
  },
  "stop_conditions": {
    "completion": null,
    "budget_deadline": null,
    "correctness_failure": null,
    "consultation_triggers": null
  }
}

```

## 実装と検証の範囲

既存runner・lib・例の探索結果、再利用先、必要な編集対象と理由、成果物・依存関係・完了条件を決めます。新しい実験の実装は同版への承認後です。実際の設定合成・CLI上書き後の値を計画と照合する方法を記録します。

資源は初期見積もりと厳守上限を分け、実行環境・account・quota・他の利用者・API要求数/token/費用・並列/retry・deadlineを確認します。資源だけの変更の許否も受入先の既存方針に従い、大戸の個人予算例外を全員へ流用しません。新しいprobe、実転送、依存変更、取消・削除はそれぞれ別の承認範囲です。

出力の種類・保存先・集約単位・checkpoint・保持枠・超過時の対応を決めます。必要ならstorage-policy.mdの欄をここへ統合します。遠隔実行が必要な場合だけremote-handoff.mdの確認を加え、毎回全templateを複製しません。

## 計画reviewと未確定事項

標本数・条件の選び方、既に見たデータ／結果、split、品質・不確実性・多重比較、失敗・欠損を確認します。実行前のreview結果と人が決めることを分けます。

未確定事項：未記入。全て合意した場合だけ「なし」と記録します。検査合格・Issue・label・reviewは人の実装／実行承認ではありません。

## Issueと承認対象

- 実験ID・plan版・固定識別情報：未記入
- 同じ版を反映する対象研究repoのIssueまたは投稿案：未記入
- 実装・実行の範囲、正確な命令、場所・期限・retry/resumeの許否：未確定
- 承認状態：未承認。実際の人の発言・対象版・範囲を確認するまで変更しない

承認済み本文と実行状況の境界は次の見出しです。科学的条件を変更する場合は旧版を保ち、新版を相談・承認します。資源だけの調整は受入先の既存方針を確認し、承認済み部分を改変せず状況欄へ記録します。

## 実行状況

未実行。承認後に実装revision、実設定との照合、入力・環境のidentity、実際のcommand/run/job ID、資源、結果、失敗・修正・再開の事実を追記します。承認前に成功記録や架空の承認を書きません。

結果表・元表・描画code・PNG/SVG等・来歴と実画像の確認を一つの正本bundleへつなぎます。結果は未確認の間draftとし、projectが要求する最終化を済ませてから結論を採用します。必要ならresult-summary.mdの欄をこの記録やbundleへ取り込みます。
