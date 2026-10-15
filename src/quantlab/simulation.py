"""Seeded, synthetic biotech catalyst paths and a Gymnasium research environment.

These illustrative assumptions exercise event-aware research mechanics. They are
not calibrated to biotechnology securities and support no investment conclusion.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError("Install the optional RL dependency with `pip install -e '.[rl]'`.") from exc


@dataclass(frozen=True)
class CatalystAssumptions:
    """Configurable catalyst-gym parameters; only advancement priors are literature-informed."""

    catalyst_interval_sessions: int = 63
    broad_market_daily_mean: float = 0.00025
    broad_market_daily_volatility: float = 0.010
    issuer_market_beta: float = 0.35
    issuer_daily_mean: float = 0.00015
    issuer_idiosyncratic_daily_volatility: float = 0.025
    event_residual_volatility: float = 0.025
    phase_sampling_probabilities: tuple[float, float] = (0.5, 0.5)
    # Broad 2011–2020 BIO/Informa phase-transition rates. The outcome means
    # program advances (Phase II→III / Phase III→NDA-BLA), not endpoint success.
    phase_success_probabilities: tuple[float, float] = (0.289, 0.578)
    phase_success_market_positive_probabilities: tuple[float, float] = (0.72, 0.65)
    phase_failure_market_positive_probabilities: tuple[float, float] = (0.22, 0.28)
    phase_positive_market_gaps: tuple[float, float] = (0.13, 0.24)
    phase_negative_market_gaps: tuple[float, float] = (-0.16, -0.32)
    transaction_cost_bps_per_unit_turnover: float = 10.0

    def __post_init__(self) -> None:
        if self.catalyst_interval_sessions <= 1:
            raise ValueError("catalyst_interval_sessions must exceed 1")
        scalar_values = (
            self.broad_market_daily_mean, self.broad_market_daily_volatility,
            self.issuer_market_beta, self.issuer_daily_mean,
            self.issuer_idiosyncratic_daily_volatility, self.event_residual_volatility,
            self.transaction_cost_bps_per_unit_turnover,
            *self.phase_sampling_probabilities, *self.phase_success_probabilities,
            *self.phase_success_market_positive_probabilities,
            *self.phase_failure_market_positive_probabilities,
            *self.phase_positive_market_gaps, *self.phase_negative_market_gaps,
        )
        if not np.isfinite(scalar_values).all():
            raise ValueError("all simulator assumptions must be finite")
        nonnegative = (
            self.broad_market_daily_volatility,
            self.issuer_idiosyncratic_daily_volatility,
            self.event_residual_volatility,
            self.transaction_cost_bps_per_unit_turnover,
        )
        if any(value < 0 for value in nonnegative):
            raise ValueError("volatility and transaction-cost assumptions must be non-negative")
        for name in (
            "phase_sampling_probabilities", "phase_success_probabilities",
            "phase_success_market_positive_probabilities",
            "phase_failure_market_positive_probabilities",
            "phase_positive_market_gaps", "phase_negative_market_gaps",
        ):
            values = getattr(self, name)
            if len(values) != 2:
                raise ValueError(f"{name} must contain one value for Phase II and Phase III")
        for name in (
            "phase_sampling_probabilities", "phase_success_probabilities",
            "phase_success_market_positive_probabilities",
            "phase_failure_market_positive_probabilities",
        ):
            values = getattr(self, name)
            if any(not 0.0 <= value <= 1.0 for value in values):
                raise ValueError(f"{name} values must be in [0, 1]")
        if not np.isclose(sum(self.phase_sampling_probabilities), 1.0):
            raise ValueError("phase_sampling_probabilities must sum to 1")
        if any(gap <= -1.0 for gap in (*self.phase_positive_market_gaps, *self.phase_negative_market_gaps)):
            raise ValueError("event gaps must be greater than -100%")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "CatalystAssumptions":
        tuple_fields = {
            "phase_sampling_probabilities", "phase_success_probabilities",
            "phase_success_market_positive_probabilities",
            "phase_failure_market_positive_probabilities",
            "phase_positive_market_gaps", "phase_negative_market_gaps",
        }
        allowed = set(cls.__dataclass_fields__)
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown simulator assumption(s): {', '.join(sorted(unknown))}")
        converted = {
            key: tuple(value) if key in tuple_fields else value
            for key, value in values.items()
        }
        return cls(**converted)


def generate_catalyst_path(
    rng: np.random.Generator,
    periods: int,
    catalyst_interval: int | None = None,
    catalyst_class: int | None = None,
    assumptions: CatalystAssumptions | None = None,
    return_outcomes: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate returns, catalyst phases, and optionally clinical outcomes.

    A clinical success is sampled separately from the stock's positive/negative
    reaction. A success can sell off and a failure can rally. Phase and outcome
    probabilities, conditional reaction probabilities, and gap sizes are
    phase-advancement rates are broad published priors; conditional stock
    reactions, gaps, and ordinary price paths remain illustrative assumptions.
    The default three-item return preserves the original public function shape;
    internal gym generation requests the fourth outcome-label array explicitly.
    """
    config = assumptions or CatalystAssumptions()
    interval = config.catalyst_interval_sessions if catalyst_interval is None else catalyst_interval
    if periods <= 0 or interval <= 1:
        raise ValueError("periods must be positive and catalyst interval greater than 1")
    if catalyst_class not in (None, 0, 1):
        raise ValueError("catalyst_class must be None, 0 (Phase II), or 1 (Phase III)")
    broad = rng.normal(config.broad_market_daily_mean, config.broad_market_daily_volatility, size=periods)
    issuer = np.empty(periods, dtype=np.float64)
    labels = np.full(periods, -1, dtype=np.int8)
    outcomes = np.full(periods, -1, dtype=np.int8)
    phase = int(rng.choice(2, p=config.phase_sampling_probabilities)) if catalyst_class is None else catalyst_class
    for t in range(periods):
        if t and t % interval == 0:
            if catalyst_class is None:
                phase = int(rng.choice(2, p=config.phase_sampling_probabilities))
            labels[t] = phase
            success_probability = config.phase_success_probabilities[phase]
            success = rng.random() < success_probability
            outcomes[t] = int(success)
            positive_probability = (
                config.phase_success_market_positive_probabilities[phase]
                if success else config.phase_failure_market_positive_probabilities[phase]
            )
            positive_reaction = rng.random() < positive_probability
            gap = (
                config.phase_positive_market_gaps[phase]
                if positive_reaction else config.phase_negative_market_gaps[phase]
            )
            issuer[t] = config.issuer_market_beta * broad[t] + gap + rng.normal(0.0, config.event_residual_volatility)
        else:
            issuer[t] = config.issuer_market_beta * broad[t] + rng.normal(
                config.issuer_daily_mean, config.issuer_idiosyncratic_daily_volatility
            )
    if return_outcomes:
        return issuer, broad, labels, outcomes
    return issuer, broad, labels


