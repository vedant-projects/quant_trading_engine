"""Sequential completed-bar processing and next-bar execution."""

from collections import deque

from app.core.execution_manager import ExecutionManager
from app.core.risk_manager import RiskManager
from app.core.signal_generator import generate_signals
from app.data.timeframes import timeframe_duration
from app.strategies.base import BaseStrategy, MarketBar, Signal
from app.utils.exceptions import RiskRejected


class StrategyEngine:
    """Run one strategy with causal event ordering."""

    def __init__(
        self,
        *,
        strategy: BaseStrategy,
        execution_manager: ExecutionManager,
        risk_manager: RiskManager,
    ) -> None:
        """Initialize an empty pending-signal queue."""
        self.strategy = strategy
        self.execution_manager = execution_manager
        self.risk_manager = risk_manager

        self.signals: list[Signal] = []
        self.rejections: list[str] = []
        self._pending: deque[Signal] = deque()

    async def process_bar(self, bar: MarketBar) -> None:
        """Execute old proposals at the open, then process the completed close."""
        portfolio = self.risk_manager.portfolio
        opening_time = bar.timestamp - timeframe_duration(bar.timeframe)

        portfolio.mark(bar.open)
        self.risk_manager.observe(opening_time)

        while self._pending:
            signal = self._pending.popleft()

            try:
                await self.execution_manager.execute(
                    signal,
                    reference_price=bar.open,
                    timestamp=opening_time,
                )
            except RiskRejected as exc:
                self.rejections.append(f"{signal.signal_id}: {exc}")

        portfolio.mark(bar.close)
        self.risk_manager.observe(bar.timestamp)

        signals = await generate_signals(self.strategy, bar)
        self.signals.extend(signals)
        self._pending.extend(signals)
