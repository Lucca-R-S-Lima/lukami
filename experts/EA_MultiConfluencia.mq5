/*
  EA Multiconfluência para MetaTrader 5
  Estratégia: Entrar quando pelo menos 80% dos principais indicadores apontarem na mesma direção e volume atual exceder média móvel.
  Lógica de saída: Ao atingir 1,5% de lucro, ativa trailing stop de 0,5%. Não fecha em TP fixo, só pelo trailing.
  Stop Loss automático em percentual do preço de entrada.
  Os detalhes dos indicadores e suas entradas serão implementados em etapas seguintes.
*/

#property copyright "lukami"
#property version   "1.02"
#property strict

//--- Input Parameters
input double  ConfluenciaPercent = 80.0;      // % de indicadores para entrada
input int     VolumeMAPeriod    = 20;         // Período da média móvel de volume
input double  TrailingThreshold = 1.5;        // % de lucro a partir do qual trailing é ativado
input double  TrailingDistance  = 0.5;        // % de trailing stop (distância do topo)
input double  TrailingBuyDrop   = 1.0;        // % de recuo para permitir nova compra após stop (trailing buy)
input double  LotSize           = 0.1;        // Tamanho padrão da ordem
input int     Slippage          = 10;         // Slippage permitido
input double  StopLossPercent   = 1.0;        // Percentual para Stop Loss a partir do preço de entrada

//--- State control variables
double gHighestProfit = 0.0;
bool   gTrailingActive = false;
double gEntryPrice = 0.0;
int    gLastTicket = -1;

//+------------------------------------------------------------------+
//| Função para calcular média móvel simples do volume               |
//+------------------------------------------------------------------+
double VolumeSMA(int period)
{
    double sum = 0.0;
    for(int i=0; i<period; i++)
        sum += iVolume(_Symbol, _Period, i);
    return sum/period;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("EA Multiconfluência inicializado.");
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
    // Cleanup if necessary
  }
//+------------------------------------------------------------------+
void OnTick()
  {
    // Verifica se tem posição aberta
    if(PositionSelect(_Symbol))
    {
      double posPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double curProfitPerc = ((SymbolInfoDouble(_Symbol, SYMBOL_BID) - posPrice) / posPrice) * 100.0;
      
      // Ativação do trailing stop
      if(!gTrailingActive && curProfitPerc >= TrailingThreshold)
      {
        gTrailingActive = true;
        gHighestProfit = curProfitPerc;
        Print("Trailing stop ativado");
      }
      
      // Se trailing ativo, atualiza ou fecha posição
      if(gTrailingActive)
      {
        if(curProfitPerc > gHighestProfit)
          gHighestProfit = curProfitPerc;

        double stopPrice = posPrice * (1.0 + (gHighestProfit - TrailingDistance)/100.0); // trailing stop dinâmico
        if(curProfitPerc <= (gHighestProfit - TrailingDistance))
        {
          // Fecha posição pelo trailing stop
          CloseAllPositions();
          gTrailingActive = false;
          Print("Posição fechada pelo trailing stop");
        }
        else
        {
          // (Opcional) Mover stop-loss para seguir, se desejar ordem virtual ou update real
        }
      }

      // (Opcional) implementar trailing buy lock (espera queda p/ reabrir compra)
    }
    else
    {
      // Checa se pode abrir nova ordem: trailing buy, confluência de indicadores, e filtro de volume médio
      if(CanOpenNewTrade())
      {
        // Avalia sinais dos indicadores (placeholder: implementar)
        int sinaisCompra = 0, sinaisVenda = 0, totalIndicadores = 5; // Supondo 5 ativos (ajustar depois)
        // TODO: Computar outputs reais dos indicadores aqui

        // Filtro dinâmico de volume
        double volumeAtual = iVolume(_Symbol, _Period, 0);
        double volumeMA = VolumeSMA(VolumeMAPeriod);
        if(volumeAtual <= volumeMA) return; // Volume insuficiente, não operar
        
        double confluenciaCompra = (double(sinaisCompra) / double(totalIndicadores)) * 100.0;
        if(confluenciaCompra >= ConfluenciaPercent)
        {
          // Abre ordem de compra
          OpenBuy();
        }
        // Implementar confluência para venda, caso deseje operar vendido
      }

    }
  }
//+------------------------------------------------------------------+

//--- Função para abrir compra
void OpenBuy()
{
  MqlTradeRequest req;
  MqlTradeResult  res;
  ZeroMemory(req);
  ZeroMemory(res);

  req.action   = TRADE_ACTION_DEAL;
  req.symbol   = _Symbol;
  req.volume   = LotSize;
  req.type     = ORDER_TYPE_BUY;
  req.price    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  
  // Implementação do stop loss em percentual
  double slPrice = req.price * (1.0 - StopLossPercent/100.0);
  req.sl       = NormalizeDouble(slPrice, _Digits);
  
  req.tp       = 0; // Sem take fixo, só trailing
  req.deviation= Slippage;

  if(!OrderSend(req,res) || res.retcode!=10009)
    Print("Erro ao abrir ordem de compra: ",res.comment);
  else
  {
    gEntryPrice = req.price;
    gLastTicket = res.order;
    Print("Ordem de compra aberta a ",gEntryPrice, 
          " | StopLoss: ", req.sl,
          " | Volume atual: ", iVolume(_Symbol, _Period, 0), 
          " | VolumeMA: ", VolumeSMA(VolumeMAPeriod));
  }
}

//--- Função para fechar todas as posições abertas
void CloseAllPositions()
{
  ulong ticket = PositionGetTicket(0);
  MqlTradeRequest req;
  MqlTradeResult  res;
  ZeroMemory(req);
  ZeroMemory(res);

  req.action   = TRADE_ACTION_DEAL;
  req.symbol   = _Symbol;
  req.position = ticket;
  req.volume   = PositionGetDouble(POSITION_VOLUME);
  req.type     = ORDER_TYPE_SELL;
  req.price    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  req.deviation= Slippage;
  if(!OrderSend(req,res))
    Print("Erro ao fechar posição: ",res.comment);
  else
    Print("Posição fechada a ",req.price);
}

//--- Placeholder: Lógica de confluência (só retorna true por enquanto)
bool CanOpenNewTrade()
{
  return true;
}
