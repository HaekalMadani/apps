"""The human-driven pair-1 block set the committed residual numbers came from.

This list is a RECORD, not a query. Discovering blocks from the manifests would
silently change the denominator as new blocks are recorded, and the figures in
`CLAUDE.md` and `configs/references/G0_REVIEW.md` would stop being reproducible
from the files they cite. Add to it deliberately, and re-state the numbers that
move when you do.

All seven are Silverstone National in the M235i, driven by the researcher (a
novice), `autopilot` absent. Four are the M6 dry run; the rest are dev and G0
review blocks. 162 clean corner passes in total.
"""

PAIR1_HUMAN_NATIONAL = (
    "DRY01_s1_pair1_off_20261010_110113",
    "DRY01_s2_pair1_adaptive_20261010_111207",
    "DRY01_s2_pair1_off_20261010_113908",
    "DRY01_s2_pair1_static_20261010_112835",
    "M5_s2_pair1_adaptive_20261009_204120",
    "g0_s2_pair1_adaptive_20260908_162754",
    "m5_tst_s2_pair1_adaptive_20260909_003201",
)
