from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from math import sin, pi
from random import randint

# energia = c*v*v/2 (J)
# W = J/s

def energyHarvested(simulation_time: float, variation: int = 7) -> float:
    """
    Calculate the total energy harvested over a given simulation time.

    Parameters:
    simulation_time (float): The total time of the simulation in seconds.
    variation (int): The percentage variation in harvested energy.

    Returns:
    float: The energy harvested in watts.
    """

    max_power = 0.4  # Maximum power in watts
    frequency = 1/(24*60*60)
    phi = 3*pi/2
    minimum_power = 1e-6 # Minimum power in watts
    harvestedPower = max_power * sin(2 * pi * frequency * simulation_time + phi)
    if harvestedPower < minimum_power:
        harvestedPower = minimum_power
    return harvestedPower * (1 + randint(-variation, variation) / 100)

C = 100e-6  # capacitancia em farads
V_MAX = 5  # voltagem máxima em volts

@dataclass
class Sensor:
    id: str = ''
    energyLevel: float = 0 # J
    maxEnergyLevel: float = C * V_MAX * V_MAX / 2  # energia máxima em joules
    layer: int = 0
    index: int = 0
    chargingCycles: int = 0
    chargingCyclesCounter: int = 0
    status: bool = False # False (setup) or True (transfer)
    state: str = 'discharged'  
    parentId: Optional[str] = None
    children: Optional[set] = field(default_factory=set)
    scheduledMeetings: Optional[List[float]] = field(default_factory=list)
    tickCount: int = 0 
    charged: bool = False
    activeTick: bool = False 
    baseStation: bool = False # define se o nó é a base station

    def step(self, simulationTime: float):
        pass

    def addMeeting(self, meeting):
        i = 0
        for meeting in self.scheduledMeetings:
            while i < len(self.scheduledMeetings) and self.scheduledMeetings[i][2] <= meeting[2]:
                i += 1
            break
        self.scheduledMeetings.insert(i, meeting)
    
'''
\If{node counts a tick} \label{if:tick count}
    \If{node has full energy storage} \label{ if:full energy}
        \State update charging count  \label{st:update charge count}
        \If{build-up mode} \label{if:build-up}
            \If{node has a parent} \label{if:parent}
                \State send setup message with id, layer, status, charging time and scheduled meetings \label{st:setup message}
            \EndIf
            \If{node receives a setup message} \label{if:receive setup message}
                \If{it is unscheduled} \label{if:unscheduled}
                    \If{the node has no parent and the message comes from a higher layer} \label{if:no parent and message from higher layer}
                        \State Answer it with its own charging time \label{st:answer message}
                        \If{the parent notices the child charging time does not fit in the agenda} \label{if:no agenda}
                            \State The parent sends a new setup message with updated scheduled meetings \label{st:resend setup message}
                        \EndIf
                        \State Register the sender as the parent and register its own layer as the parent's plus one \label{st:register parent and layer}
                        \State Broadcast a setup message to find children \label{st:broadcast new setup message}
                        \State Start the timeout count \label{st:start timeout}
                    \Else
                        \If{the node has a parent, sent its broadcast and the message comes from lower layer} \label{if:node has parent and the message comes from a lower layer}
                            \State Register the sender as a child and also record its charging time and scheduled meeting times \label{st:register child and meeting}
                        \EndIf 
                    \EndIf
                \Else
                    \If{it has ready status and comes from lower layer} \label{if:lower layer ready}
                        \State Change the status to ready \label{st:becomes ready from child}
                    \Else
                        \State Reset the timeout count \label{st:reset timeout}
                    \EndIf
                \EndIf
            \EndIf
            \If{timeout expires} \label{if:timeout expires}
                \State Change status to ready \label{st:becomes ready by itself}
            \EndIf
            \If{ready} \label{if:ready}
                \State Send setup message with new status \label{st:send ready status message}
            \EndIf
        \Else
        % transfer mode
            \If{scheduled moment} \label{if:scheduled message}
                \If{communication is successful} \label{if:successful communication}
                    \State Keep the schedule \label{st:keep schedule}
                \Else
                    \State Go back to the build-up mode \label{st:restart build-up mode}
                \EndIf
            \EndIf
        \EndIf
    \EndIf
    \If{node has at least minimum energy storage} \label{if:minimum energy}
        \State update ticks count \label{st:update tick count}
    \EndIf
\EndIf
'''