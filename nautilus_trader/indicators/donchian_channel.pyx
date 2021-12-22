# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2021 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

from collections import deque

from nautilus_trader.core.correctness cimport Condition
from nautilus_trader.indicators.base.indicator cimport Indicator
from nautilus_trader.model.data.bar cimport Bar
from nautilus_trader.model.data.tick cimport QuoteTick
from nautilus_trader.model.data.tick cimport TradeTick


cdef class DonchianChannel(Indicator):
    """
    Donchian Channels are three lines generated by moving average calculations
    that comprise an indicator formed by upper and lower bands around a
    mid-range or median band. The upper band marks the highest price of a
    instrument_id over N periods while the lower band marks the lowest price of a
    instrument_id over N periods. The area between the upper and lower bands
    represents the Donchian Channel.

    Parameters
    ----------
    period : int
        The rolling window period for the indicator (> 0).

    Raises
    ------
    ValueError
        If `period` is not positive (> 0).
    """

    def __init__(self, int period):
        Condition.positive_int(period, "period")
        super().__init__(params=[period])

        self.period = period
        self._upper_prices = deque(maxlen=period)
        self._lower_prices = deque(maxlen=period)

        self.upper = 0
        self.middle = 0
        self.lower = 0

    cpdef void handle_quote_tick(self, QuoteTick tick) except *:
        """
        Update the indicator with the given ticks high and low prices.

        Parameters
        ----------
        tick : TradeTick
            The tick for the update.

        """
        Condition.not_none(tick, "tick")

        self.update_raw(tick.ask.as_double(), tick.bid.as_double())

    cpdef void handle_trade_tick(self, TradeTick tick) except *:
        """
        Update the indicator with the given ticks price.

        Parameters
        ----------
        tick : TradeTick
            The tick for the update.

        """
        Condition.not_none(tick, "tick")

        cdef double price = tick.price.as_double()
        self.update_raw(price, price)

    cpdef void handle_bar(self, Bar bar) except *:
        """
        Update the indicator with the given bar.

        Parameters
        ----------
        bar : Bar
            The update bar.

        """
        Condition.not_none(bar, "bar")

        self.update_raw(bar.high.as_double(), bar.low.as_double())

    cpdef void update_raw(self, double high, double low) except *:
        """
        Update the indicator with the given prices.

        Parameters
        ----------
        high : double
            The price for the upper channel.
        low : double
            The price for the lower channel.

        """
        # Add data to queues
        self._upper_prices.append(high)
        self._lower_prices.append(low)

        # Initialization logic
        if not self.initialized:
            self._set_has_inputs(True)
            if len(self._upper_prices) >= self.period and len(self._lower_prices) >= self.period:
                self._set_initialized(True)

        # Set values
        self.upper = max(self._upper_prices)
        self.lower = min(self._lower_prices)
        self.middle = (self.upper + self.lower) / 2

    cpdef void _reset(self) except *:
        self._upper_prices.clear()
        self._lower_prices.clear()

        self.upper = 0
        self.middle = 0
        self.lower = 0
