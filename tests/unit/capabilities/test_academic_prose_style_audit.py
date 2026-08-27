from __future__ import annotations

from research_skills_os.capabilities.academic_prose_style_audit.gates import audit_prose


def codes(text: str, anchors: tuple[str, ...] = ()) -> set[str]:
    return {finding.code for finding in audit_prose(text, anchors).findings}


def test_flags_high_precision_formulaic_filler() -> None:
    report = audit_prose("值得注意的是，该结果具有重要意义。")  # noqa: RUF001

    assert "formulaic_filler" in {finding.code for finding in report.findings}
    assert report.metrics.formulaic_filler_count == 2


def test_flags_repeated_paragraph_openings() -> None:
    text = "\n\n".join(
        [
            "现有研究讨论情绪表达。",
            "现有研究关注互动反馈。",
            "现有研究也分析平台结构。",
        ]
    )

    assert "repeated_paragraph_opening" in codes(text)


def test_flags_connector_stacking_but_does_not_block_revision() -> None:
    text = "此外，研究甲报告相关性。此外，研究乙限定了样本。此外，研究丙提出另一种解释。"  # noqa: RUF001

    report = audit_prose(text)

    assert "connector_density" in {finding.code for finding in report.findings}
    assert report.ok is True


def test_missing_protected_anchor_is_blocking() -> None:
    report = audit_prose("这一判断仍需限定。", ("E-01", "10.1000/test"))

    assert report.ok is False
    assert report.missing_anchors == ("E-01", "10.1000/test")
    assert any(
        finding.code == "protected_anchor_missing" and finding.severity == "blocking"
        for finding in report.findings
    )


def test_preserved_anchors_and_natural_prose_pass() -> None:
    text = (
        "平台反馈并不直接等同于态度改变。E-01 记录的是互动数量与情绪表达之间的相关关系，"  # noqa: RUF001
        "而非因果效应。\n\n"
        "这一边界使 10.1000/test 的发现适合解释可见性竞争，却不足以推断个体信念已经改变。"  # noqa: RUF001
    )

    report = audit_prose(text, ("E-01", "10.1000/test"))

    assert report.ok is True
    assert report.missing_anchors == ()
    assert "formulaic_filler" not in {finding.code for finding in report.findings}
