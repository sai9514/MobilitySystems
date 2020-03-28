import geopy.distance
from gurobipy import *
import networkx as nx
import csv
from MobilitySystems import getData
import matplotlib.pyplot as plt


valueTime = 0.003231
eScooterLimit = 3600
EScooterCost = 0.0033
MonthlyPackageCost = 96
waitingTimeValue = 600 * valueTime


directory = "/home/sai/PycharmProjects/BerlinRoutes/OutputsGurobi/Students/User1/"

# getting monthly user trips
user_monthly_trips = getData.getUserMonthlyTripDetails()
print(user_monthly_trips)
# creating the model for monthly package route selection
m = Model('MonthlyPackageRoutes')

# creating monthly over usage variable for e scooter limit
MonthlyOverUsage = m.addVar(vtype=GRB.INTEGER, name='MonthlyOverUsage')

r = {}
transfer = {}

edgeAttrs = {}
publicEdgeAttrs = {}
scootEdgeAttrs = {}
edgeIn = {}
edgeOut = {}
edgeModeIn = {}
edgeModeOut = {}

subNodesList = []
monValTime = {}
eScooterTime = {}
tripNum = 0

# Get list of Public transport modes from list of public transport modes
publicModeList = []
with open('publicModeList.csv', 'r') as csv_file:
    ff = csv.reader(csv_file)
    for eachRow in ff:
        publicModeList.append(eachRow[0])

# iterating through the trips one by one
for trip in user_monthly_trips:
    print(tripNum)
    # getting origin and destination for each trip
    orig = trip[0]
    dest = trip[1]

    # getting the network file with public transport and e scooters
    G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlinNew.gpickle")

    # nx.draw_networkx(G, with_labels=True, node_size=10, font_size=2, arrowsize=4) plt.savefig(
    # "/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/sample_" + str(week) + "_" + str(tripNum) + ".pdf",
    # bbox_inches='tight', format='pdf', dpi=1200)

    node_attrs = nx.get_node_attributes(G, name='locale')

    # adding links between orig or dest to stops or e scooters
    for item in node_attrs.items():
        d1 = geopy.distance.vincenty(orig, item[1]).km
        d2 = geopy.distance.vincenty(dest, item[1]).km
        if "es_" not in item[0]:  # for public transport stops
            if d1 < 4:
                G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
            if d2 < 4:
                G.add_edge(item[0], "dest", key='walk', attrs={"walk": int(720 * d2)})
        else:  # for e scooter stops
            if d1 < 4:
                G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
            if d2 < 5:
                G.add_edge(item[0], "dest", key='scoot', attrs={"scoot": int(180 * d2)})
    print("Total No. of edges after connecting orig, dest and e scooters: ", nx.number_of_edges(G))
    edgeList = G.edges.data('attrs')

    # Creating separate dictionaries of public transport edges, Escooter edges and all edges
    for eachEdge in edgeList:
        for modeKey in eachEdge[2]:
            edgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]
            if 'walk' != modeKey:
                if 'scoot' != modeKey:
                    # Public transport edges for each trip
                    publicEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]
                else:
                    # EScooter edges for each trip
                    scootEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]

    # looping through all edges one by one to create dict of "in" edges and "out" edges from a node
    # for the dicts edgeIn and edgeOut - key: (trip, nodes), value: list of edges entering/leaving the vertex
    # adding a binary variable for each link
    for edges in edgeAttrs:
        # condition to only create these dictionaries for the current trip (to avoid duplicates)
        if edges[0] == tripNum:
            edgeLink = (edges[1][0], edges[1][1])
            u = edges[1][0]     # from node
            v = edges[1][1]     # to node

            # route decision variable based on tripNum, and edges
            r[edges] = m.addVar(vtype=GRB.BINARY, name='route_' + str(edges))

            if (tripNum, v) in edgeIn:
                edgeIn[tripNum, v].append(r[edges])
            else:
                edgeIn[tripNum, v] = [r[edges]]
            if (tripNum, u) in edgeOut:
                edgeOut[tripNum, u].append(r[edges])
            else:
                edgeOut[tripNum, u] = [r[edges]]

            # edge In and Out dictionaries along with their mode - used for transfer constraint
            if (tripNum, v, edgeLink[1][2]) in edgeModeIn:
                edgeModeIn[tripNum, v, edgeLink[1][2]].append(r[edges])
            else:
                edgeModeIn[tripNum, v, edgeLink[1][2]] = [r[edges]]
            if (tripNum, u, edgeLink[1][2]) in edgeModeOut:
                edgeModeOut[tripNum, u, edgeLink[1][2]].append(r[edges])
            else:
                edgeModeOut[tripNum, u, edgeLink[1][2]] = [r[edges]]

    # list of nodes in each trip
    subNodesList.append(list(G.nodes()))

    """
    # write the timings in csv file for viewing
    with open(directory + 'Timings/' + 'Timings_trip_' + str(tripNum) + '.csv', 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["edges", "timings"])
        for edgeAttr in edgeAttrs:
            if edgeAttr[0] == tripNum:
                writer.writerow([str.encode(str(edgeAttr[1])), int(list(edgeAttrs[edgeAttr].values())[0])])
    plt.clf()
    """
    tripNum += 1

