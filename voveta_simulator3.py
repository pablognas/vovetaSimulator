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

def main(harvesting_variation:float = 7, tick_period:float = 1000, cycles:int = 500, layers:int = 2, nodes_per_layer:int = 2, step:int = 100):
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
    # executar um passo da simulação
    simulationTime += step # ms
    for node in wsn:
      # chamar a função de execução do passo para cada nó
      pass

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Run VoVeTA-like WSN simulation')
  parser.add_argument('--harvesting_variation', type = float, default = 7)
  parser.add_argument('--tick_period', type = float, default = 1000) # in ms
  parser.add_argument('--cycles', type = int, default = 5)
  parser.add_argument('--layers', type = int, default = 2)
  parser.add_argument('--nodes_per_layer', type = int, default = 2)
  parser.add_argument('--step', type = int, default = 100)
  args = parser.parse_args()
  main(harvesting_variation=args.harvesting_variation, tick_period=args.tick_period, cycles=args.cycles, layers=args.layers, nodes_per_layer=args.nodes_per_layer)