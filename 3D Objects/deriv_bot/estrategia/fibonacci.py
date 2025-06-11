# estrategia/fibonacci.py
import pandas as pd

def analyze(df: pd.DataFrame, fib_period: int = 50) -> str | None:
    """
    Análise simplificada de retração de Fibonacci.
    Busca por reversões em níveis chave (61.8%) após um swing de alta ou baixa.
    
    :param df: DataFrame do pandas com 'high', 'low', 'close'.
    :param fib_period: Período para determinar o swing high/low.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < fib_period:
        return None
        
    try:
        recent_df = df.iloc[-fib_period:]
        swing_high = recent_df['high'].max()
        swing_low = recent_df['low'].min()
        price_range = swing_high - swing_low

        if price_range == 0: return None

        # Nível de retração de 61.8% para um movimento de alta (suporte)
        support_level = swing_high - 0.618 * price_range
        
        # Nível de retração de 61.8% para um movimento de baixa (resistência)
        resistance_level = swing_low + 0.618 * price_range

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Lógica de Reversão para Alta (UP)
        # O preço caiu abaixo do suporte e depois fechou acima dele, com uma vela de alta.
        if prev_candle['low'] <= support_level and last_candle['close'] > support_level:
            if last_candle['close'] > last_candle['open']: # Confirmação com candle de alta
                return "UP"

        # Lógica de Reversão para Baixa (DOWN)
        # O preço subiu acima da resistência e depois fechou abaixo dela, com uma vela de baixa.
        if prev_candle['high'] >= resistance_level and last_candle['close'] < resistance_level:
            if last_candle['close'] < last_candle['open']: # Confirmação com candle de baixa
                return "DOWN"
                
        return None
    except Exception:
        return None