from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

shortMessageConsumption = 55e-9  # energia gasta para enviar uma mensagem curta (J)
fullMessageConsumption = 770e-9  # energia gasta para enviar uma mensagem completa (J)


@dataclass
class SetupMessage:
    senderId: str # id do nó que envia a mensagem
    senderIdLayer: int # camada do nó que envia a mensagem
    status: str # status do nó - setup ou data
    chargingTime: float # quantidade de ticks que o nó precisa para carregar completamente
    scheduledMeetings: List[float] = field(default_factory=list) # lista de encontros agendados para o nó - cada encontro é representado por uma lista [id do nó, próximo encontro, ticks entre encontros]
    received: set = field(default_factory=set) # set de ids dos nós que já receberam a mensagem para calcular métricas
    ignored: set = field(default_factory=set) # set de ids dos nós que ignoraram a mensagem para calcular métricas
    tickCount: int = 0 # contador de ticks (relógio de Lamport)
    sendtime: int = 0 # tempo de envio da mensagem (ms) - usado para que o simulador saiba a hora de trocar a mensagem de agendada para enviada
            

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