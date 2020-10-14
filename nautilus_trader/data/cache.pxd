# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2020 Nautech Systems Pty Ltd. All rights reserved.
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

from nautilus_trader.common.logging cimport LoggerAdapter
from nautilus_trader.data.base cimport DataCacheReadOnly
from nautilus_trader.model.bar cimport Bar
from nautilus_trader.model.bar cimport BarType
from nautilus_trader.model.instrument cimport Instrument
from nautilus_trader.model.tick cimport QuoteTick
from nautilus_trader.model.tick cimport TradeTick
from nautilus_trader.serialization.constants cimport *
from nautilus_trader.trading.calculators cimport ExchangeRateCalculator


cdef class DataCache(DataCacheReadOnly):
    cdef LoggerAdapter _log

    cdef dict _instruments
    cdef dict _bid_quotes
    cdef dict _ask_quotes
    cdef dict _quote_ticks
    cdef dict _trade_ticks
    cdef dict _bars
    cdef ExchangeRateCalculator _xrate_calculator

    cpdef void set_tick_capacity(self, int capacity) except *
    cpdef void set_bar_capacity(self, int capacity) except *
    cpdef void reset(self) except *

    cpdef void add_instrument(self, Instrument instrument) except *
    cpdef void add_quote_tick(self, QuoteTick tick) except *
    cpdef void add_trade_tick(self, TradeTick tick) except *
    cpdef void add_bar(self, BarType bar_type, Bar bar) except *
