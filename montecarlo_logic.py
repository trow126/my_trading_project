# montecarlo_logic.py
import math

class DecompositionMonteCarloLogic:
    """
    分解モンテカルロ法のロジックを管理するクラス。
    Backtraderから独立してテスト可能。
    """
    def __init__(self):
        self.sequence = [] # 数列リスト
        self.reset_cycle() # 初期化時に最初のサイクルを開始

    def reset_cycle(self):
        """数列を初期状態 [0, 1] にリセットする"""
        self.sequence = [0, 1]
        # print("DEBUG: Cycle Reset ->", self.sequence) # デバッグ用

    def get_unit_size(self) -> int:
        """次の取引の単位ロット数を計算する"""
        if len(self.sequence) >= 2:
            return self.sequence[0] + self.sequence[-1]
        elif len(self.sequence) == 1:
            return self.sequence[0]
        else: # 数列が空 (サイクル完了直後など)
            return 0

    def _apply_decomposition(self):
        """数列が1つになった場合に分解ルールを適用する (内部メソッド)"""
        if len(self.sequence) == 1:
            val = self.sequence[0]
            if val > 1:
                # 分解ルール: 例として整数除算とその残りを使う
                # 例: 2 -> [1, 1], 3 -> [1, 2], 4 -> [2, 2], 5 -> [2, 3]
                half1 = val // 2
                half2 = val - half1
                self.sequence = [half1, half2]
                # print(f"DEBUG: Decomposition Applied: {val} -> {self.sequence}") # デバッグ用
            # elif val == 1:
                # 1の場合は分解しない (ルールに基づき)
                # print(f"DEBUG: Decomposition Skipped for value 1")
                pass


    def update_sequence(self, is_win: bool, traded_unit_size: int):
        """取引結果に基づいて数列を更新する"""
        if self.is_cycle_complete():
            # print("警告: サイクル完了後にupdate_sequenceが呼ばれました。") # 必要ならログ出力
            return

        if is_win:
            # 勝ちの場合
            if len(self.sequence) >= 2:
                self.sequence.pop(0)  # 左端を削除
                self.sequence.pop(-1) # 右端を削除
            elif len(self.sequence) == 1:
                # 最後の1つで勝った場合
                if traded_unit_size == self.sequence[0]:
                     self.sequence.pop(0) # 残りの要素を削除
                else:
                    # 通常ありえないが、念のためログ出し＆削除
                    print(f"警告: 数列[1]の時に想定外ロット({traded_unit_size} vs {self.sequence[0]})で勝利。要素を削除します。")
                    self.sequence.pop(0)
            # print(f"DEBUG: Win update -> {self.sequence}") # デバッグ用

        else:
            # 負けの場合
            # 取引した単位ロット数を右端に追加
            self.sequence.append(traded_unit_size)
            # print(f"DEBUG: Lose update -> {self.sequence}") # デバッグ用

        # 勝ち負け処理後に分解ルールを適用
        self._apply_decomposition()

        # サイクル完了チェック (完了したらリセットするかは呼び出し元で判断)
        if self.is_cycle_complete():
            # print("DEBUG: Cycle now complete.") # デバッグ用
            pass


    def is_cycle_complete(self) -> bool:
        """現在のサイクルが完了したか（数列が空か）を返す"""
        return len(self.sequence) == 0