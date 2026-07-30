"""Confusion matrix and per-class precision/recall/F1, with no extra dependencies (no scikit-learn).

Shared by scripts/evaluate.py and scripts/calibrate_threshold.py so both report metrics the
same way instead of each computing accuracy ad hoc.
"""
from dataclasses import dataclass


@dataclass
class ClassificationReport:
    labels: list
    confusion: dict  # confusion[expected][predicted] = count
    per_class: dict  # per_class[label] = {"precision", "recall", "f1", "support"}
    accuracy: float
    macro_f1: float
    total: int

    def render(self) -> str:
        lines = []

        header = "expected \\ predicted".ljust(22) + "".join(label.ljust(11) for label in self.labels)
        lines.append(header)
        for expected in self.labels:
            row = expected.ljust(22)
            row += "".join(str(self.confusion[expected][predicted]).ljust(11) for predicted in self.labels)
            lines.append(row)

        lines.append("")
        lines.append(f"{'label':<10}{'precision':>10}{'recall':>10}{'f1':>10}{'support':>10}")
        for label in self.labels:
            m = self.per_class[label]
            lines.append(
                f"{label:<10}{m['precision']:>10.3f}{m['recall']:>10.3f}{m['f1']:>10.3f}{m['support']:>10d}"
            )

        lines.append("")
        lines.append(f"accuracy: {self.accuracy * 100:.1f}% ({self.total} samples), macro-F1: {self.macro_f1:.3f}")
        return "\n".join(lines)


def classification_report(expected: list, predicted: list, labels: list) -> ClassificationReport:
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")

    confusion = {e: {p: 0 for p in labels} for e in labels}
    for e, p in zip(expected, predicted):
        # Anything outside the known label set (e.g. an unexpected model label) is dropped
        # into the confusion matrix as-is only if both sides are known; otherwise skipped.
        if e in confusion and p in confusion[e]:
            confusion[e][p] += 1

    per_class = {}
    f1_scores = []
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[e][label] for e in labels if e != label)
        fn = sum(confusion[label][p] for p in labels if p != label)
        support = sum(confusion[label].values())

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        if support > 0:
            f1_scores.append(f1)

    total = len(expected)
    correct = sum(1 for e, p in zip(expected, predicted) if e == p)
    accuracy = correct / total if total else 0.0
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return ClassificationReport(
        labels=labels, confusion=confusion, per_class=per_class, accuracy=accuracy, macro_f1=macro_f1, total=total
    )
