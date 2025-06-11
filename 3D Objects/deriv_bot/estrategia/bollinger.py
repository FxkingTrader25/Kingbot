# estrategia/bollinger.py
import pandas as pd
import ta

def analyze(df: pd.DataFrame, bollinger_period: int = 20, bollinger_dev: float = 2.0) -> str | None:
    """
    Analisa as Bandas de Bollinger para sinais de reversão à média.
    Sinal UP: Preço toca ou cruza a banda inferior.
    Sinal DOWN: Preço toca ou cruza a banda superior.
    
    :param df: DataFrame do pandas com a coluna 'close'.
    :param bollinger_period: Período da média móvel.
    :param bollinger_dev: Número de desvios padrão para as bandas.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < bollinger_period:
        return None
        
    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if df.empty or len(df) < bollinger_period: return None

        bollinger = ta.volatility.BollingerBands(close=df['close'], window=bollinger_period, window_dev=bollinger_dev)
        last_close = df['close'].iloc[-1]
        last_upper_band = bollinger.bollinger_hband().iloc[-1]
        last_lower_band = bollinger.bollinger_lband().iloc[-1]

        if last_close <= last_lower_band:
            return "UP"
        elif last_close >= last_upper_band:
            return "DOWN"
            
        return None
    except Exception:
        return None