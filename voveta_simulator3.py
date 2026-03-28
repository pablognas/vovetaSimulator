import sys
import argparse
from sensor import Sensor
from dataclasses import dataclass, field
from typing import List

@dataclass
class Meio:
  simulationTime: int = 0
  tickCount: int = 0
  tickPeriod: int = 1000 # ms
  tick: bool = False
  nextTick: int = tickPeriod
  cycles: int = 500
  harvestingVariation: float = 7
  layers: int = 2
  nodesPerLayer: int = 2
  msgsReceived: int = 0
  msgsLost: int = 0
  step: int = 100
  messagesSent: List = field(default_factory=list)
  messagesScheduled: List = field(default_factory=list)
  wsn: List[Sensor] = field(default_factory=list)

  def __init__(self, harvestingVariation:float = 7, tickPeriod:float = 1000, cycles:int = 500, layers:int = 2, nodesPerLayer:int = 2, step:int = 100):
    # inicialização das variáveis de simulação e métricas de avaliação
    self.simulationTime = 0
    self.tickCount = 0
    self.tickPeriod = tickPeriod
    self.nextTick = tickPeriod
    self.cycles = cycles
    self.harvestingVariation = harvestingVariation
    self.layers = layers
    self.nodesPerLayer = nodesPerLayer
    self.msgsReceived = 0
    self.msgsLost = 0
    self.messagesSent = []
    self.messagesScheduled = []
    self.step = step
    self.wsn = self.criaRede()

    print(f'Running simulation with harvesting_variation={self.harvestingVariation}, tick_period={self.tickPeriod}, cycles={self.cycles}, layers={self.layers}, nodes_per_layer={self.nodesPerLayer}, step={self.step}')

    with open('simulation.log', 'w') as f:
      f.write(f'{sys._getframe().f_lineno} - Starting VoVeTA-like WSN simulation with {self.layers} layers and {self.nodesPerLayer} nodes per layer for {self.cycles} cycles\n')

    # adição da base station à rede
    self.wsn.insert(0, Sensor(id='base_station', energyLevel = 10000, layer = -1, index = 0, baseStation=True, maxEnergyLevel=1,parentId='base_station',activeTick=True, charged=True, energyState='energyActive'))

    # execução da simulação
    while self.tickCount < self.cycles:
      # executar um passo da simulação
      self.simulationTime += self.step # ms
      print(f'Simulation time: {self.simulationTime} ms, Tick count: {self.tickCount}')
      # incrementar o tickCount e atualizar o próximo tick
      if self.simulationTime >= self.nextTick:
        self.tick = True
        self.tickCount += 1
        self.nextTick += self.tickPeriod
        print(f'Tick {self.tickCount} at simulation time {self.simulationTime} ms')
        with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Tick {self.tickCount} at simulation time {self.simulationTime} ms\n')
      for node in self.wsn:
        # chamar a função de execução do passo para cada nó
        print(f'Running step for node {node.id} at layer {node.layer} and index {node.index}')
        newMessages = node.hardwareStep(self.step, tick=self.tick, messagesSent=self.messagesSent)
      # reset do tick para o próximo ciclo
      if self.tick:
        self.tick = False
    
    with open('simulation.log', 'a') as f:
      f.write(f'{sys._getframe().f_lineno} - Simulation finished after {self.cycles} cycles\n')
      f.write(f'{sys._getframe().f_lineno} - Total messages received: {self.msgsReceived}\n')
      f.write(f'{sys._getframe().f_lineno} - Total messages lost: {self.msgsLost}\n')

  def criaRede(self):
    wsn = []
    for layer in range(self.layers):
      for index in range(self.nodesPerLayer): wsn.append(Sensor(id=f'node_{layer}_{index}', layer=layer, index=index))
    return wsn

# def criaRede(num_layers: int, nodes_per_layer: int):
#   wsn = []
#   for layer in range(num_layers):
#     for index in range(nodes_per_layer):
#       node = Sensor(id=f'node_{layer}_{index}', layer=layer, index=index)
#       wsn.append(node) 
#   return wsn

# def main(harvesting_variation:float = 7, tick_period:float = 1000, cycles:int = 500, layers:int = 2, nodes_per_layer:int = 2, step:int = 100):
#   with open('simulation.log', 'w') as f:
#     f.write(f'{sys._getframe().f_lineno} - Starting VoVeTA-like WSN simulation with {layers} layers and {nodes_per_layer} nodes per layer for {cycles} cycles\n')
#   # configurações de tempo
#   simulationTime = 0 # ms
#   nextTick = tick_period
#   tickCount = 0

#   # inicializa as metricas:
#   msgsReceived = 0
#   msgsLost = 0

#   # criar a rede
#   wsn = criaRede(layers, nodes_per_layer)
#   # node = Sensor(energyLevel = 1, layer = 1, index = 0)
#   base = Sensor(id='base_station', energyLevel = 10000, layer = -1, index = 0, baseStation=True, maxEnergyLevel=1,parentId='base_station',activeTick=True)
#   wsn.append(base)

#   # prepara a lista de mensagens
#   messagesSent = []
#   messagesScheduled = []

#   while tickCount < cycles:
#     # executar um passo da simulação
#     simulationTime += step # ms
#     for node in wsn:
#       # chamar a função de execução do passo para cada nó
#       node.step(simulationTime)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Run VoVeTA-like WSN simulation')
  parser.add_argument('--harvesting_variation', type = float, default = 7)
  parser.add_argument('--tick_period', type = float, default = 1000) # in ms
  parser.add_argument('--cycles', type = int, default = 5)
  parser.add_argument('--layers', type = int, default = 2)
  parser.add_argument('--nodes_per_layer', type = int, default = 2)
  parser.add_argument('--step', type = int, default = 100)
  args = parser.parse_args()
  print(f'Running simulation with harvesting_variation={args.harvesting_variation}, tick_period={args.tick_period}, cycles={args.cycles}, layers={args.layers}, nodes_per_layer={args.nodes_per_layer}, step={args.step}')
  Meio(harvestingVariation=args.harvesting_variation, tickPeriod=args.tick_period, cycles=args.cycles, layers=args.layers, nodesPerLayer=args.nodes_per_layer, step=args.step)