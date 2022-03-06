# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2022 Nautech Systems Pty Ltd. All rights reserved.
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

import pkgutil

import orjson

from nautilus_trader.adapters.binance.parsing.ws_data import parse_ticker_24hr_spot_ws
from nautilus_trader.backtest.data.providers import TestInstrumentProvider


ETHUSDT = TestInstrumentProvider.ethusdt_binance()


class TestBinanceWebSocketParsing:
    def test_parse_spot_ticker(self):
        # Arrange
        data = pkgutil.get_data(
            package="tests.integration_tests.adapters.binance.resources.ws_messages",
            resource="ws_spot_ticker_24hr.json",
        )
        msg = orjson.loads(data)

        # Act
        result = parse_ticker_24hr_spot_ws(
            instrument_id=ETHUSDT.id,
            msg=msg,
            ts_init=9999999999999991,
        )

        # Assert
        assert result.instrument_id == ETHUSDT.id
