from app.config import settings

SCAM_PROTOCOLS: dict[str, list[str]] = {
    "irs_impersonation": [
        "Do not click any links in this email.",
        "Do not call any phone number listed in this email.",
        "The real IRS only contacts you by postal mail first.",
        "If worried, call the IRS directly at 1-800-829-1040.",
        "You can report this email at reportphishing@irs.gov.",
    ],
    "tech_support": [
        "Do not call the phone number in this email.",
        "Do not allow anyone to remotely access your computer.",
        "Microsoft, Apple, and Google never contact you about viruses by email.",
        "Close the email and run your own antivirus if worried.",
    ],
    "lottery_prize": [
        "You cannot win a lottery you did not enter.",
        "Do not send any money or gift cards to claim a 'prize'.",
        "Do not share your bank account or Social Security number.",
        "Report this to the FTC at ReportFraud.ftc.gov.",
    ],
    "bank_fraud": [
        "Do not click any links — go directly to your bank's website by typing it yourself.",
        "Do not provide your password, PIN, or account number via email.",
        "Call the number on the back of your bank card to verify any issue.",
    ],
    "romance_scam": [
        "Be cautious of anyone you have never met in person asking for money.",
        "Do not send gift cards, wire transfers, or cryptocurrency to online contacts.",
        "Talk to a trusted family member or friend before sending anything.",
        "Report to the FTC at ReportFraud.ftc.gov.",
    ],
    "package_delivery": [
        "Do not click any tracking links in this email.",
        "Visit the carrier's official website directly to check your package.",
        "Legitimate carriers do not ask for payment via email to release a package.",
    ],
    "grandparent_scam": [
        "Hang up or stop replying and call the family member directly on a number you already have.",
        "Never wire money or buy gift cards based on an urgent email request.",
        "Verify any emergency with a second trusted family member before acting.",
    ],
    "not_scam": [],
}


def combine_risk_score(
    similarity: dict,
    classifier: dict,
    url_reputation: dict,
    header_anomaly_score: float,
) -> dict:
    w = settings
    score = (
        similarity["score"] * w.weight_similarity
        + classifier["confidence"] * w.weight_classifier
        + url_reputation["score"] * w.weight_url
        + header_anomaly_score * w.weight_headers
    )

    # Override: any malicious URL alone pushes score above flag threshold
    if url_reputation.get("malicious_urls"):
        score = max(score, 0.85)

    score = round(min(score, 1.0), 4)
    risk_pct = round(score * 100, 1)

    scam_type = classifier.get("label") or similarity.get("cluster_label") or "unknown"
    if scam_type == "not_scam" and score >= settings.flag_threshold:
        scam_type = similarity.get("cluster_label") or "unknown"

    if score >= settings.flag_threshold:
        risk_label = "flagged"
    elif score >= settings.review_threshold:
        risk_label = "review"
    else:
        risk_label = "clean"
        scam_type = None

    protocol = SCAM_PROTOCOLS.get(scam_type or "", [])

    return {
        "risk_score": risk_pct,
        "risk_label": risk_label,
        "scam_type": scam_type if risk_label != "clean" else None,
        "protocol_steps": protocol,
        "signals": {
            "similarity_score": similarity["score"],
            "classifier_label": classifier.get("label"),
            "classifier_confidence": classifier.get("confidence"),
            "malicious_urls": url_reputation.get("malicious_urls", []),
            "header_anomaly_score": header_anomaly_score,
        },
    }
