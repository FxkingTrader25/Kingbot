# estrategia/macd_histogram.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, macd_fast: int = 12, macd_slow: int = 26, macd_sign: int = 9) -> str | None:
    """
    Analisa o histograma do MACD para sinais de momentum.
    Sinal "UP": Histograma cruza de negativo para positivo.
    Sinal "DOWN": Histograma cruza de positivo para negativo.

    :param df: DataFrame com a coluna 'close'.
    :param macd_slow: Período da MME lenta.
    :param macd_fast: Período da MME rápida.
    :param macd_sign: Período da linha de sinal.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < macd_slow + 1:
        return None

    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if df.empty or len(df) < macd_slow + 1: return None

        # Calcula o MACD
        macd_indicator = ta.trend.MACD(
            close=df['close'],
            window_slow=macd_slow,
            window_fast=macd_fast,
            window_sign=macd_sign
        )
        df['macd_hist'] = macd_indicator.macd_diff()

        # Obtém os valores mais recentes do histograma
        last_hist = df['macd_hist'].iloc[-1]
        prev_hist = df['macd_hist'].iloc[-2] if len(df) >= 2 else None

        if prev_hist is None: return None

        # Sinal de compra (UP): Histograma cruza de negativo para positivo
        if prev_hist < 0 and last_hist >= 0:
            return "buy"
        # Sinal de venda (DOWN): Histograma cruza de positivo para negativo
        elif prev_hist > 0 and last_hist <= 0:
            return "sell"
        
        return None

    except Exception:
        return None
