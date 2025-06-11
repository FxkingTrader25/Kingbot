# utils/candle_builder.py

import pandas as pd
from datetime import datetime

class CandleBuilder:
    """
    Constrói e gerencia um DataFrame de velas (candles) a partir de dados da API.
    Pode ser alimentado tanto por ticks individuais quanto por velas completas (OHLC).
    """
    def __init__(self, granularity: int):
        """
        Inicializa o construtor de velas.
        :param granularity: A granularidade da vela em segundos (ex: 60 para 1 minuto).
        """
        self.granularity = granularity
        self.columns = ['epoch', 'open', 'high', 'low', 'close', 'volume']
        self.candles_df = pd.DataFrame(columns=self.columns)
        self.current_tick_candle = {} # Dicionário para construir uma vela a partir de ticks
        print(f"CandleBuilder inicializado com granularidade de {self.granularity}s.")

    # utils/candle_builder.py

    def add_candle(self, ohlc_data: dict):
        """
        Adiciona uma vela completa (OHLC) recebida da API.
        """
        try:
            candle = {
                'epoch': int(ohlc_data['epoch']),
                'open': float(ohlc_data['open']),
                'high': float(ohlc_data['high']),
                'low': float(ohlc_data['low']),
                'close': float(ohlc_data['close']),
                'volume': float(ohlc_data.get('volume', 0))
            }
            
            new_candle_df = pd.DataFrame([candle])

            # =================== CORREÇÃO DO FUTUREWARNING ===================
            # Se o DataFrame principal estiver vazio, apenas o substitua
            if self.candles_df.empty:
                self.candles_df = new_candle_df
            else:
                # Caso contrário, execute a lógica de concatenação
                self.candles_df = self.candles_df[self.candles_df['epoch'] != candle['epoch']]
                self.candles_df = pd.concat([self.candles_df, new_candle_df], ignore_index=True)
            # ================================================================
            
            self.candles_df.drop_duplicates(subset=['epoch'], keep='last', inplace=True)
            self.candles_df.sort_values(by='epoch', inplace=True)
            
            if len(self.candles_df) > 750:
                self.candles_df = self.candles_df.iloc[-750:]

        except (ValueError, KeyError) as e:
            print(f"Erro ao processar a vela: {e}. Dados recebidos: {ohlc_data}")

    def get_dataframe(self) -> pd.DataFrame:
        """
        Retorna o DataFrame de velas atual, garantindo que os tipos de dados estejam corretos.
        """
        if self.candles_df.empty:
            return pd.DataFrame(columns=self.columns) # Retorna um DF vazio com colunas

        df = self.candles_df.copy()
        
        # Garante que as colunas numéricas tenham o tipo correto
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Opcional: remover linhas com NaNs resultantes da coerção
        df = df.dropna(subset=['open', 'high', 'low', 'close']) 
        
        return df

