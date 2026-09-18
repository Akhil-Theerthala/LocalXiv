"""Checks on a rendered figure: native renderer defects and text density."""
# Text runs per million square units below which a page is rejected as sparse. The reference
# figures measure about 42 to 64; the abandoned model-drawn output measured 13.
MIN_TEXT_DENSITY = 30


def text_density(checks):
    """Text runs per million square units of the rendered canvas."""
    canvas = checks.get('canvas') or {}
    area = float(canvas.get('width') or 0) * float(canvas.get('height') or 0)
    if area <= 0:
        return 0.0
    return len(checks.get('text_runs') or []) / (area / 1e6)


def native_issues(checks):
    """One message per native defect, in the renderer's order."""
    return [str(issue.get('message') or issue.get('code')) for issue in checks.get('issue_details') or []]
