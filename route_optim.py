import csv

from mobility import getData
from gurobipy import *
import networkx as nx

m = Model('RouteOptimization')

init_time = "12:34:55"
stop_id = "060024101336"
limit_dist = 0.4
stops = []
agency = 1




orig = (52.5176000, 13.3938110)
dest = (52.5018090, 13.4538480)

valueTime = 100
f = 1
c = 1
ulEscoot = 500

G = getData.getNWFromAgencyEdgeAttrs(agency, orig, dest)
edgeList = G.edges.data('attrs')

nodeList = list(G.nodes())
print(nodeList)
print(edgeList)

edgeAttrs = {}
publicEdgeAttrs = {}
scootEdgeAttrs = {}

# creating dictionaries with full edges and only public transport edges for different constraints
for eachEdge in edgeList:
    edgeAttrs[(eachEdge[0], eachEdge[1])] = eachEdge[2]
    if 'walk' not in eachEdge[2].keys():
        if 'scoot' not in eachEdge[2].keys():
            publicEdgeAttrs[(eachEdge[0], eachEdge[1])] = eachEdge[2]
        else:
            scootEdgeAttrs[(eachEdge[0], eachEdge[1])] = eachEdge[2]

print("All edges: ", edgeAttrs)
print("PublicTransport edges: ", publicEdgeAttrs)
print("EScooterTransport edges: ", scootEdgeAttrs)

# key: nodes, value: list of edges entering/leaving the vertex
edgeIn = {n: [] for n in nodeList}
edgeOut = {n: [] for n in nodeList}

# adding a binary variable for each link
r = {}
for edgeLink in edgeAttrs:
    u = edgeLink[0]
    v = edgeLink[1]
    r[edgeLink] = m.addVar(vtype=GRB.BINARY, name='r' + str(edgeLink))
    edgeIn[v].append(r[edgeLink])
    edgeOut[u].append(r[edgeLink])

# adding a binary variable for use of public transport
x = m.addVar(vtype=GRB.BINARY, name='publicTransUse')

m.update()
print(edgeIn)
print(edgeOut)

# adding constraints
for node in nodeList:
    m.addConstr(quicksum(edgeIn[node]) <= 1, name='arrivalConstr')
    m.addConstr(quicksum(edgeOut[node]) <= 1, name='departureConstr')

nodeList.remove('orig')
nodeList.remove('dest')

mainNodesList = nodeList
for eachNode in mainNodesList:
    m.addConstr(quicksum(edgeOut[eachNode]) - quicksum(edgeIn[eachNode]) == 0, name='flowConstr')

m.addConstr(quicksum(edgeOut['orig']) - quicksum(edgeIn['orig']) == 1, name='originConst')

m.addConstr(quicksum(edgeIn['dest']) - quicksum(edgeOut['dest']) == 1, name='destConst')

# Constraint for x - to check if public transport is used in the route
# Need to quick sum only public transport edges

m.addConstr(quicksum(r[edgeAttr] for edgeAttr in publicEdgeAttrs) >= 1000 * (x - 1), name='publicTransConstr1')

m.addConstr(quicksum(r[edgeAttr] for edgeAttr in publicEdgeAttrs) <= 1000 * x, name='publicTransConstr2')

monValTime = {}
eScooterTimeCost = {}

for edgeAttr in edgeAttrs:
    monValTime[edgeAttr] = int(list(edgeAttrs[edgeAttr].values())[0]) * valueTime
    print("monValTime: ", monValTime[edgeAttr])

    # include unlock costs here
    eScooterTimeCost[edgeAttr] = ulEscoot + (int(list(edgeAttrs[edgeAttr].values())[0]) * c)
    print("eScooterTimeCost: ", eScooterTimeCost[edgeAttr])

obj = quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in edgeAttrs) + quicksum(
    r[edgeAttr] * (eScooterTimeCost[edgeAttr]) for edgeAttr in scootEdgeAttrs) + x * f

# set Objective
m.setObjective(obj, GRB.MINIMIZE)

m.optimize()
var_values = {}

for v in m.getVars():
    var_values[(str(v.varName))] = v.x

print(var_values.items())

with open('optimumroute.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    for key, value in var_values.items():
        writer.writerow([key, value])

"""
stops = getData.getClosestStops(init_lat, init_lon, limit_dist)
for stop in stops:
    print(stop)

trips = []
trips = []
trips = getData.getTripsFromStop(stop_id, init_time)
for trip in trips:
    print(trip)
"""