# removing orig and dest in each list of nodes
for nodes in subNodesList:
    nodes.remove('orig')
    nodes.remove('dest')

for edgeAttr in edgeAttrs:
    monValTime[edgeAttr] = int(list(edgeAttrs[edgeAttr].values())[0]) * valueTime

for edgeAttr in scootEdgeAttrs:
    eScooterTime[edgeAttr] = (int(list(edgeAttrs[edgeAttr].values())[0]))

# creating constraints for whole month

# constraint to make sure each node is left if it is reached (flow constraint)
for t in range(0, tripNum):
    # origin constraint
    m.addConstr((quicksum(edgeOut[t, 'orig']) == 1), name='originConst')

    # destination constraint
    m.addConstr((quicksum(edgeIn[t, 'dest']) == 1), name='destConst')

    # add transfer binary variable for each node, each mode
    print("log for creating transfer decision variable")
    for nodes in subNodesList[t]:
        for mode in publicModeList:
            if (t, nodes, mode) in edgeModeIn or (t, nodes, mode) in edgeModeOut:
                transfer[t, nodes, mode] = m.addVar(vtype=GRB.BINARY,
                                                    name='transfer_' + str(t) + str(nodes) + str(mode))
            if (t, nodes, mode) not in edgeModeIn:
                edgeModeIn[t, nodes, mode] = [0]
            if (t, nodes, mode) not in edgeModeOut:
                edgeModeOut[t, nodes, mode] = [0]

    for node in subNodesList[t]:
        # node = subNodes[i]
        # constraint to make sure each node is left if it is reached (flow constraint)
        m.addConstr(quicksum(edgeOut[t, node]) - quicksum(edgeIn[t, node]) == 0, name='flowConstr')

        # constraint to make sure only one edge reaches a node
        m.addConstr(quicksum(edgeIn[t, node]) <= 1, name='arrivalConstr')

        # constraint to make sure only one edge is leaving a node
        m.addConstr(quicksum(edgeOut[t, node]) <= 1, name='departConstr')

        # transfer constraint at each node for each mode for each trip
        for mode in publicModeList:
            if (t, node, mode) in transfer:
                m.addConstr(
                    quicksum(edgeModeOut[t, node, mode]) - quicksum(edgeModeIn[t, node, mode]) <= transfer[
                        t, node, mode],
                    name='transferConstr')

# Monthly OverUsage Constraint
m.addConstr(quicksum(
    r[edgeAttr] * eScooterTime[edgeAttr] for edgeAttr in scootEdgeAttrs) <= eScooterLimit + MonthlyOverUsage)

# Objective Function
obj = quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in edgeAttrs) + \
      quicksum(transfer.values()) * waitingTimeValue + \
      EScooterCost * MonthlyOverUsage + MonthlyPackageCost

m.setObjective(obj, GRB.MINIMIZE)
m.optimize()

var_values = {}
for v in m.getVars():
    var_values[(str.encode(v.varName))] = v.x

# print("var_values are  ", var_values.items())

with open(directory + 'ObjectiveValueMonthly.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Objective", "Values"])
    writer.writerow(["Objective Function", obj.getValue()])
    writer.writerow(["Package Cost", MonthlyPackageCost])
    for key, value in var_values.items():
        if "MonthlyOverUsage" in str(key):
            overUsage = value
            writer.writerow(["Over-Usage Cost", EScooterCost * overUsage])
    writer.writerow(["Monetary Time Value", obj.getValue() - MonthlyPackageCost - (EScooterCost * overUsage)])

with open(directory + 'OptimumSolutionMonthly.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Variables", "Values"])
    for key, value in var_values.items():
        if value != 0:
            writer.writerow([key, value])