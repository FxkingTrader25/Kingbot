# estrategia/padroes_vela.py
import pandas as pd

def analyze(df: pd.DataFrame) -> str | None:
    """
    Analisa padrões de velas de Engolfo (Engulfing).
    
    :param df: DataFrame do pandas com 'open' e 'close'.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < 2:
        return None
        
    try:
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        # Engolfo de Alta (Bullish Engulfing)
        # A vela anterior é de baixa, a atual é de alta e "engole" a anterior.
        is_bullish_engulfing = (prev_candle['close'] < prev_candle['open'] and 
                                last_candle['close'] > last_candle['open'] and 
                                last_candle['close'] > prev_candle['open'] and 
                                last_candle['open'] < prev_candle['close'])
        if is_bullish_engulfing:
            return "UP"

        # Engolfo de Baixa (Bearish Engulfing)
        # A vela anterior é de alta, a atual é de baixa e "engole" a anterior.
        is_bearish_engulfing = (prev_candle['close'] > prev_candle['open'] and
                                last_candle['close'] < last_candle['open'] and
                                last_candle['close'] < prev_candle['open'] and
                                last_candle['open'] > prev_candle['close'])
        if is_bearish_engulfing:
            return "DOWN"
            
        return None
    except Exception:
        return None