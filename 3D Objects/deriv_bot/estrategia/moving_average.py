# estrategia/moving_average.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, ma_window: int = 20) -> str | None:
    """
    Analisa o cruzamento do preço com uma Média Móvel Simples (SMA).
    
    :param df: DataFrame do pandas com a coluna 'close'.
    :param ma_window: Período da média móvel.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < ma_window + 1:
        return None
        
    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if df.empty or len(df) < ma_window + 1: return None

        df['sma'] = ta.trend.sma_indicator(close=df['close'], window=ma_window)

        last_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        last_sma = df['sma'].iloc[-1]
        prev_sma = df['sma'].iloc[-2]

        # Cruzamento para cima
        if last_close > last_sma and prev_close <= prev_sma:
            return "UP"
        # Cruzamento para baixo
        elif last_close < last_sma and prev_close >= prev_sma:
            return "DOWN"
            
        return None
    except Exception:
        return None