# adx.py
import pandas as pd
from ta.trend import ADXIndicator

def verificar(candles):
    if len(candles) < 20:
        return False
    df = pd.DataFrame(candles, columns=["open", "high", "low", "close"])
    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
    return adx.adx().iloc[-1] > 20  # ou outro limiar
  
  # volume.py
  from collections import Counter

def verificar(candle_ticks, fator=1.5):
    
    if len(candle_ticks) < 60:
        return False

    volumes = Counter((tick['epoch'] // 60) for tick in candle_ticks[-60:])
    media_volume = sum(volumes.values()) / len(volumes)

    ultimo_epoch = candle_ticks[-1]['epoch'] // 60
    volume_atual = volumes[ultimo_epoch]

    return volume_atual > fator * media_volume
     
     
     #rsi.py
     def verificar(candles, tipo="CALL"):
    if len(candles) < 15:
        return False

    df = pd.DataFrame(candles, columns=["close"])
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    ultimo_rsi = rsi.iloc[-1]

    if tipo == "CALL":
        return ultimo_rsi < 30
    elif tipo == "PUT":
        return ultimo_rsi > 70
    return False
# reconhecimento.py 
def verificar(candles):
    """
    Reconhecimento avançado de padrões de vela.
    candles: lista de dicionários com 'open', 'high', 'low', 'close'
    Retorna: dict com 'sinal' (CALL/PUT), 'padrao' ou None
    """
    if len(candles) < 3:
        return None

    c0, c1, c2 = candles[-3], candles[-2], candles[-1]

    def corpo(c): return abs(c['close'] - c['open'])
    def pavio_inf(c): return min(c['open'], c['close']) - c['low']
    def pavio_sup(c): return c['high'] - max(c['open'], c['close'])

    sinais = []

    # Engolfo de alta
    if (c1['close'] < c1['open'] and
        c2['close'] > c2['open'] and
        c2['open'] < c1['close'] and
        c2['close'] > c1['open']):
        sinais.append({'sinal': 'CALL', 'padrao': 'engolfo_alta'})

    # Engolfo de baixa
    if (c1['close'] > c1['open'] and
        c2['close'] < c2['open'] and
        c2['open'] > c1['close'] and
        c2['close'] < c1['open']):
        sinais.append({'sinal': 'PUT', 'padrao': 'engolfo_baixa'})

    # Doji
    if corpo(c2) < (c2['high'] - c2['low']) * 0.1:
        sinais.append({'sinal': None, 'padrao': 'doji'})

    # Martelo (CALL)
    if corpo(c2) > 0 and pavio_inf(c2) > corpo(c2) * 2 and pavio_sup(c2) < corpo(c2):
        sinais.append({'sinal': 'CALL', 'padrao': 'martelo'})

    # Martelo Invertido (PUT)
    if corpo(c2) > 0 and pavio_sup(c2) > corpo(c2) * 2 and pavio_inf(c2) < corpo(c2):
        sinais.append({'sinal': 'PUT', 'padrao': 'martelo_invertido'})

    # Estrela da Manhã (CALL)
    if (c0['close'] < c0['open'] and
        corpo(c1) < corpo(c0) and
        c2['close'] > c2['open'] and
        c2['close'] > ((c0['open'] + c0['close']) / 2)):
        sinais.append({'sinal': 'CALL', 'padrao': 'estrela_manha'})

    # Estrela da Tarde (PUT)
    if (c0['close'] > c0['open'] and
        corpo(c1) < corpo(c0) and
        c2['close'] < c2['open'] and
        c2['close'] < ((c0['open'] + c0['close']) / 2)):
        sinais.append({'sinal': 'PUT', 'padrao': 'estrela_tarde'})

    return sinais[-1] if sinais else None

# padroes_vela.py
def verificar(candles):
    """
    Detecta padrões de candle (martelo, engolfo, doji, estrela da manhã/tarde, etc.).
    candles: lista de dicionários com 'open', 'high', 'low', 'close'
    Retorna: dict com 'sinal' (CALL/PUT), 'padrao' (nome do padrão) ou None
    """
    if len(candles) < 3:
        return None

    c0, c1, c2 = candles[-3], candles[-2], candles[-1]

    def corpo(c): return abs(c['close'] - c['open'])
    def pavio_inf(c): return min(c['open'], c['close']) - c['low']
    def pavio_sup(c): return c['high'] - max(c['open'], c['close'])

    sinais = []

    # ----- Martelo (CALL)
    if corpo(c2) < (pavio_inf(c2) * 0.5) and pavio_inf(c2) > (pavio_sup(c2) * 2):
        sinais.append({'sinal': 'CALL', 'padrao': 'martelo'})

    # ----- Martelo Invertido (CALL)
    if corpo(c2) < (pavio_sup(c2) * 0.5) and pavio_sup(c2) > (pavio_inf(c2) * 2):
        sinais.append({'sinal': 'CALL', 'padrao': 'martelo_invertido'})

    # ----- Engolfo de Alta (CALL)
    if (c1['close'] < c1['open'] and
        c2['close'] > c2['open'] and
        c2['open'] < c1['close'] and
        c2['close'] > c1['open']):
        sinais.append({'sinal': 'CALL', 'padrao': 'engolfo_alta'})

    # ----- Engolfo de Baixa (PUT)
    if (c1['close'] > c1['open'] and
        c2['close'] < c2['open'] and
        c2['open'] > c1['close'] and
        c2['close'] < c1['open']):
        sinais.append({'sinal': 'PUT', 'padrao': 'engolfo_baixa'})

    # ----- Doji (indecisão)
    if corpo(c2) <= (c2['high'] - c2['low']) * 0.1:
        sinais.append({'sinal': None, 'padrao': 'doji'})

    # ----- Estrela da Manhã (CALL)
    if (c0['close'] < c0['open'] and
        corpo(c1) < corpo(c0) and
        c2['close'] > c2['open'] and
        c2['close'] > ((c0['open'] + c0['close']) / 2)):
        sinais.append({'sinal': 'CALL', 'padrao': 'estrela_manha'})

    # ----- Estrela da Tarde (PUT)
    if (c0['close'] > c0['open'] and
        corpo(c1) < corpo(c0) and
        c2['close'] < c2['open'] and
        c2['close'] < ((c0['open'] + c0['close']) / 2)):
        sinais.append({'sinal': 'PUT', 'padrao': 'estrela_tarde'})

    return sinais[-1] if sinais else None

# moving_averange_py
def verificar(candles, tipo="CALL"):
    if len(candles) < 20:
        return False
    media = sum(candles[-20:]) / 20
    preco = candles[-1]

    if tipo == "CALL":
        return preco > media
    elif tipo == "PUT":
        return preco < media
    return False

# fibonaci.py
def verificar(candles, tipo="CALL"):
    if len(candles) < 30:
        return False
    high = max(candles[-30:])
    low = min(candles[-30:])
    nivel_61 = low + 0.618 * (high - low)
    nivel_38 = low + 0.382 * (high - low)
    preco = candles[-1]

    if tipo == "CALL":
        return preco < nivel_61
    elif tipo == "PUT":
        return preco > nivel_38
    return False
 # bollinger.py
 def verificar(candles, tipo="CALL"):
    if len(candles) < 20:
        return False
    media = sum(candles[-20:]) / 20
    desvio = (sum((p - media) ** 2 for p in candles[-20:]) / 20) ** 0.5
    upper = media + 2 * desvio
    lower = media - 2 * desvio
    preco = candles[-1]

    if tipo == "CALL":
        return preco <= lower
    elif tipo == "PUT":
        return preco >= upper
    return False
