import csv
from MobilitySystems import getData
from gurobipy import *
import networkx as nx
import geopy.distance

valueTime = 0.0032305
ulEscoot = 1
EScooterCost = 0.005
publicTransportCost = 2.9
waitingTimeValue = 300 * valueTime

directory = "/home/sai/PycharmProjects/BerlinRoutes/OutputsGurobi/Students/User2/"

# get list of trips from the user data file
user_payg_trips = getData.getUserPAYGTripsDetails()


# Opening the result files to write them later
with open(directory + 'OptimumRoutePAYG.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Trips", "Variables", "Value"])

with open(directory + 'ObjectiveFunctionPAYG.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Trips", "Objectives", "Value", "valueTime: ", valueTime, "EScooterCost: ", EScooterCost])

i = -1

# iterating through each trip

for trip in user_payg_trips:

    # getting the network file with public transport and e scooters

    G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlinNew.gpickle")
    orig = trip[0]
    dest = trip[1]
    m = Model('PAYGRouteOptimization')
    r = {}
    t = {}
    edgeAttrs = {}
    publicEdgeAttrs = {}
    publicModeEdgeAttrs = {}
    scootEdgeAttrs = {}
    edgeIn = {}
    edgeOut = {}
    edgeModeIn = {}
    edgeModeOut = {}

    node_attrs = nx.get_node_attributes(G, name='locale')
    # print(node_attrs)
    # print("No. of initial edges ", nx.number_of_edges(G))

    for item in node_attrs.items():
        d1 = geopy.distance.vincenty(orig, item[1]).km
        d2 = geopy.distance.vincenty(dest, item[1]).km
        if "es_" not in item[0]:  # for public transport stops
            if d1 < 1:
                G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
            if d2 < 1:
                G.add_edge(item[0], "dest", key='walk', attrs={"walk": int(720 * d2)})
        else:  # for e scooter stops
            if d1 < 1:
                G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
            if d2 < 5:
                G.add_edge(item[0], "dest", key='scoot', attrs={"scoot": int(180 * d2)})
    # print("No. of edges after orig, dest and e scooters: ", nx.number_of_edges(G))

    edgeList = G.edges.data('attrs')
    # print(edgeList)

    # Get list of Public transport modes from list of public transport modes
    publicModeList = []
    with open('publicModeList.csv', 'r') as csv_file:
        ff = csv.reader(csv_file)
        for eachRow in ff:
            publicModeList.append(eachRow[0])

    # creating dictionaries with full edges and only public transport edges for different constraints
    for eachEdge in edgeList:
        print(eachEdge)
        for modeKey in eachEdge[2]:
            edgeAttrs[(eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]
            if 'walk' != modeKey:
                if 'scoot' != modeKey:
                    publicEdgeAttrs[(eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]
                else:
                    scootEdgeAttrs[(eachEdge[0], eachEdge[1], modeKey)] = eachEdge[2]

    # for the dicts edgeIn and edgeOut - key: nodes, value: list of edges entering/leaving the vertex
    # adding a binary variable for each link
    for edgeLink in edgeAttrs:
        u = edgeLink[0]     # from node
        v = edgeLink[1]     # to node
        r[edgeLink] = m.addVar(vtype=GRB.BINARY, name='r_' + str(edgeLink))     # route decision variable

        if v in edgeIn:
            edgeIn[v].append(r[edgeLink])
        else:
            edgeIn[v] = [r[edgeLink]]
        if u in edgeOut:
            edgeOut[u].append(r[edgeLink])
        else:
            edgeOut[u] = [r[edgeLink]]

        # edge In and Out dictionaries along with their mode - used for transfer constraint

        if (v, edgeLink[2]) in edgeModeIn:
            edgeModeIn[v, edgeLink[2]].append(r[edgeLink])
        else:
            edgeModeIn[v, edgeLink[2]] = [r[edgeLink]]
        if (u, edgeLink[2]) in edgeModeOut:
            edgeModeOut[u, edgeLink[2]].append(r[edgeLink])
        else:
            edgeModeOut[u, edgeLink[2]] = [r[edgeLink]]

    # adding a binary variable for use of public transport
    x = m.addVar(vtype=GRB.BINARY, name='publicTransportUse')

    nodeList = list(G.nodes())

    nodeList.remove('orig')
    nodeList.remove('dest')

    mainNodesList = nodeList

    # add transfer binary variable for each node, each mode
    print("log for creating transfer decision variable")
    for nodes in mainNodesList:
        for mode in publicModeList:
            if (nodes, mode) in edgeModeIn or (nodes, mode) in edgeModeOut:
                t[nodes, mode] = m.addVar(vtype=GRB.BINARY, name='t_' + str(nodes) + str(mode))
            if (nodes, mode) not in edgeModeIn:
                edgeModeIn[nodes, mode] = [0]
            if (nodes, mode) not in edgeModeOut:
                edgeModeOut[nodes, mode] = [0]

    # creating constraints

    # origin constraint
    m.addConstr(quicksum(edgeOut['orig']) == 1, name='originConst')

    # destination constraint
    m.addConstr(quicksum(edgeIn['dest']) == 1, name='destConst')

    for eachNode in mainNodesList:
        # adding constraints

        # constraint to make sure only one edge reaches a node
        m.addConstr(quicksum(edgeIn[eachNode]) <= 1, name='arrivalConstr')

        # constraint to make sure only one edge is leaving a node
        m.addConstr(quicksum(edgeOut[eachNode]) <= 1, name='departureConstr')

        # constraint to make sure each node is left if it is reached (flow constraint)
        m.addConstr(quicksum(edgeOut[eachNode]) - quicksum(edgeIn[eachNode]) == 0, name='flowConstr')

        # transfer constraint at each node for each mode
        for mode in publicModeList:
            if (eachNode, mode) in t:
                m.addConstr(
                    quicksum(edgeModeOut[eachNode, mode]) - quicksum(edgeModeIn[eachNode, mode]) <= t[eachNode, mode],
                    name='transferConstr')



    # Constraint for x - to check if public transport is used in the route
    # Need to quick sum only public transport edges

    m.addConstr(quicksum(r[edgeAttr] for edgeAttr in publicEdgeAttrs) >= 1000 * (x - 1), name='publicTransConstr1')

    m.addConstr(quicksum(r[edgeAttr] for edgeAttr in publicEdgeAttrs) <= 1000 * x, name='publicTransConstr2')

    print("All constraints created")

    monValTime = {}
    eScooterTimeCost = {}

    for edgeAttr in edgeAttrs:
        monValTime[edgeAttr] = int(list(edgeAttrs[edgeAttr].values())[0]) * valueTime

    for scootEdgeAttr in scootEdgeAttrs:
        # include unlock costs here
        eScooterTimeCost[scootEdgeAttr] = ulEscoot + (int(list(scootEdgeAttrs[scootEdgeAttr].values())[0]) * EScooterCost)

    obj = quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in edgeAttrs) + \
          quicksum(r[edgeAttr] * (eScooterTimeCost[edgeAttr]) for edgeAttr in scootEdgeAttrs) + \
          quicksum(t.values()) * waitingTimeValue + x * publicTransportCost

    # set Objective
    m.setObjective(obj, GRB.MINIMIZE)
    m.optimize()

    var_values = {}

    for v in m.getVars():
        var_values[(str.encode(v.varName))] = v.x
    i += 1
    with open(directory + 'OptimumRoutePAYG.csv', 'a') as csv_file:
        writer = csv.writer(csv_file)
        for key, value in var_values.items():
            if value != 0:
                writer.writerow([i, key, value])
    with open(directory + 'ObjectiveFunctionPAYG.csv', 'a') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([i, "Objective Function", obj.getValue()])
        eScooterUse = 0
        monValue = 0
        for key, value in var_values.items():
            key1 = key
            if "publicTransport" in str(key):
                publicTransUse = value
                writer.writerow([i, "Public Transport Cost", publicTransportCost * publicTransUse])
            else:
                if "t_" not in str(key):
                    if "es_" in str(str(key))[4:-2][:6]:
                        print(str(key))
                        thisEdge = str(str(key.decode('utf-8')))[2:-1]
                        print(thisEdge)
                        scootKey = (thisEdge.split("', '")[0][2:], thisEdge.split("', '")[1][:], thisEdge.split("', '")[2][:-1])
                        print(scootKey)
                        if value != 0:
                            eScooterUse += eScooterTimeCost[scootKey]
                    if value != 0:
                        monEdge = str(str(key1.decode('utf-8')))[2:-1]
                        monKey = (monEdge.split("', '")[0][2:], monEdge.split("', '")[1], monEdge.split("', '")[2][:-1])
                        monValue += monValTime[monKey]
                else:
                    t_value = value
                    if t_value != 0:
                        writer.writerow([i, "Transfer Variable: " + str(key), t_value])
        writer.writerow([i, "E Scooter Cost", eScooterUse])
        writer.writerow([i, "Monetary Time Value", monValue])
