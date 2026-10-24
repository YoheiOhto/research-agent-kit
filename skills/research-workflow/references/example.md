# 合成データで流れを確認する例

架空の手順例で、科学的結果・実行依頼・承認ではありません。実データ・モデル呼出し・投稿なし。実研究では受入先の条件・runner・承認を確認します。

## 計画とIssueの下書き

```text
状態: 合成例の草案。研究実行は未承認。
目的: 架空スコアを表と図で追跡する。
比較: baseline / candidate。小さい値ほど低いスコア。
入力: 下記6行（3ケース×2方式）、手作りの値。
分割・モデル・prompt・学習・乱数: 該当なし。推論も乱数生成も行わない。
集計: 3ケースを全て表示し、方式別の算術平均だけを補助表示する。
不確実性: 信頼区間・有意差なし。母集団へ推論しない。
品質条件: 重複・欠損・追加行を拒否。スコアは有限の0〜1。
停止: 入力不一致、描画失敗、出力先が既存、必要な依存がない場合。
成果物: CSV、描画コード、PNG、SVG、出典。目視確認前はdraft。
資源・期限・容量: 採用時に利用者と決める。未承認。
## 実行状況
まだ実行・目視確認していない。承認済み条件はこの見出しより上を保全する。
```

Issueは下書きです。対象への投稿許可が必要です。実研究では確定した計画の同じ版を反映し、実装・実行の明示承認を得ます。

```text
タイトル案: [DRAFT / SYNTHETIC] 保存表から図までの追跡例
計画: experiments/demo/plan.md（版の識別子は実物を確認して記録）
対象: 架空の3ケース×2方式。研究結果や性能改善の主張はしない。
成果物案: outputs/demo/reports/demo-v1/
完了条件: 表・コード・図・出典の対応と実見記録。
Issue URL / Git SHA / job ID: 未記録。
承認: この下書きは承認記録ではない。
```

## 保存表と任意の描画例

`metrics.csv`は`synthetic`で、実ジョブの成功記録ではありません。平均baseline=0.50、candidate=0.40は作った値の要約で、性能改善の証拠ではありません。

```csv
case,method,score,status
A,baseline,0.40,synthetic
B,baseline,0.50,synthetic
C,baseline,0.60,synthetic
A,candidate,0.30,synthetic
B,candidate,0.40,synthetic
C,candidate,0.50,synthetic
```

`plot.py`はPython 3.11以降とMatplotlibを使う説明用コードです。依存がなければ止まり、自動導入しません。ここでは実行していません。

```python
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

source, output = map(Path, sys.argv[1:])
raw = source.read_bytes()
reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
if reader.fieldnames != ["case", "method", "score", "status"]:
    raise ValueError("bad CSV columns")
rows = list(reader)
expected = {(case, method) for case in "ABC"
            for method in ("baseline", "candidate")}
if len(rows) != 6 or {(r["case"], r["method"]) for r in rows} != expected:
    raise ValueError("missing, extra or duplicate keys")
if any(r["status"] != "synthetic" or None in r for r in rows):
    raise ValueError("not the synthetic fixture")
scores = {(r["case"], r["method"]): float(r["score"]) for r in rows}
if any(not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()):
    raise ValueError("invalid score")

output.mkdir(parents=True, exist_ok=False)
(output / "metrics.csv").write_bytes(raw)
(output / "plot.py").write_bytes(Path(__file__).read_bytes())
fig, ax = plt.subplots(figsize=(5, 3))
for index, method in enumerate(("baseline", "candidate")):
    values = [scores[case, method] for case in "ABC"]
    ax.scatter([index] * 3, values, label=f"{method}: 3 synthetic cases")
    ax.plot(index, sum(values) / 3, marker="_", color="black", markersize=20)
ax.set(xticks=[0, 1], xticklabels=["baseline", "candidate"],
       ylim=(0, 1), ylabel="Synthetic score (unitless)",
       title="Synthetic demonstration; black bars = means; no CI")
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(output / "figure.png", dpi=150)
fig.savefig(output / "figure.svg")
plt.close(fig)
names = ("metrics.csv", "plot.py", "figure.png", "figure.svg")
provenance = {
    "status": "synthetic-draft", "python": platform.python_version(),
    "matplotlib": matplotlib.__version__, "git_commit": None,
    "issue_url": None, "job_ids": [], "visual_review": "pending",
    "sha256": {n: hashlib.sha256((output / n).read_bytes()).hexdigest()
               for n in names},
}
(output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
```

合成例を確認すると決めた場合は`python3 plot.py metrics.csv outputs/demo/reports/demo-v1`です。既存先は拒否し、部分出力は保全します。実研究ではGit SHA・入力・設定・job IDの実物を記録します。

## 目視確認と共有

PNGと描画したSVGで、軸・凡例・欠け・表との対応を確認します。SVGの文字列確認だけでは実見になりません。`review.md`の形式例です。

```text
対象: figure.png / figure.svg と provenance.json の実際のハッシュ
確認者・日時: 実際に確認した後で記録
確認状態: pending（まだ開いていない）
確認内容: 3ケース×2方式、0〜1の軸、単位、平均、凡例、欠け、SVG表示
問題と修正: 未確認。修正後は新しいファイルと出典を再確認する。
```

有効なreview receiptではありません。実見前はdraftです。同じ内容は再利用し、変更時は旧版を残します。

通常はチャットで案内します。HTMLは明示依頼時だけ保存先を合意し、実見済みの図で自己完結させます。CSV・コード・PNG/SVG・出典はbundleに保全し、分析やページを自動で増やしません。
