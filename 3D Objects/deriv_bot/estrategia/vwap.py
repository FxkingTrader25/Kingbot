# estrategia/vwap.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, vwap_window: int = 14) -> str | None:
    """
    Analisa o cruzamento do preço com o VWAP (Volume-Weighted Average Price).
    Um sinal de "UP" é gerado quando o preço de fecho cruza para cima do VWAP.
    Um sinal de "DOWN" é gerado quando o preço de fecho cruza para baixo do VWAP.

    :param df: DataFrame com 'high', 'low', 'close', 'volume'.
    :param vwap_window: A janela de cálculo para o VWAP.
    :return: "UP", "DOWN", ou None.
    """
    if 'volume' not in df.columns or len(df) < vwap_window + 1:
        return None

    try:
        # Garante que os dados de entrada são numéricos
        for col in ['high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['high', 'low', 'close', 'volume'])
        if df.empty or len(df) < vwap_window + 1: return None

        # Calcula o VWAP
        df['vwap'] = ta.volume.VolumeWeightedAveragePrice(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            volume=df['volume'],
            window=vwap_window
        ).volume_weighted_average_price()

        # Obtém os dados mais recentes para a decisão
        last_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        last_vwap = df['vwap'].iloc[-1]
        prev_vwap = df['vwap'].iloc[-2]

        # Sinal de compra (UP): Preço cruza para cima do VWAP
        if prev_close <= prev_vwap and last_close > last_vwap:
            return "buy"
        # Sinal de venda (DOWN): Preço cruza para baixo do VWAP
        elif prev_close >= prev_vwap and last_close < last_vwap:
            return "sell"
        
        return None

    except Exception:
        return None
