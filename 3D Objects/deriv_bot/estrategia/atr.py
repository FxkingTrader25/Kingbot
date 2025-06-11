# estrategia/atr.py
import pandas as pd
import ta

def calculate(df: pd.DataFrame, window: int = 14) -> float | None:
    """
    Calcula o Average True Range (ATR) para medir a volatilidade.
    Esta função não gera um sinal, mas fornece o valor do ATR para ser usado
    em outras lógicas, como a definição de um stop loss dinâmico.

    :param df: DataFrame com 'high', 'low', 'close'.
    :param window: O período para o cálculo do ATR.
    :return: O valor do último ATR ou None se houver erro.
    """
    if len(df) < window + 1:
        return None

    try:
        # Garante que os dados de entrada são numéricos
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['high', 'low', 'close'])
        if df.empty or len(df) < window + 1: return None

        # Calcula o indicador ATR
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=window
        )
        # Retorna o valor mais recente do ATR
        return atr_indicator.average_true_range().iloc[-1]

    except Exception:
        return None
