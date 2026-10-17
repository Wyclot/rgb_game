# Adaptive Guardian

The shipped game uses explicit FSMs with an interpretable adaptive policy, mirrored in `adaptive.py` for experiments. It tracks attack/dodge count, combat duration, damage taken, and distance samples. Repeated dodges favor delayed nova; distance favors a projectile fan; other states cycle sweep/nova/fan. Phase II accelerates recovery and adds projectiles. Attacks retain visible telegraphs.

This is adaptive rule-based AI, **not a trained neural network**. No PyTorch weights or Gymnasium training results are claimed. A training environment is deferred because it does not improve the playable vertical slice without a meaningful reward model and evaluation budget.

Run: `.venv/bin/python -m pytest ml -q`.