class BiotechCatalystGym(gym.Env):
    """Single-issuer, long-or-cash catalyst environment with lagged features.

    At session t the action is selected from trailing issuer returns, the known
    calendar distance, and declared phase class. It earns session t's return;
    the catalyst outcome is not observed until that session has elapsed.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        episode_length: int = 252,
        lookback: int = 20,
        catalyst_interval: int = 63,
        transaction_cost_bps: float | None = None,
        assumptions: CatalystAssumptions | None = None,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        if episode_length <= 0 or lookback < 5:
            raise ValueError("episode_length must be positive and lookback at least 5")
        self.assumptions = assumptions or CatalystAssumptions(catalyst_interval_sessions=catalyst_interval)
        if catalyst_interval != 63 and catalyst_interval != self.assumptions.catalyst_interval_sessions:
            raise ValueError("set catalyst cadence in assumptions or pass a matching catalyst_interval")
        effective_cost = (
            self.assumptions.transaction_cost_bps_per_unit_turnover
            if transaction_cost_bps is None else transaction_cost_bps
        )
        if catalyst_interval <= 1 or effective_cost < 0:
            raise ValueError("catalyst interval must exceed 1 and costs must be non-negative")
        self.episode_length = int(episode_length)
        self.lookback = int(lookback)
        self.catalyst_interval = int(self.assumptions.catalyst_interval_sessions)
        self.transaction_cost_bps = float(effective_cost)
        self.render_mode = render_mode
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(
            low=np.array([-5.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([5.0, 5.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self._returns = np.zeros(self.lookback + self.episode_length, dtype=np.float64)
        self._benchmark = np.zeros_like(self._returns)
        self._events = np.full(len(self._returns), -1, dtype=np.int8)
        self._trial_outcomes = np.full(len(self._returns), -1, dtype=np.int8)
        self._cursor = self.lookback
        self._position = 0
        self._net_returns: list[float] = []
        self._benchmark_returns: list[float] = []
        self._event_returns: list[float] = []
        self._event_exposure: list[float] = []
        self._turnover: list[float] = []
        self._costs: list[float] = []
        self._exposures: list[float] = []

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        options = options or {}
        if "returns" in options:
            source = np.asarray(options["returns"], dtype=np.float64)
            if source.ndim != 1 or len(source) != self.episode_length:
                raise ValueError(f"returns must be a 1-D sequence of {self.episode_length} values")
            if not np.isfinite(source).all() or np.any(source <= -1.0):
                raise ValueError("returns must be finite and greater than -100%")
            warmup = np.asarray(options.get("warmup_returns", np.zeros(self.lookback)), dtype=np.float64)
            if warmup.shape != (self.lookback,) or not np.isfinite(warmup).all():
                raise ValueError(f"warmup_returns must be a finite sequence of {self.lookback} values")
            self._returns = np.concatenate((warmup, source))
            self._benchmark = self._validated_series(options, "benchmark_returns", source)
            self._events = self._validated_events(options, len(source))
            self._trial_outcomes = self._validated_trial_outcomes(options, len(source))
            if np.any((self._trial_outcomes >= 0) & (self._events < 0)):
                raise ValueError("known trial outcomes must align with a Phase II/III event phase")
        else:
            issuer, broad, labels, outcomes = generate_catalyst_path(
                self.np_random, self.episode_length,
                catalyst_class=options.get("catalyst_class"), assumptions=self.assumptions,
                return_outcomes=True,
            )
            warmup = self.np_random.normal(0.0, 0.02, size=self.lookback)
            self._returns = np.concatenate((warmup, issuer))
            self._benchmark = np.concatenate((np.zeros(self.lookback), broad))
            self._events = np.concatenate((np.full(self.lookback, -1, dtype=np.int8), labels))
            self._trial_outcomes = np.concatenate((np.full(self.lookback, -1, dtype=np.int8), outcomes))
        self._cursor = self.lookback
        self._position = 0
        self._net_returns = []
        self._benchmark_returns = []
        self._event_returns = []
        self._event_exposure = []
        self._turnover = []
        self._costs = []
        self._exposures = []
        return self._observation(), {
            "seed": seed,
            "synthetic": "returns" not in options,
            "assumptions": "illustrative_uncalibrated",
        }

    def _validated_series(self, options: dict, key: str, fallback: np.ndarray) -> np.ndarray:
        values = np.asarray(options.get(key, fallback), dtype=np.float64)
        if values.shape != fallback.shape or not np.isfinite(values).all() or np.any(values <= -1.0):
            raise ValueError(f"{key} must be finite, greater than -100%, and length {len(fallback)}")
        return np.concatenate((np.zeros(self.lookback), values))

    def _validated_events(self, options: dict, periods: int) -> np.ndarray:
        values = np.asarray(options.get("event_phases", options.get("event_labels", np.full(periods, -1))), dtype=np.int8)
        if values.shape != (periods,) or not np.isin(values, (-1, 0, 1)).all():
            raise ValueError("event phases must contain -1 (none), 0 (Phase II), or 1 (Phase III)")
        return np.concatenate((np.full(self.lookback, -1, dtype=np.int8), values))

    def _validated_trial_outcomes(self, options: dict, periods: int) -> np.ndarray:
        values = np.asarray(options.get("trial_outcomes", np.full(periods, -1)), dtype=np.int8)
        if values.shape != (periods,) or not np.isin(values, (-1, 0, 1)).all():
            raise ValueError("trial_outcomes must contain -1 (unknown/none), 0 (failure), or 1 (success)")
        return np.concatenate((np.full(self.lookback, -1, dtype=np.int8), values))

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        if not self.action_space.contains(action):
            raise ValueError("action must be 0 (cash) or 1 (long)")
        if self._cursor >= len(self._returns):
            raise RuntimeError("episode has ended; call reset() before step()")
        new_position = int(action)
        market_return = float(self._returns[self._cursor])
        benchmark_return = float(self._benchmark[self._cursor])
        event_phase = int(self._events[self._cursor])
        trial_outcome = int(self._trial_outcomes[self._cursor])
        turnover = float(abs(new_position - self._position))
        cost = turnover * self.transaction_cost_bps / 10_000.0
        net_return = new_position * market_return - cost
        reward = float(np.log1p(net_return))
        self._position = new_position
        self._cursor += 1
        self._net_returns.append(net_return)
        self._benchmark_returns.append(benchmark_return)
        self._event_returns.append(market_return if event_phase >= 0 else np.nan)
        self._event_exposure.append(float(new_position) if event_phase >= 0 else np.nan)
        self._turnover.append(turnover)
        self._costs.append(cost)
        self._exposures.append(float(new_position))
        terminated = self._cursor >= len(self._returns)
        info = {
            "market_return": market_return,
            "benchmark_return": benchmark_return,
            "net_return": net_return,
            "exposure": new_position,
            "turnover": turnover,
            "transaction_cost": cost,
            "event_label_observed_after_transition": event_phase,
            "event_phase_observed_after_transition": event_phase,
            "program_advancement_observed_after_transition": bool(trial_outcome) if trial_outcome >= 0 else None,
            # Compatibility key retained for existing forks; the outcome now
            # means progression to the next phase, not endpoint success.
            "trial_success_observed_after_transition": bool(trial_outcome) if trial_outcome >= 0 else None,
        }
        if terminated:
            info["episode"] = {
                "returns": np.asarray(self._net_returns),
                "benchmark_returns": np.asarray(self._benchmark_returns),
                "event_returns": np.asarray(self._event_returns),
                "event_exposure": np.asarray(self._event_exposure),
                "exposures": np.asarray(self._exposures),
                "turnover": float(np.sum(self._turnover)),
                "transaction_cost": float(np.sum(self._costs)),
            }
        return self._observation(), reward, terminated, False, info

    def _observation(self) -> np.ndarray:
        history = self._returns[max(0, self._cursor - self.lookback):self._cursor]
        momentum = float(np.prod(1.0 + history[-5:]) - 1.0)
        volatility = float(np.std(history, ddof=1)) if len(history) > 1 else 0.0
        next_event = np.flatnonzero(self._events[self._cursor:] >= 0)
        if len(next_event):
            distance = int(next_event[0])
            event_index = self._cursor + distance
            event_class = float(self._events[event_index])
        else:
            distance = self.catalyst_interval
            event_class = 0.0
        return np.asarray([
            np.clip(momentum * 20.0, -5.0, 5.0),
            np.clip(volatility / 0.02, 0.0, 5.0),
            min(distance / self.catalyst_interval, 1.0),
            event_class,
        ], dtype=np.float32)


# Backward-compatible import for forks that used the first generic gym name.
TradingGym = BiotechCatalystGym


def discretize_observation(observation: Sequence[float], catalyst_interval: int = 63) -> int:
    """Map momentum, volatility, catalyst proximity, and phase to 36 states."""
    if catalyst_interval <= 1:
        raise ValueError("catalyst_interval must exceed 1")
    momentum, volatility, distance, phase = observation
    momentum_bin = 0 if momentum < -0.1 else 1 if momentum <= 0.1 else 2
    volatility_bin = 0 if volatility < 1.2 else 1
    event_bin = 0 if distance > 5 / catalyst_interval else 1 if distance > 0 else 2
    phase_bin = int(round(float(phase)))
    return (((momentum_bin * 2 + volatility_bin) * 3 + event_bin) * 2) + phase_bin
