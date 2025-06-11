# estrategia/adx.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, adx_period: int = 14, adx_threshold: int = 25) -> str | None:
    """
    Analisa o ADX (Average Directional Index) para sinais de início de tendência.
    Gera um sinal com base no cruzamento do +DI e -DI, mas apenas se o ADX
    estiver acima de um limiar, indicando que uma tendência forte está presente.

    :param df: DataFrame com colunas 'high', 'low', 'close'.
    :param adx_period: O período de tempo para o cálculo do ADX.
    :param adx_threshold: O limiar do ADX para validar a força da tendência.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < adx_period * 2:
        return None

    try:
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['high', 'low', 'close'])

        if df.empty or len(df) < adx_period * 2: return None

        adx_indicator = ta.trend.ADXIndicator(
            high=df['high'], low=df['low'], close=df['close'], window=adx_period
        )
        df['adx'] = adx_indicator.adx()
        df['plus_di'] = adx_indicator.adx_pos()
        df['minus_di'] = adx_indicator.adx_neg()

        # Obtém os valores mais recentes
        last_adx = df['adx'].iloc[-1]
        last_plus_di = df['plus_di'].iloc[-1]
        last_minus_di = df['minus_di'].iloc[-1]
        prev_plus_di = df['plus_di'].iloc[-2]
        prev_minus_di = df['minus_di'].iloc[-2]

        # Lógica do sinal
        is_strong_trend = last_adx > adx_threshold

        if is_strong_trend:
            if last_plus_di > last_minus_di and prev_plus_di <= prev_minus_di:
                return "UP"
            elif last_minus_di > last_plus_di and prev_minus_di <= prev_plus_di:
                return "DOWN"

        return None
    except Exception:
        return None