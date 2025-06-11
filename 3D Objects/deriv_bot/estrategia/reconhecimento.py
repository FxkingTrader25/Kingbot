# estrategia/reconhecimento.py
import pandas as pd

def analyze(df: pd.DataFrame) -> str | None:
    """
    Analisa padrões de velas de 3 dias: Estrela da Manhã e Estrela da Tarde.
    
    :param df: DataFrame com 'open' e 'close'.
    :return: "UP", "DOWN", ou None.
    """
    if len(df) < 3:
        return None
        
    try:
        c0, c1, c2 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        body = lambda c: abs(c['close'] - c['open'])
        mid_point_c0 = (c0['open'] + c0['close']) / 2

        # Estrela da Manhã (Sinal de Fundo -> UP)
        # 1. Vela de baixa forte.
        # 2. Pequena vela (doji/pião) com gap de baixa.
        # 3. Vela de alta que fecha acima do ponto médio da primeira vela.
        is_morning_star = (c0['close'] < c0['open'] and  # 1. Baixa
                           body(c1) < body(c0) and      # 2. Corpo pequeno
                           c1['close'] < c0['close'] and    # Gap ou corpo baixo
                           c2['close'] > c2['open'] and     # 3. Alta
                           c2['close'] > mid_point_c0)    # Fecha acima do meio
        if is_morning_star:
            return "UP"

        # Estrela da Tarde (Sinal de Topo -> DOWN)
        # 1. Vela de alta forte.
        # 2. Pequena vela (doji/pião) com gap de alta.
        # 3. Vela de baixa que fecha abaixo do ponto médio da primeira vela.
        is_evening_star = (c0['close'] > c0['open'] and  # 1. Alta
                           body(c1) < body(c0) and      # 2. Corpo pequeno
                           c1['close'] > c0['close'] and    # Gap ou corpo alto
                           c2['close'] < c2['open'] and     # 3. Baixa
                           c2['close'] < mid_point_c0)    # Fecha abaixo do meio
        if is_evening_star:
            return "DOWN"
            
        return None
    except Exception:
        return None