from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

shortMessageConsumption = 325e-6  # energia gasta para enviar uma mensagem curta (J)
fullMessageConsumption = 325e-5  # energia gasta para enviar uma mensagem completa (J)
shortMessageDuration = 1 # ms
fullMessageDuration = 10 # ms

@dataclass
class SetupMessage:
    senderId: str # id do nó que envia a mensagem
    # senderIdLayer: int # camada do nó que envia a mensagem
    status: bool # indica se o setup já foi concluído naquele nó (True) ou se ainda está em processo de setup (False)
    chargingTime: float # quantidade de ticks que o nó precisa para carregar completamente
    scheduledMeetings: List[float] = field(default_factory=list) # lista de encontros agendados para o nó - cada encontro é representado por uma lista [id do nó, próximo encontro, ticks entre encontros]
    received: set = field(default_factory=set) # set de ids dos nós que já receberam a mensagem para calcular métricas
    ignored: set = field(default_factory=set) # set de ids dos nós que ignoraram a mensagem para calcular métricas
    tickCount: int = 0 # contador de ticks (relógio de Lamport)
    parentReady: bool = False # indica se o nó pai do nó que recebe a mensagem já está pronto para o setup - usado para que os nós saibam quando enviar a mensagem de resposta para o pai no setup
    # sendtime: int = 0 # tempo de envio da mensagem (ms) - usado para que o simulador saiba a hora de trocar a mensagem de agendada para enviada
    parentId: Optional[str] = None # id do nó pai - usado para que os nós saibam para quem enviar a mensagem de resposta no setup
            

def addMessage(messageList : List[SetupMessage], message: SetupMessage):
    i = 0
    while i < len(messageList) and messageList[i].sendtime <= message.sendtime:
        i += 1
    messageList.insert(i, message)
    return messageList


@dataclass
class DataMessage:
    senderId: str # id do nó que envia a mensagem
    data: Any # dados a serem enviados - pode ser qualquer tipo de dado, dependendo da aplicação
    # sendtime: int # tempo de envio da mensagem (ms) - usado para que o simulador saiba a hora de trocar a mensagem de agendada para enviada
    parentId: Optional[str] = None # id do nó pai - usado para que os nós saibam para quem enviar a mensagem de resposta no setup
    scheduledMeetings: List[float] = field(default_factory=list) # lista de encontros agendados para o nó - cada encontro é representado por uma lista [id do nó, próximo encontro, ticks entre encontros]
    originDataList: List[Dict] = field(default_factory=list) # lista de origens dos dados: cada entrada é {'nodeId', 'acquireTick', 'sendTime'}

@dataclass
class ParentReadyMessage:
    senderId: str # id do nó que envia a mensagem
    parentReady: bool # indica se o nó pai do nó que recebe a mensagem já está pronto para o setup - usado para que os nós saibam quando enviar a mensagem de resposta para o pai no setup

# Tipos de mensagens:
# 0 - transferencia de dados
# 1 - broadcast para encontrar filhos
# 2 - resposta para o pai com o tempo de carga e o encontro agendado
# 3 - treplica para o filho ajustando o tempo de encontros
# 4 - encontro teste bem sucedido
# 5 - fim do setup -> modo transferência
# 6 - falha no encontro -> modo setup