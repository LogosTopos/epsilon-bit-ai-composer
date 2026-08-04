"""Volume envelope sequence for chiptune instruments.

Tick-based envelope that overrides the renderer's default AR envelope.
Tick rate: 60 Hz (FamiTracker convention).
"""

from __future__ import annotations
import numpy as np

ENV_TICK_HZ = 60.0


def expand_volume_envelope(
    env: list[float],
    n_samples: int,
    sr: int = 44100,
    loop_at: int | None = None,
) -> np.ndarray:
    """Expand a tick-based volume envelope into a sample-rate array.

    Args:
        env: Per-tick volume multipliers in [0.0, 1.0]. Each value held for one tick.
        n_samples: Total samples to fill (note duration in samples).
        sr: Sample rate.
        loop_at: If set, after reaching the end of `env`, loop back to this tick index
                 and continue cycling for the remaining samples (sustain behavior).
                 If None, hold the last value of `env` for the remainder.

    Returns:
        np.ndarray of shape (n_samples,) float32, multiplier in [0.0, 1.0].
    """
    samples_per_tick = int(round(sr / ENV_TICK_HZ))
    out = np.empty(n_samples, dtype=np.float32)
    n_env = len(env)
    if n_env == 0:
        out.fill(1.0)
        return out

    pos = 0
    tick = 0
    while pos < n_samples:
        if tick < n_env:
            val = float(env[tick])
        elif loop_at is not None and 0 <= loop_at < n_env:
            cycle_len = n_env - loop_at
            val = float(env[loop_at + ((tick - n_env) % cycle_len)])
        else:
            val = float(env[-1])
        end = min(pos + samples_per_tick, n_samples)
        out[pos:end] = val
        pos = end
        tick += 1
    return out


if __name__ == "__main__":
    sr = 44100
    # Test 1: basic decay envelope, non-looping
    env1 = expand_volume_envelope([1.0, 0.8, 0.6, 0.4, 0.2, 0.0], sr)
    assert len(env1) == sr, f"len={len(env1)}"
    spt = int(round(sr / ENV_TICK_HZ))  # 735
    assert np.allclose(env1[:spt], 1.0, atol=0.01), f"tick0={env1[:10]}"
    after_tick5 = 5 * spt
    assert np.allclose(env1[after_tick5:], 0.0, atol=0.01), f"tick5+={env1[after_tick5:after_tick5+10]}"

    # Test 2: looping envelope
    env2 = expand_volume_envelope([1.0, 0.5], sr, loop_at=0)
    assert len(env2) == sr
    # Should oscillate between 1.0 and 0.5 every tick
    tick0_vals = env2[:spt]
    tick1_vals = env2[spt:2*spt]
    tick2_vals = env2[2*spt:3*spt]
    assert np.allclose(tick0_vals, 1.0, atol=0.01)
    assert np.allclose(tick1_vals, 0.5, atol=0.01)
    assert np.allclose(tick2_vals, 1.0, atol=0.01)

    # Test 3: empty env
    env3 = expand_volume_envelope([], 1000)
    assert np.allclose(env3, 1.0)

    # Test 4: loop_at mid-envelope
    env4 = expand_volume_envelope([1.0, 0.8, 0.6, 0.4], sr, loop_at=2)
    assert np.allclose(env4[:spt], 1.0, atol=0.01)
    assert np.allclose(env4[2*spt:3*spt], 0.6, atol=0.01)
    assert np.allclose(env4[4*spt:5*spt], 0.6, atol=0.01)

    print("OK: all envelope tests passed")
