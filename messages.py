from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

shortMessageConsumption = 55e-9  # energia gasta para enviar uma mensagem curta (J)
fullMessageConsumption = 770e-9  # energia gasta para enviar uma mensagem completa (J)


@dataclass
class SetupMessage:
    senderId: str
    senderIdLayer: int
    status: str
    chargingTime: float
    scheduledMeetings: List[float] = field(default_factory=list)
    received: set = field(default_factory=set)
    ignored: set = field(default_factory=set)
    tickCount: int = 0
    sendtime: int = 0
            

def addMessage(messageList : List[SetupMessage], message: SetupMessage):
    i = 0
    while i < len(messageList) and messageList[i].sendtime <= message.sendtime:
        i += 1
    messageList.insert(i, message)
    return messageList




# Tipos de mensagens:
# 0 - transferencia de dados
# 1 - broadcast para encontrar filhos
# 2 - resposta para o pai com o tempo de carga e o encontro agendado
# 3 - treplica para o filho ajustando o tempo de encontros
# 4 - encontro teste bem sucedido
# 5 - fim do setup -> modo transferência
# 6 - falha no encontro -> modo setup