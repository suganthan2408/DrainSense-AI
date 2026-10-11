"""
DrainSense AI — Model evaluation

Computes classification metrics from verified WaterloggingOutcome records.
Only runs when at least MIN_OBSERVATIONS verified outcomes exist.
Reports limitations honestly.
"""

import logging

import numpy as np

logger = logging.getLogger("drainsense")


def compute_and_store_metrics(threshold: float = 50.0):
    """
    Compute precision, recall, F1, accuracy and confusion matrix
    from verified WaterloggingOutcome records.

    Returns a ModelEvaluation instance, or None if insufficient data.
    """
    from outcomes.models import WaterloggingOutcome, ModelEvaluation

    verified = WaterloggingOutcome.objects.filter(
        is_synthetic=False,
    ).exclude(
        report_source=WaterloggingOutcome.SOURCE_SYNTHETIC,
    ).exclude(
        outcome=WaterloggingOutcome.OUTCOME_UNKNOWN,
    ).select_related("risk_assessment")

    n = verified.count()
    if n < ModelEvaluation.MIN_OBSERVATIONS:
        logger.info("Only %d verified outcomes — need %d for metrics", n, ModelEvaluation.MIN_OBSERVATIONS)
        return None

    y_true = []
    y_pred = []

    for outcome in verified:
        actual = 1 if outcome.outcome == WaterloggingOutcome.OUTCOME_OCCURRED else 0
        if outcome.risk_assessment:
            predicted = 1 if outcome.risk_assessment.risk_score >= threshold else 0
        else:
            # Skip outcomes with no linked assessment
            continue
        y_true.append(actual)
        y_pred.append(predicted)

    if len(y_true) < ModelEvaluation.MIN_OBSERVATIONS:
        return None

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else None

    start = verified.order_by("observation_window_start").first().observation_window_start
    end = verified.order_by("-observation_window_end").first().observation_window_end

    evaluation = ModelEvaluation.objects.create(
        model_version="heuristic-v1",
        evaluation_period_start=start,
        evaluation_period_end=end,
        n_observations=len(y_true),
        n_positive=int(y_true.sum()),
        n_negative=int((1 - y_true).sum()),
        precision=round(precision, 4) if precision is not None else None,
        recall=round(recall, 4) if recall is not None else None,
        f1_score=round(f1, 4) if f1 is not None else None,
        accuracy=round(accuracy, 4) if accuracy is not None else None,
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        classification_threshold=threshold,
        limitations_notes=(
            f"Metrics based on {len(y_true)} observations. "
            f"Synthetic demonstration records are excluded from this evaluation. "
            f"The score threshold ({threshold}) was not tuned on a validation set. "
            f"These metrics should be interpreted cautiously given the small sample size "
            f"and the heuristic nature of the risk scorer."
        ),
    )

    logger.info(
        "Evaluation computed: n=%d precision=%.3f recall=%.3f f1=%.3f",
        len(y_true),
        precision or 0,
        recall or 0,
        f1 or 0,
    )
    return evaluation
