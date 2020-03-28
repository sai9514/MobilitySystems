import geopy.distance
from gurobipy import *
import networkx as nx
import csv
from MobilitySystems import getData
import matplotlib.pyplot as plt

valueTime = 0.0032305
ulEscoot = 1
eScooterLimit = 1200
EScooterCost = 0.0033
WeeklyPackageCost = 21
publicTransportCost = 2.9
publicTransportLimit = 6
waitingTimeValue = 600 * valueTime

directory = "/home/sai/PycharmProjects/BerlinRoutes/OutputsGurobi/Students/User2/"

# getting weekly user trips
user_weekly_trips = getData.getUserWeeklyTripDetails()
print(user_weekly_trips)
tripForPrint = -1

# Opening the result files to write them later
with open(directory + 'OptimumRouteWeekly.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["week", "trip", "variables", "values"])

with open(directory + 'ObjectiveValuesWeekly.csv', 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Week", "Objective", "Values"])

# iterating through the weeks one by one
for week in user_weekly_trips:
    trips = user_weekly_trips[week]  # includes all the trips for this week as an array

    # Creating model for the entire week

    m = Model('WeeklyPackageRoutes')

    # creating over usage constraint for e scooter and public transport for each week
    WeeklyOverUsage = m.addVar(vtype=GRB.INTEGER,
                               name='ScooterWeeklyOverUsage')  # Overusage of scooter decision variable
    publicOverUsage = m.addVar(vtype=GRB.INTEGER,
                               name='PublicWeeklyOverUsage')  # Overusage of public transport decision variable

    r = {}
    x = {}
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
    eScooterUnlockCost = {}
    tripNum = 0

    # Get list of Public transport modes from list of public transport modes
    publicModeList = []
    with open('publicModeList.csv', 'r') as csv_file:
        ff = csv.reader(csv_file)
        for eachRow in ff:
            publicModeList.append(eachRow[0])

    # print(week)
    for trip in trips:
        # getting origin and destination for each trip in the week
        orig = trip[0]
        dest = trip[1]

        # Decision variable to check if public transport was used in this trip
        x[tripNum] = m.addVar(vtype=GRB.BINARY, name='publicUsage_trip_' + str(
            tripNum))

        # getting the network file with public transport and e scooters
        G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlin1.gpickle")

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
                edgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[
                    2]  # All edges of the trip in dictionary
                if 'walk' != modeKey:
                    if 'scoot' != modeKey:
                        # Public transport edges for each trip
                        publicEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[
                            2]
                    else:
                        # EScooter edges for each trip
                        scootEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1], modeKey)] = eachEdge[
                            2]

                        # looping through all edges one by one to create dict of "in" edges and "out" edges from a node
        # for the dicts edgeIn and edgeOut - key: (trip, nodes), value: list of edges entering/leaving the vertex
        # adding a binary variable for each link
        for edges in edgeAttrs:
            # condition to only create these dictionaries for the current trip (to avoid duplicates)
            if edges[0] == tripNum:
                edgeLink = (edges[1][0], edges[1][1])  # "from node" to "to node"
                u = edges[1][0]  # from node
                v = edges[1][1]  # to node

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
        write the timings in csv file for viewing
        with open(directory + week + '_timings_trip_' + str(
                tripNum) + '.csv', 'w') as csv_file:
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
        eScooterTime[edgeAttr] = (int(list(scootEdgeAttrs[edgeAttr].values())[0]))
        eScooterUnlockCost[edgeAttr] = ulEscoot

    # creating constraints for each trip

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

        m.addConstr(quicksum(r[publicEdges] for publicEdges in publicEdgeAttrs if publicEdges[0] == t) >= 1000 * (
                x[t] - 1))
        m.addConstr(
            quicksum(r[publicEdges] for publicEdges in publicEdgeAttrs if publicEdges[0] == t) <= 1000 * x[t])

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

    # Weekly OverUsage Constraint
    m.addConstr(quicksum(
        r[edgeAttr] * eScooterTime[edgeAttr] for edgeAttr in scootEdgeAttrs) <= eScooterLimit + WeeklyOverUsage)

    # Public Over Usage Constraint
    m.addConstr(quicksum(x[i] for i in range(0, tripNum - 1)) <= publicTransportLimit + publicOverUsage)

    # Objective FunctioneScooterTime
    obj = quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in edgeAttrs.keys()) + \
          quicksum(r[edgeAttr] * (eScooterUnlockCost[edgeAttr]) for edgeAttr in scootEdgeAttrs.keys()) + \
          quicksum(transfer.values()) * waitingTimeValue + \
          EScooterCost * WeeklyOverUsage + WeeklyPackageCost

    m.setObjective(obj, GRB.MINIMIZE)
    m.optimize()

    var_values = {}
    for v in m.getVars():
        var_values[(str.encode(v.varName))] = v.x

    # print("var_values are  ", var_values.items())

    with open(directory + 'ObjectiveValuesWeekly.csv', 'a') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([week, "Objective Function", obj.getValue()])
        writer.writerow([week, "Package Cost", WeeklyPackageCost])
        scooterOverUsage = 0
        publicTransOverUsage = 0
        for key, value in var_values.items():
            if "PublicWeeklyOverUsage" in str(key):
                publicTransOverUsage = value
                writer.writerow([week, "Public Transport Over-Usage Cost", publicTransportCost * publicTransOverUsage])
            if "ScooterWeeklyOverUsage" in str(key):
                scooterOverUsage = value
                writer.writerow([week, "Scooter Over-Usage Cost", EScooterCost * scooterOverUsage])
        writer.writerow([week, "Monetary Time Value", obj.getValue() - WeeklyPackageCost - (EScooterCost *
                                                                                            scooterOverUsage) - (
                                     publicTransportCost * publicTransOverUsage)])

    i = 0
    with open(directory + 'OptimumRouteWeekly.csv', 'a') as csv_file:
        writer = csv.writer(csv_file)
        tripForPrint += 1
        for key, value in var_values.items():
            if "Usage" in str(key):
                writer.writerow([week, tripForPrint, key, value])
            elif "transfer_" in str(key):
                writer.writerow([week, tripForPrint, key, value])
            else:
                routeNumber = ""
                if key[6:7].isdigit():
                    if not key[7:8].isdigit():
                        routeNumber = int(key[6:7])
                    else:
                        routeNumber = int(key[6:7] + key[7:8])
                else:
                    routeNumber = i
                if i != routeNumber:
                    i += 1
                    tripForPrint += 1
                if value != 0:
                    writer.writerow([week, tripForPrint, key, value])
