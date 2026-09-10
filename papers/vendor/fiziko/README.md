# Fiziko

Unmodified `fiziko.mp` from https://github.com/jemmybutton/fiziko, downloaded
2026-09-09. Copyright Sergey Slyusarev. See LICENSE.md for GPL-3.0 terms.
SHA-256: `55c7b8053e62516e5091713b31d4cc21707901f9ffa5e456afbf6fef2b39e2b5`.

This optional renderer uses the host's MetaPost executable. LocalXiv does not
bundle a TeX distribution. Without `mpost`, the planner offers its other visuals.
`FIZIKO_MP` can override this library with an explicitly installed copy.

Only the fixed template in `papers/illustrations.py` runs. The model selects
the template and supplies prose, never MetaPost source or file paths.
