# estrategia/rsi.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, rsi_period: int = 14, rsi_overbought: int = 70, rsi_oversold: int = 30) -> str | None:
    """
    Analisa o Índice de Força Relativa (RSI) para sinais de reversão.
    
    :param df: DataFrame do pandas com 'close'.
    :param rsi_period: Período do RSI.
    :param rsi_overbought: Nível de sobrecompra.
    :param rsi_oversold: Nível de sobrevenda.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < rsi_period + 1:
        return None
        
    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if df.empty or len(df) < rsi_period + 1: return None

        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=rsi_period).rsi()
        last_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]

        # Sinal de compra quando o RSI sai da zona de sobrevenda
        if last_rsi > rsi_oversold and prev_rsi <= rsi_oversold:
            return "UP"
        # Sinal de venda quando o RSI sai da zona de sobrecompra
        elif last_rsi < rsi_overbought and prev_rsi >= rsi_overbought:
            return "DOWN"
            
        return None
    except Exception:
        return None