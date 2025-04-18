# strategies.py
import backtrader as bt
# 同じディレクトリにある montecarlo_logic.py からクラスをインポート
try:
    from .montecarlo_logic import DecompositionMonteCarloLogic
except ImportError: # スクリプトとして直接実行する場合などのため
    from montecarlo_logic import DecompositionMonteCarloLogic


class MonteCarloSmaCrossWithTPSL(bt.Strategy):
    """
    分解モンテカルロ法によるロット管理と、
    SMAクロスシグナル、固定pips TP/SLを組み合わせた戦略クラス。
    """
    params = (
        ('unit_lot', 0.01),       # 1単位あたりのロット数
        ('sma_short_period', 12), # 短期SMA期間
        ('sma_long_period', 26),  # 長期SMA期間
        ('tp_pips', 25.0),        # 利益確定のpips数 (損益対称性を考慮)
        ('sl_pips', 25.0),        # 損切りのpips数 (損益対称性を考慮)
        # ('debug_log', False),     # 詳細ログ出力フラグ (Trueにするとログ増加)
    )

    def log(self, txt, dt=None):
        ''' logging function for this strategy'''
        # if self.params.debug_log: # デバッグフラグに応じて出力制御
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        # pip valueの取得 (シンボル名から簡易的に判断)
        if 'JPY' in self.data._name:
             self.pip_value = 0.01
        else: # ドルストレートなどを想定
             self.pip_value = 0.0001

        self.log(f'Strategy Parameters: Unit Lot={self.params.unit_lot}, SMA={self.params.sma_short_period}/{self.params.sma_long_period}, '
                 f'TP={self.params.tp_pips}pips, SL={self.params.sl_pips}pips, PipValue={self.pip_value}')

        # モンテカルロロジック
        self.sizer_logic = DecompositionMonteCarloLogic()
        self.log(f'Initial Monte Carlo Sequence: {self.sizer_logic.sequence}')

        # インジケーター
        self.sma_short = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma_short_period)
        self.sma_long = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma_long_period)
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)

        # 注文関連の変数をリストで保持
        self.orders = []
        self.current_trade_units = 0

        self.log('MonteCarloSmaCrossWithTPSL Initialized')

    def notify_order(self, order):
         if order.status in [order.Submitted, order.Accepted]:
             return
         try: self.orders.remove(order)
         except ValueError: pass

         if order.status == order.Completed:
             exec_type = 'BUY' if order.isbuy() else 'SELL'
             if order.ordtype == order.Market: exec_type += " Market Entry"
             elif order.ordtype == order.Limit: exec_type += " Limit (TP?)"
             elif order.ordtype == order.Stop: exec_type += " Stop (SL?)"
             self.log(f'{exec_type} EXECUTED: Ref={order.ref}, Price: {order.executed.price:.3f}, Size: {order.executed.size:.2f}')
         elif order.status in [order.Canceled, order.Margin, order.Rejected]:
             self.log(f'Order {order.getstatusname()}: Ref={order.ref}')

    def notify_trade(self, trade):
        if trade.isclosed:
            is_win = trade.pnl > 0
            traded_unit_size = self.current_trade_units
            close_reason = "TP hit?" if is_win else "SL hit?"

            self.log(f'Trade Closed ({close_reason}): PNL={trade.pnl:.2f}, Win={is_win}, '
                     f'Traded Units={traded_unit_size}, Seq Before: {self.sizer_logic.sequence}')
            self.sizer_logic.update_sequence(is_win, traded_unit_size)
            self.log(f'                                         Seq After: {self.sizer_logic.sequence}')

            if self.sizer_logic.is_cycle_complete():
                self.log("Cycle Complete! Resetting sequence.")
                self.sizer_logic.reset_cycle()
            self.current_trade_units = 0

    def next(self):
        if self.orders or self.position:
            return # 保留中のオーダーがあるか、ポジションがあれば何もしない

        unit_size = self.sizer_logic.get_unit_size()
        if unit_size > 0:
            calculated_size = unit_size * self.params.unit_lot
            if self.crossover > 0: # ゴールデンクロス
                entry_price = self.data.close[0]
                sl_price = entry_price - self.params.sl_pips * self.pip_value
                tp_price = entry_price + self.params.tp_pips * self.pip_value
                self.current_trade_units = unit_size
                self.log(f'BUY BRACKET CREATE: Units={unit_size}, Size={calculated_size:.2f}, SL={sl_price:.3f}, TP={tp_price:.3f}, Sequence: {self.sizer_logic.sequence}')
                orders = self.buy_bracket(size=calculated_size, exectype=bt.Order.Market, stopprice=sl_price, limitprice=tp_price)
                self.orders.extend(orders)
            # elif self.crossover < 0: # デッドクロス (売りエントリーも入れる場合)
            #     entry_price = self.data.close[0]
            #     sl_price = entry_price + self.params.sl_pips * self.pip_value
            #     tp_price = entry_price - self.params.tp_pips * self.pip_value
            #     self.current_trade_units = unit_size
            #     self.log(f'SELL BRACKET CREATE: Units={unit_size}, Size={calculated_size:.2f}, SL={sl_price:.3f}, TP={tp_price:.3f}, Sequence: {self.sizer_logic.sequence}')
            #     orders = self.sell_bracket(size=calculated_size, exectype=bt.Order.Market, stopprice=sl_price, limitprice=tp_price)
            #     self.orders.extend(orders)

    def stop(self):
         self.log('MonteCarloSmaCrossWithTPSL Finished')
         self.log(f'Final Monte Carlo Sequence: {self.sizer_logic.sequence}')

# --- 必要であれば他のStrategyクラスもここに追加 ---
# class SmaCrossStrategy(bt.Strategy): ...