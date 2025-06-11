# estrategia/volume.py
import pandas as pd

def analyze(df: pd.DataFrame, volume_factor: float = 1.5, volume_history_periods: int = 20) -> str | None:
    """
    Analisa picos de volume que podem indicar o início ou clímax de um movimento.
    
    :param df: DataFrame com 'volume', 'close', 'open'.
    :param volume_factor: Fator de multiplicação para a média de volume.
    :param volume_history_periods: Período para calcular a média de volume.
    :return: "UP", "DOWN", ou None.
    """
    if 'volume' not in df.columns or len(df) < volume_history_periods:
        return None
        
    try:
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df = df.dropna(subset=['volume'])
        if df.empty or len(df) < volume_history_periods: return None

        # Calcula a média móvel do volume
        df['volume_avg'] = df['volume'].rolling(window=volume_history_periods, min_periods=10).mean()
        
        last_candle = df.iloc[-1]
        
        # Verifica se o volume da última vela é significativamente maior que a média
        is_volume_spike = last_candle['volume'] > (last_candle['volume_avg'] * volume_factor)

        if is_volume_spike:
            # Se o pico de volume ocorreu numa vela de alta, sinaliza UP
            if last_candle['close'] > last_candle['open']:
                return "UP"
            # Se o pico de volume ocorreu numa vela de baixa, sinaliza DOWN
            elif last_candle['close'] < last_candle['open']:
                return "DOWN"
                
        return None
    except Exception:
        return None