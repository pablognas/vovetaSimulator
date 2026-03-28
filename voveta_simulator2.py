import sys
import argparse
from sensor import Sensor, energyHarvested
from messages import SetupMessage,shortMessageConsumption,fullMessageConsumption, addMessage
from random import random

def criaRede(num_layers: int, nodes_per_layer: int):
  wsn = []
  for layer in range(num_layers):
    for index in range(nodes_per_layer):
      node = Sensor(id=f'node_{layer}_{index}', layer=layer, index=index)
      wsn.append(node) 
  return wsn

def main(harvesting_variation:float = 7, tick_period:float = 1000, cycles:int = 500, layers:int = 2, nodes_per_layer:int = 2):
    with open('simulation.log', 'w') as f:
      f.write(f'{sys._getframe().f_lineno} - Starting VoVeTA-like WSN simulation with {layers} layers and {nodes_per_layer} nodes per layer for {cycles} cycles\n')
    # configurações de tempo
    simulationTime = 0 # ms
    nextTick = tick_period
    tickCount = 0

    # inicializa as metricas:
    msgsReceived = 0
    msgsLost = 0

    # criar a rede
    wsn = criaRede(layers, nodes_per_layer)
    # node = Sensor(energyLevel = 1, layer = 1, index = 0)
    base = Sensor(id='base_station', energyLevel = 10000, layer = -1, index = 0, baseStation=True, maxEnergyLevel=1,parentId='base_station',activeTick=True)
    wsn.append(base)

    # prepara a lista de mensagens
    messagesSent = []
    messagesScheduled = []
    
    while tickCount < cycles:
      simulationTime += 100 # ms
      # print(f'{sys._getframe().f_lineno} - Tick {tickCount}')
      # processa as mensagens recebidas
      for node in wsn:
        with open('simulation.log', 'a') as f:
          f.write(f'{sys._getframe().f_lineno} - Time {simulationTime} ms - Node {node.id} energy level: {node.energyLevel:.4f} J max energy: {node.maxEnergyLevel:.4f} J\n')
        if not node.baseStation:
          # node.energyLevel += energyHarvested(simulationTime / 1000, args.harvesting_variation) / 1000  # J/ms
          node.energyLevel += 1e-2  # J/ms
          if node.energyLevel >= node.maxEnergyLevel:
            node.energyLevel = node.maxEnergyLevel  
            if not node.charged:
              node.charged = True
              node.chargingCycles = node.chargingCyclesCounter + 1 
              node.chargingCyclesCounter = 0
              with open('simulation.log', 'a') as f:
                f.write(f'{sys._getframe().f_lineno} - Time {simulationTime} ms - Node {node.id} full charge reached. Total cycles: {node.chargingCycles}\n')
              # print(sys._getframe(0).f_lineno,f'Time {simulationTime} ms - Node {node.id} full charge reached. Total cycles: {node.chargingCycles}'
      for message in messagesScheduled:
        if message.sendtime <= simulationTime:
          messagesSent.append(message)
          messagesScheduled.remove(message)
          with open('simulation.log', 'a') as f:
            f.write(f'{sys._getframe().f_lineno} - Time {simulationTime} ms - Message from node {message.senderId} scheduled for sending at time {message.sendtime} ms is now sent\n')

      if simulationTime >= nextTick: # \If{node counts a tick} \label{if:tick count}
        # tem que fazer o tratamento de quais nós estavam ativos no tick anterior, tirar a energia gasta nesse periodo, desativa-los e ativar os nos do tick corrente
        nextTick += args.tick_period
        tickCount += 1
        with open('simulation.log', 'a') as f:
          f.write(f'{sys._getframe().f_lineno} - Tick {format(tickCount)}\n')
        wsn[-1].tickCount += 1
        base = wsn[-1]
        messagesScheduled = addMessage(messagesScheduled, SetupMessage(senderId=base.id, senderIdLayer=base.layer, chargingTime=base.chargingCycles,status='setup', scheduledMeetings=base.scheduledMeetings, tickCount=base.tickCount, sendtime=simulationTime+int(random()*200))) # broadcast setup message

        for layer in range(layers):
          for node in wsn:
            if node.layer == layer:
              node.tickCount += 1
              if not node.baseStation and node.charged and not node.scheduledMeetings: # \If{the node has no scheduled meetings} \label{if:no scheduled meetings}
                node.activeTick = True
                node.charged = False
              elif not node.baseStation and node.scheduledMeetings: # \If{the node has scheduled meetings} \label{if:scheduled meetings}
                for meeting in node.scheduledMeetings:
                  if meeting[2] == node.tickCount: # \If{the scheduled meeting is for the current tick} \label{if:scheduled meeting for current tick}
                    node.activeTick = True
                    node.scheduledMeetings.remove(meeting) # \State Remove the meeting from the schedule \label{st:remove meeting from schedule}
                    if node.charged:
                      with open('simulation.log','a') as f: f.write(f'{node.id} met {meeting[0]} at {meeting[2]}\n')
                      node.addMeeting([meeting[0],meeting[1],meeting[1]+meeting[2]])
                    else:
                      with open('simulation.log','a') as f: f.write(f'{node.id} lost meeting with {meeting[0]} at {meeting[2]}')
              elif not node.baseStation and not node.charged and node.activeTick: # \If{the node is not fully charged but was active in the previous tick} \label{if:not fully charged but active in previous tick}
                node.activeTick = False
              with open('simulation.log', 'a') as f:                 f.write(f'{sys._getframe().f_lineno} - Checking node {node.id} from layer {node.layer} at tick {tickCount} - activeTick: {node.activeTick} - energyLevel: {node.energyLevel:.4f} J - scheduledMeetings: {node.scheduledMeetings}\n')
              if node.activeTick:
                with open('simulation.log', 'a') as f:
                  f.write(f'{sys._getframe().f_lineno} - Node {node.id} from layer {node.layer} is active at tick {tickCount}\n')
                if node.status == False: # \If{build-up mode} \label{if:build-up}
                  if node.parentId is not None: # \If{node has a parent} \label{if:parent}
                    # print(f'{sys._getframe().f_lineno} - Node {node.id} is broadcasting setup message to find children')
                    with open('simulation.log', 'a') as f:
                      f.write(f'{sys._getframe().f_lineno} - Node {node.id} is broadcasting setup message to find children\n')
                    messagesScheduled = addMessage(messagesScheduled, SetupMessage(senderId=node.id, senderIdLayer=node.layer , chargingTime=node.chargingCycles,status='setup', scheduledMeetings=node.scheduledMeetings, tickCount=node.tickCount, sendtime=simulationTime+int(random()*200))) # broadcast setup message
                    if not node.baseStation:
                      node.energyLevel -= shortMessageConsumption # gasto de energia por envio de mensagem de setup
                  else:
                    # print(f'{sys._getframe().f_lineno} - Node {node.id} has no parent and is not the base station, so it cannot send setup messages')
                    with open('simulation.log', 'a') as f:
                      f.write(f'{sys._getframe().f_lineno} - Node {node.id} has no parent and is not the base station, so it cannot send setup messages\n')
                else:
                  # print(f'{sys._getframe().f_lineno} - Node {node.id} is in steady-state mode and is not sending setup messages')
                  with open('simulation.log', 'a') as f:
                    f.write(f'{sys._getframe().f_lineno} - Node {node.id} is in transfer mode and is not sending setup messages\n')
      with open('simulation.log','a') as f:
        f.write(f'{sys._getframe().f_lineno} - {len(messagesSent)} messages in the queue at time {simulationTime} ms\n')
      rmvMessages = []
      wsnMode = wsn[-1].status # o modo da WSN é definido pelo status da base station
      for message in messagesSent:
        with open('simulation.log','a') as f:
          f.write(f'{sys._getframe().f_lineno} - Message: {message}\n')
        if message.sendtime + 1000 <= simulationTime:
          rmvMessages.append(message)
          continue
        if wsnMode == True:
          with open('simulation.log','a') as f:
            f.write(f'{sys._getframe().f_lineno} - WSN is in transfer mode at time {simulationTime} ms\n') 
        elif wsnMode == False: # build-up mode
          with open('simulation.log','a') as f:
            f.write(f'{sys._getframe().f_lineno} - WSN is in build-up mode at time {simulationTime} ms\n')
          layerCounter = message.senderIdLayer - 1
          if layerCounter < -1:
            layerCounter = -1
          while layerCounter <= message.senderIdLayer + 1: # \While{there are layers to check for neighbors} \label{while:layers to check for neighbors}
            for node in wsn:
              if node.layer == layerCounter and (layerCounter == message.senderIdLayer-1 or layerCounter == message.senderIdLayer+1) and node.activeTick: # \If{the node is in a neighbor layer from the sender and is active} \label{if:node in neighbor layer and active}
                if node.id not in message.received:
                  message.received.add(node.id)
                  with open('simulation.log','a') as f:
                    f.write(f'{sys._getframe().f_lineno} - Node {node.id} from layer {node.layer}, child of {node.parentId} received message from node {message.senderId} at time {simulationTime} ms\n')
                  msgsReceived += 1
                  if node.parentId is None: # \If{the node has no parent} \label{if:node has no parent}
                    if message.senderIdLayer == node.layer -1 and message.status == 'setup': # \If{the message comes from a higher layer and is a setup message and the node is active} \label{if:message from higher layer and setup and active}           
                      node.parentId = message.senderId # \State Register the sender as the parent \label{st:register parent}
                      node.layer = message.senderIdLayer + 1 # \State Register the node's layer as the sender's layer plus one \label{st:register layer}
                      node.addMeeting([message.senderId, message.chargingTime, node.tickCount+max(message.chargingTime, node.chargingCycles)+1]) # \State Register the scheduled meeting with the parent \label{st:register scheduled meeting}    
                  else:
                    with open('simulation.log','a') as f:
                      f.write(f'{sys._getframe().f_lineno} - Node {node.id}, {node.layer} - Message {message.senderId}, {message.senderIdLayer}, {message.scheduledMeetings}\n')
                     # 148 - Node node_0_1, 0 - Message base_station, -1, [] -> Ignorar
                     # 148 - Node base_station, -1 - Message node_0_1, 0, [['base_station', 0, 3]] -> Registrar filho e encontro
                    for meeting in message.scheduledMeetings:
                      if meeting[0] == node.id and meeting[2] == node.tickCount: # \If{the node already has a scheduled meeting with the sender} \label{if:node already has scheduled meeting with sender}
                        with open('simulation.log','a') as f:                          f.write(f'{sys._getframe().f_lineno} - Node {node.id} already has a scheduled meeting with sender {message.senderId} for tick {meeting[2]}\n')
                        pass
                      elif meeting[0] == node.id and meeting[2] > node.tickCount: # \If{the node has a scheduled meeting with the sender but for a future tick} \label{if:node has scheduled meeting with sender but for future tick}
                        if meeting not in node.scheduledMeetings:
                          node.addMeeting([message.senderId,meeting[1],meeting[2]]) # \State Register the meeting with the sender \label{st:register meeting with sender}
                          node.children.add(message.senderId) # \State Register the sender as a child \label{st:register sender as child}
                        with open('simulation.log','a') as f:
                          f.write(f'{sys._getframe().f_lineno} - {meeting}\n')

              elif node.layer == layerCounter and (layerCounter == message.senderIdLayer-1 or layerCounter == message.senderIdLayer+1) and not node.activeTick:
                if node.id not in message.ignored:
                  message.ignored.add(node.id)
                  msgsLost += 1
            layerCounter += 1
      while rmvMessages:
          messagesSent.remove(rmvMessages.pop())

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Run VoVeTA-like WSN simulation')
  parser.add_argument('--harvesting_variation', type = float, default = 7)
  parser.add_argument('--tick_period', type = float, default = 1000) # in ms
  parser.add_argument('--cycles', type = int, default = 500)
  parser.add_argument('--layers', type = int, default = 2)
  parser.add_argument('--nodes_per_layer', type = int, default = 2)
  args = parser.parse_args()
  main(harvesting_variation=args.harvesting_variation, tick_period=args.tick_period, cycles=args.cycles, layers=args.layers, nodes_per_layer=args.nodes_per_layer)