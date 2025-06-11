# ==================== IMPORTS ====================
import asyncio
import json
import websockets
import time
import traceback
from datetime import datetime
from typing import Literal, Dict, Any, Union
import pandas as pd
import inspect

# Tortoise ORM imports
from tortoise.contrib.fastapi import register_tortoise

# FastAPI imports
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from fastapi.responses import FileResponse

# Socket.IO imports
import socketio

# Módulos de configuração e segurança
from core.config import settings
from auth.router import router as auth_router
from models.user import User

# Utilitários e Estratégias
from utils.candle_builder import CandleBuilder
from estrategia import (
    reconhecimento, rsi, bollinger, fibonacci,
    moving_average, adx, volume, padroes_vela,
    vwap, macd_histogram, williams_r, atr 
)

# Mapeia nomes de string para módulos de estratégia
STRATEGY_MODULES = {
    "reconhecimento": reconhecimento, 
    "rsi": rsi, 
    "bollinger": bollinger,
    "fibonacci": fibonacci, 
    "moving_average": moving_average, 
    "adx": adx,
    "volume": volume, 
    "padroes_vela": padroes_vela,
    "vwap": vwap, 
    "macd_histogram": macd_histogram, 
    "williams_r": williams_r,
}

# ==================== AUTENTICAÇÃO E DEPENDÊNCIAS ====================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if (username := payload.get("sub")) is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if (user := await User.get_or_none(username=username)) is None:
        raise credentials_exception
    return user

# ==================== SCHEMAS Pydantic ====================
class NewsArticle(BaseModel):
    """Schema para um artigo de notícia na página de destino."""
    title: str
    summary: str
    image_url: str
    read_more_url: str

class PricingPlan(BaseModel):
    """Schema para um plano de preços na página de destino."""
    name: str
    description: str
    price: str
    features: list[str]
    button_text: str
    button_url: str
    is_premium: bool = False

class SettingsUpdate(BaseModel):
    """Schema para as configurações do usuário que podem ser atualizadas."""
    deriv_token: str | None = None
    stake: float | None = None
    duration: int | None = None
    candle_granularity: int | None = None
    logica_estrategia: Literal["OR", "AND"] | None = None
    contract_type_to_trade: Literal["CALLPUT", "ACCUMULATOR", "MULTIPLIER"] | None = None
    
    take_profit: int | None = None 
    stop_loss: int | None = None   

    accumulator_growth_rate: float | None = None
    take_profit_accumulator: float | None = None 
    stop_loss_accumulator: float | None = None   

    multiplier_value: int | None = None
    take_profit_multiplier: float | None = None  
    stop_loss_multiplier: float | None = None    

    estrategias_config_json: Dict[str, Any] = Field(default_factory=dict) 

class UserPublic(BaseModel):
    """Schema para dados públicos do usuário (sem informações sensíveis)."""
    id: int
    username: str
    plan_type: str
    premium_trial_end_date: Union[datetime, None] = None
    is_premium_active: bool = False 

    deriv_token: Union[str, None] = None 
    stake: Union[float, None] = None
    duration: Union[int, None] = None
    candle_granularity: Union[int, None] = None
    logica_estrategia: Union[Literal["OR", "AND"], None] = None
    contract_type_to_trade: Union[Literal["CALLPUT", "ACCUMULATOR", "MULTIPLIER"], None] = None

    take_profit: Union[int, None] = None
    stop_loss: Union[int, None] = None

    accumulator_growth_rate: Union[float, None] = None
    take_profit_accumulator: Union[float, None] = None
    stop_loss_accumulator: Union[float, None] = None

    multiplier_value: Union[int, None] = None
    take_profit_multiplier: Union[float, None] = None
    stop_loss_multiplier: Union[float, None] = None

    estrategias_config_json: Union[Dict[str, Any], None] = None

    class Config:
        from_attributes = True 
        json_encoders = { datetime: lambda dt: dt.isoformat() }

# ==================== CONSTANTS ====================
DERIV_WS_URL = "wss://ws.binaryws.com/websockets/v3?app_id=1089" # Use o seu App ID

