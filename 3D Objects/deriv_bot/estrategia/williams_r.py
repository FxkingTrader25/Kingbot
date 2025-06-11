# estrategia/williams_r.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, williams_period: int = 14, williams_overbought: int = -20, williams_oversold: int = -80) -> str | None:
    """
    Analisa o Williams %R (Percent Range).
    Sinal "UP": Indicador cruza para cima do nível de sobrevenda.
    Sinal "DOWN": Indicador cruza para baixo do nível de sobrecompra.

    :param df: DataFrame com 'high', 'low', 'close'.
    :param williams_period: Período de cálculo.
    :param williams_overbought: Nível de sobrecompra (geralmente -20).
    :param williams_oversold: Nível de sobrevenda (geralmente -80).
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < williams_period:
        return None

    try:
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['high', 'low', 'close'])
        if df.empty or len(df) < williams_period: return None

        # Calcula o Williams %R
        df['williams_r'] = ta.momentum.WilliamsRIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            lbp=williams_period
        ).williams_r()

        # Obtém os valores mais recentes
        last_williams_r = df['williams_r'].iloc[-1]
        prev_williams_r = df['williams_r'].iloc[-2] if len(df) >= 2 else None

        if prev_williams_r is None: return None

        # Sinal de compra (UP): Cruza acima do nível de sobrevenda
        if prev_williams_r <= williams_oversold and last_williams_r > williams_oversold:
            return "buy"
        # Sinal de venda (DOWN): Cruza abaixo do nível de sobrecompra
        elif prev_williams_r >= williams_overbought and last_williams_r < williams_overbought:
            return "sell"
        
        return None

    except Exception:
        return None