# ==================== FASTAPI + SOCKET.IO SETUP ====================
app = FastAPI(title="KingBot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

# ==================== BOT SESSION ====================
user_bot_sessions: Dict[int, 'BotSession'] = {}

class BotSession:
    def __init__(self, user_id: int, deriv_token: str, initial_settings: SettingsUpdate, sio_server: socketio.AsyncServer):
        self.user_id = user_id
        self.sio = sio_server
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.token = deriv_token
        self.user_settings = initial_settings
        self.running = False
        self.is_trading_enabled = False
        self.active_contract_id: str | None = None
        self.active_contract_buy_price: float = 0.0
        self.run_task: asyncio.Task | None = None

        self.candle_builder = CandleBuilder(initial_settings.candle_granularity or 60)
        self.current_symbol = "R_100"
        self.trade_count, self.win_count, self.loss_count, self.total_profit_loss = 0, 0, 0, 0.0
        print(f"Sessão Bot inicializada para user {self.user_id}")
        print(f"Configurações iniciais do bot: {initial_settings.dict()}")


    async def send_log(self, message: str, level: str = 'info'):
        print(f"[User {self.user_id}][{level.upper()}] {message}")
        await self.sio.emit('bot_log', {'message': message, 'level': level}, room=str(self.user_id))

    async def update_status_to_client(self):
        await self.sio.emit('bot_status_update', {'running': self.running}, room=str(self.user_id))

    def reset_session_state(self, new_settings: SettingsUpdate):
        self.running, self.is_trading_enabled, self.ws, self.active_contract_id = False, False, None, None
        self.trade_count, self.win_count, self.loss_count, self.total_profit_loss = 0, 0, 0, 0.0
        self.active_contract_buy_price = 0.0
        self.run_task = None

        if new_settings.deriv_token: self.token = new_settings.deriv_token
        self.user_settings = new_settings
        self.candle_builder = CandleBuilder(new_settings.candle_granularity or 60)
        print(f"DEBUG: BotSession resetada para user {self.user_id} com novas configurações: {new_settings.dict()}")

    async def connect_and_run(self):
        if self.running:
            await self.send_log("⚠️ Bot já está em execução.", 'warning')
            return

        self.running = True
        await self.update_status_to_client()
        await self.send_log("A iniciar o bot...", 'info')

        try:
            async with websockets.connect(DERIV_WS_URL) as ws:
                self.ws = ws
                await self.send_log("Conectado à Deriv. A autenticar...", 'info')
                await self.ws.send(json.dumps({"authorize": self.token}))

                while self.running:
                    try:
                        message = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
                        if not self.running:
                            break
                        await self.process_message(json.loads(message))
                    except asyncio.TimeoutError:
                        if not self.running:
                            break
                        if self.is_trading_enabled and not self.active_contract_id:
                            await self.make_decision_and_trade()
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        await self.send_log("Conexão WebSocket foi fechada.", 'warning')
                        break
                    except Exception as e:
                        await self.send_log(f"Erro no loop principal: {e}", 'error')
                        traceback.print_exc()
                        break
        except Exception as e:
            await self.send_log(f"Falha crítica ao conectar à Deriv: {e}", 'error')
            traceback.print_exc()
        finally:
            self.running = False
            self.is_trading_enabled = False
            await self.update_status_to_client()
            await self.send_log("Bot parado.", 'info')

    async def process_message(self, data: dict):
        msg_type = data.get('msg_type')

        if 'error' in data:
            error_message = data['error'].get('message', 'Erro desconhecido.')
            await self.send_log(f"Erro da API ({msg_type}): {error_message}", 'error')
            if msg_type == 'authorize':
                self.running = False
                await self.send_log("Falha na autenticação. Verifique seu token da Deriv.", 'error')
            if msg_type in ['buy', 'proposal']:
                self.is_trading_enabled = True
            return

        if msg_type == 'authorize':
            await self.send_log("Autenticação bem-sucedida.", 'success')
            await self.sio.emit('account_info', data['authorize'], room=str(self.user_id))

            await self.send_log(f"A subscrever ao histórico de velas ({self.user_settings.candle_granularity}s)...", 'info')
            await self.ws.send(json.dumps({
                "ticks_history": self.current_symbol,
                "style": "candles",
                "granularity": self.user_settings.candle_granularity,
                "end": "latest",
                "count": 750,
                "subscribe": 1
            }))
            await self.ws.send(json.dumps({"transaction": 1, "subscribe": 1}))
            self.is_trading_enabled = True

        elif msg_type == 'ohlc':
            if candle_data := data.get('ohlc'):
                self.candle_builder.add_candle(candle_data)
                await self.make_decision_and_trade()

        elif msg_type == 'proposal':
            if not (proposal_id := data.get('proposal', {}).get('id')):
                await self.send_log("Proposta inválida recebida. A tentar novamente...", 'error')
                self.is_trading_enabled = True
                return
            await self.send_log(f"Proposta recebida (ID: {proposal_id}). A comprar contrato...", 'info')
            self.active_contract_buy_price = float(data.get('proposal', {}).get('ask_price', self.user_settings.stake))
            await self.buy_contract(proposal_id)

        elif msg_type == 'buy':
            contract_details = data['buy']
            self.active_contract_id = contract_details['contract_id']
            self.trade_count += 1
            await self.send_log(f"Contrato comprado! ID: {self.active_contract_id}, Preço: {contract_details.get('buy_price'):.2f} USD", 'success')
            await self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": self.active_contract_id, "subscribe": 1}))

        elif msg_type == 'proposal_open_contract':
            contract = data.get('proposal_open_contract')
            if contract and contract.get('contract_id') == self.active_contract_id and contract.get('is_sold'):
                await self.process_sold_contract(contract)

        elif msg_type == 'transaction' and (tx := data.get('transaction')):
            if tx.get('action') == 'sell' and tx.get('contract_id') == self.active_contract_id:
                sell_price = float(tx.get('amount', 0))
                profit_or_loss = sell_price - self.active_contract_buy_price
                balance_after = tx.get('balance_after')

                await self.send_log(f"Transação de fecho detectada (ID: {tx['contract_id']}). Lucro/Prejuízo: {profit_or_loss:.2f}", 'info')

                closed_contract_data = {
                    'profit': profit_or_loss,
                    'contract_id': tx['contract_id'],
                    'is_sold': 1,
                    'balance_after': balance_after
                }
                await self.process_sold_contract(closed_contract_data)

        elif msg_type == 'ping':
            await self.ws.send(json.dumps({"pong": 1}))

        elif msg_type != 'tick' and msg_type != 'transaction':
            await self.send_log(f"Mensagem não tratada: {msg_type} - {json.dumps(data)}", "debug")


    async def make_decision_and_trade(self):
        if not self.running or not self.is_trading_enabled or self.active_contract_id:
            return

        df = self.candle_builder.get_dataframe()

        min_period_required = 1
        active_strategies = self.user_settings.estrategias_config_json.get('strategies_enabled', [])

        for strategy_name in active_strategies:
            strategy_params_map = {
                "rsi": ("rsi_period", 14), "bollinger": ("bollinger_period", 20),
                "moving_average": ("ma_window", 20), "adx": ("adx_period", 14),
                "volume": ("volume_history_periods", 20), "fibonacci": ("fib_period", 50),
                "vwap": ("vwap_window", 14), "macd_histogram": ("macd_slow", 26),
                "williams_r": ("williams_period", 14),
            }
            if strategy_name in strategy_params_map:
                param_key, default_period = strategy_params_map[strategy_name]
                configured_period = self.user_settings.estrategias_config_json.get(param_key, default_period)
                min_period_required = max(min_period_required, int(configured_period))

        if self.user_settings.contract_type_to_trade == "ACCUMULATOR" and \
           self.user_settings.estrategias_config_json.get('use_dynamic_sl', False):
            atr_window = self.user_settings.estrategias_config_json.get('atr_window', 14)
            min_period_required = max(min_period_required, int(atr_window) + 1)

        min_period_required += 5

        if df.empty or len(df) < min_period_required:
            await self.send_log(f"A aguardar dados suficientes. Necessário {min_period_required} velas, encontrado {len(df)}.", "debug")
            return

        decision = await self.apply_strategies(df)

        if decision in ["buy", "sell"]:
            await self.send_log(f"Decisão final: {decision.upper()} para {self.user_settings.contract_type_to_trade}. A enviar proposta...", 'info')
            self.is_trading_enabled = False
            await self.propose_contract(decision)

    async def apply_strategies(self, df: pd.DataFrame) -> Literal["buy", "sell", "hold"]:
        strategies_conf = self.user_settings.estrategias_config_json or {}
        active_strategies = strategies_conf.get('strategies_enabled', [])
        if not active_strategies: return "hold"

        signals = []
        for name in active_strategies:
            if module := STRATEGY_MODULES.get(name):
                try:
                    strategy_params = {k: v for k, v in strategies_conf.items()}
                    analyze_func = getattr(module, 'analyze')
                    sig_params = inspect.signature(analyze_func).parameters
                    filtered_params = {}
                    if name == "rsi": filtered_params = { "rsi_period": strategy_params.get('rsi_period', 14), "rsi_overbought": strategy_params.get('rsi_overbought', 70), "rsi_oversold": strategy_params.get('rsi_oversold', 30), }
                    elif name == "bollinger": filtered_params = { "bollinger_period": strategy_params.get('bollinger_period', 20), "bollinger_dev": strategy_params.get('bollinger_std_dev', 2.0), }
                    elif name == "macd_histogram": filtered_params = { "macd_fast": strategy_params.get('macd_fast', 12), "macd_slow": strategy_params.get('macd_slow', 26), "macd_sign": strategy_params.get('macd_sign', 9), }
                    elif name == "adx": filtered_params = { "adx_period": strategy_params.get('adx_period', 14), "adx_threshold": strategy_params.get('adx_threshold', 25), }
                    elif name == "moving_average": filtered_params = { "ma_window": strategy_params.get('ma_window', 20), }
                    elif name == "volume": filtered_params = { "volume_factor": strategy_params.get('volume_factor', 1.5), "volume_history_periods": strategy_params.get('volume_history_periods', 20), }
                    elif name == "fibonacci": filtered_params = { "fib_period": strategy_params.get('fib_period', 50), }
                    elif name == "vwap": filtered_params = { "vwap_window": strategy_params.get('vwap_window', 14), }
                    elif name == "williams_r": filtered_params = { "williams_period": strategy_params.get('williams_period', 14), "williams_overbought": strategy_params.get('williams_overbought', -20), "williams_oversold": strategy_params.get('williams_oversold', -80), }

                    if 'send_log' in sig_params: sig = analyze_func(df.copy(), **filtered_params, send_log=self.send_log)
                    else: sig = analyze_func(df.copy(), **filtered_params)
                    if sig == "buy": sig = "UP"
                    if sig == "sell": sig = "DOWN"
                    if sig in ["UP", "DOWN"]:
                        await self.send_log(f"Sinal de '{name}': {sig}", 'debug')
                        signals.append("buy" if sig == "UP" else "sell")
                except Exception as e:
                    await self.send_log(f"Erro ao executar estratégia '{name}': {e}", 'error')
                    traceback.print_exc()

        if not signals: return "hold"

        logic = self.user_settings.logica_estrategia
        final_decision = "hold"
        if logic == "AND":
            if len(signals) == len(active_strategies) and all(s == signals[0] for s in signals):
                final_decision = signals[0]
                await self.send_log(f"Lógica AND: Todas as {len(active_strategies)} estratégias concordaram em '{final_decision.upper()}'.", "debug")
        else:
            buy_count = signals.count("buy")
            sell_count = signals.count("sell")
            if buy_count > sell_count: final_decision = "buy"
            elif sell_count > buy_count: final_decision = "sell"
            if final_decision != "hold":
                 await self.send_log(f"Lógica OR: Decisão final é '{final_decision.upper()}' baseada em {signals}.", "debug")

        return final_decision

    async def propose_contract(self, action: Literal["buy", "sell"]):
        try:
            payload = {
                "proposal": 1,
                "amount": self.user_settings.stake,
                "basis": "stake",
                "currency": "USD",
                "symbol": self.current_symbol
            }
            ctype = self.user_settings.contract_type_to_trade
            s_conf = self.user_settings.estrategias_config_json or {}

            if ctype == "CALLPUT":
                payload.update({
                    "contract_type": "CALL" if action == "buy" else "PUT",
                    "duration": self.user_settings.duration,
                    "duration_unit": "s"
                })
            elif ctype == "ACCUMULATOR":
                if action == "sell":
                    await self.send_log("Aviso: ACCUMULATOR não suporta 'SELL'. Operação ignorada.", 'warning')
                    self.is_trading_enabled = True
                    return

                payload.update({
                    "contract_type": "ACCU",
                    "growth_rate": self.user_settings.accumulator_growth_rate or 0.02,
                })

                # A API está a rejeitar take_profit e stop_loss para ACCUMULATOR na proposta.
                # A lógica foi removida para evitar o erro. O contrato funcionará sem TP/SL definidos.
                await self.send_log("Aviso: TP/SL não serão definidos para Accumulator para evitar erro da API.", "warning")

            elif ctype == "MULTIPLIER":
                payload.update({
                    "contract_type": "MULTUP" if action == "buy" else "MULTDOWN",
                    "multiplier": self.user_settings.multiplier_value or 100,
                })
                if tp := self.user_settings.take_profit_multiplier: payload['take_profit'] = tp
                if sl := self.user_settings.stop_loss_multiplier: payload['stop_loss'] = sl

            # Garantia final de que 'duration' não é enviado para contratos errados
            if ctype != "CALLPUT":
                payload.pop('duration', None)
                payload.pop('duration_unit', None)

            await self.send_log(f"Enviando proposta com payload: {json.dumps(payload)}", "debug")
            await self.ws.send(json.dumps(payload))
        except Exception as e:
            await self.send_log(f"Erro ao enviar proposta: {e}", "error")
            traceback.print_exc()
            self.is_trading_enabled = True

    async def buy_contract(self, proposal_id: str):
        try:
            payload = {"buy": proposal_id, "price": self.active_contract_buy_price}
            await self.send_log(f"Enviando ordem de compra: {json.dumps(payload)}", 'debug')
            await self.ws.send(json.dumps(payload))
        except Exception as e:
            await self.send_log(f"Erro ao comprar contrato: {e}", "error")
            self.is_trading_enabled = True

    async def process_sold_contract(self, contract):
        profit = float(contract['profit'])
        contract_id = contract['contract_id']
        balance_after = contract.get('balance_after')

        if contract_id != self.active_contract_id:
            await self.send_log(f"Recebido fecho para contrato antigo ({contract_id}). Ignorando.", "debug")
            return

        self.total_profit_loss += profit

        if profit >= 0:
            self.win_count += 1
            await self.send_log(f"✅ Vitória! Lucro: {profit:.2f} USD. (Total P/L: {self.total_profit_loss:.2f})", 'success')
        else:
            self.loss_count += 1
            await self.send_log(f"❌ Derrota! Prejuízo: {abs(profit):.2f} USD. (Total P/L: {self.total_profit_loss:.2f})", 'error')

        self.active_contract_id = None
        self.active_contract_buy_price = 0.0

        trade_update_data = {
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'total_profit_loss': f"{self.total_profit_loss:.2f}",
            'balance_after': balance_after
        }
        await self.sio.emit('trade_update', trade_update_data, room=str(self.user_id))

        await asyncio.sleep(0.1)
        self.is_trading_enabled = True

        if self.user_settings.contract_type_to_trade == "CALLPUT":
            if (tp := self.user_settings.take_profit) and self.win_count >= tp:
                await self.send_log(f"🎉 Take Profit atingido ({self.win_count} vitórias)! A parar o bot.", 'success')
                self.running = False
            elif (sl := self.user_settings.stop_loss) and self.loss_count >= sl:
                await self.send_log(f"🛑 Stop Loss atingido ({self.loss_count} derrotas)! A parar o bot.", 'error')
                self.running = False

        if not self.running:
            await self.stop_bot_logic()

    async def stop_bot_logic(self):
        """Lógica centralizada para parar o bot."""
        if not self.running: return

        await self.send_log("Comando para parar o bot recebido...", "warning")
        self.running = False

        if self.run_task and not self.run_task.done():
            self.run_task.cancel()
            try:
                await self.run_task
            except asyncio.CancelledError:
                await self.send_log("Tarefa do bot foi cancelada.", "info")
            except Exception as e:
                await self.send_log(f"Erro ao cancelar tarefa do bot: {e}", "error")

        if self.ws and not self.ws.closed:
            await self.ws.close()
            await self.send_log("Conexão WebSocket fechada ativamente.", "info")

        self.run_task = None
        await self.update_status_to_client()


# ==================== ROTAS FASTAPI ====================
app.include_router(auth_router, prefix="/auth", tags=["Autenticação"])

@app.get("/api/user/me", response_model=UserPublic)
async def read_current_user_data(current_user: User = Depends(get_current_user)):
    """
    Retorna os dados do usuário logado, incluindo suas configurações, garantindo que
    todos os campos opcionais e JSONField sejam tratados corretamente.
    """
    parsed_settings = {
        "id": current_user.id,
        "username": current_user.username,
        "plan_type": getattr(current_user, 'plan_type', 'free'),
        "premium_trial_end_date": current_user.premium_trial_end_date,
        "is_premium_active": current_user.is_premium_active(),
        "deriv_token": current_user.get_deriv_token(), 
        "stake": getattr(current_user, 'stake', None),
        "duration": getattr(current_user, 'duration', None),
        "candle_granularity": getattr(current_user, 'candle_granularity', None),
        "logica_estrategia": getattr(current_user, 'logica_estrategia', 'OR'),
        "contract_type_to_trade": getattr(current_user, 'contract_type_to_trade', 'CALLPUT'),
        "take_profit": getattr(current_user, 'take_profit', None),
        "stop_loss": getattr(current_user, 'stop_loss', None),
        "accumulator_growth_rate": getattr(current_user, 'accumulator_growth_rate', None),
        "take_profit_accumulator": getattr(current_user, 'take_profit_accumulator', None),
        "stop_loss_accumulator": getattr(current_user, 'stop_loss_accumulator', None),
        "multiplier_value": getattr(current_user, 'multiplier_value', None),
        "take_profit_multiplier": getattr(current_user, 'take_profit_multiplier', None),
        "stop_loss_multiplier": getattr(current_user, 'stop_loss_multiplier', None),
        "estrategias_config_json": current_user.get_strategy_config(), 
    }
    
    return UserPublic(**parsed_settings)


@app.post("/api/user/settings", status_code=status.HTTP_200_OK)
async def update_user_settings(settings_update: SettingsUpdate, current_user: User = Depends(get_current_user)):
    """Atualiza as configurações do usuário na base de dados."""
    print(f"DEBUG: A salvar configurações para {current_user.username}: {settings_update.dict()}")
    update_data = settings_update.dict(exclude_unset=True)
    
    if "deriv_token" in update_data: 
        current_user.set_deriv_token(update_data.pop("deriv_token"))

    if "estrategias_config_json" in update_data:
        current_user.estrategias_config_json = update_data.pop("estrategias_config_json")
    
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
        else:
            print(f"ATENÇÃO: Campo '{field}' não encontrado no modelo User. Não foi salvo.")
            
    await current_user.save()
    return {"message": "Configurações salvas com sucesso!"}

@app.post("/api/bot/start", status_code=status.HTTP_200_OK)
async def start_bot(settings_payload: SettingsUpdate, user: User = Depends(get_current_user)):
    """
    Inicia o bot de trading para o usuário.
    Recebe as configurações do frontend diretamente no payload.
    """
    if not (token := user.get_deriv_token()):
        # Se o token não está no DB, verifica se veio no payload (e.g., primeira vez usando)
        if not settings_payload.deriv_token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token da Deriv não configurado.")
        final_token = settings_payload.deriv_token
    else:
        final_token = token

    if user.id in user_bot_sessions and user_bot_sessions[user.id].running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bot já está em execução.")
    
    if user.id not in user_bot_sessions:
        user_bot_sessions[user.id] = BotSession(user.id, final_token, settings_payload, sio)
    else:
        # Se já existe uma sessão, mas o bot está parado, reseta e inicia com novas configurações
        user_bot_sessions[user.id].reset_session_state(settings_payload)
    
    # Garante que a tarefa anterior foi limpa e que não há uma tarefa "done" no Task list
    session = user_bot_sessions[user.id]
    if session.run_task and not session.run_task.done():
        await session.send_log("Tentativa de iniciar um bot com tarefa já existente. A tarefa está a ser cancelada para reiniciar.", "warning")
        session.run_task.cancel()
        try:
            await session.run_task # Espera a tarefa antiga terminar o cancelamento
        except asyncio.CancelledError:
            pass # Isso é esperado
        session.run_task = None # Limpa a referência após o cancelamento

    # Cria a nova tarefa e guarda a referência na sessão
    session.run_task = asyncio.create_task(session.connect_and_run())
    
    return {"message": "Comando para iniciar o bot enviado!"}

@app.post("/api/bot/stop", status_code=status.HTTP_200_OK)
async def stop_bot(user: User = Depends(get_current_user)):
    session = user_bot_sessions.get(user.id)
    if not session or not session.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O bot não está em execução.")

    await session.send_log("Comando para parar o bot recebido...", "warning")
    
    # Define a flag 'running' como False, que será pega pelo loop principal
    session.running = False

    # Tenta cancelar a tarefa ativamente se ela ainda estiver em execução
    if session.run_task and not session.run_task.done():
        session.run_task.cancel()
        try:
            # Espera a tarefa terminar após o cancelamento (para limpar recursos)
            await session.run_task
        except asyncio.CancelledError:
            # Este erro é esperado e indica que o cancelamento foi bem-sucedido
            await session.send_log("Tarefa do bot foi cancelada com sucesso.", "info")
        except Exception as e:
            await session.send_log(f"Erro ao cancelar tarefa do bot: {e}", "error")
        finally:
            session.run_task = None # Limpa a referência da tarefa após o término

    # Adição crucial: Fecha explicitamente a conexão WebSocket para interromper imediatamente o recv()
    if session.ws and not session.ws.closed:
        await session.ws.close()
        await session.send_log("Conexão WebSocket fechada ativamente.", "info")

    # Garante que o status final é 'parado' na UI
    await session.update_status_to_client()
            
    return {"message": "Comando para parar o bot enviado e executado."}

@app.get("/api/bot/status", status_code=status.HTTP_200_OK)
async def get_bot_status(user: User = Depends(get_current_user)):
    session = user_bot_sessions.get(user.id)
    return {"running": session.running if session else False}

# ==================== ROTAS PÚBLICAS E ARQUIVOS ESTÁTICOS ====================
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/", include_in_schema=False)
async def read_lading_page(): return FileResponse('static/lading.html')

# ==================== EVENTOS SOCKET.IO ====================
@sio.on('connect')
async def handle_connect(sid, environ):
    print(f"Cliente conectado: {sid}")
    # A autenticação será tratada pelo evento 'join_user_room' enviado pelo cliente
    pass

@sio.on('disconnect')
def handle_disconnect(sid): print(f"Cliente desconectado: {sid}")

@sio.on('join_user_room')
async def handle_join_user_room(sid, data):
    token = data.get('token')
    if token:
        try:
            user = await get_current_user(token)
            user_id = user.id
            sio.enter_room(sid, str(user_id))
            print(f"Cliente {sid} autenticado e entrou na sala {user_id}")
            await sio.emit('bot_log', {'message': f"Conectado à sua sessão: {user.id}", 'level': 'info'}, room=str(user_id))
            if user_id in user_bot_sessions and user_bot_sessions[user_id].running:
                await sio.emit('bot_log', {'message': 'Seu bot já está ativo. Sincronizando estado.', 'level': 'info'}, room=str(user_id))
                await user_bot_sessions[user_id].update_status_to_client()
        except HTTPException:
             await sio.emit('auth_error', {'message': 'Token inválido.'}, room=sid)
             print(f"Falha na autenticação do Socket.IO para o cliente {sid}")


# ==================== INICIALIZAÇÃO DA BASE DE DADOS ====================
register_tortoise(
    app, db_url=settings.DATABASE_URL,
    modules={"models": ["models.user", "aerich.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
